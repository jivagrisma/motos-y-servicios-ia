"""T2.1/T2.2 — Extracción estructurada de conversaciones WhatsApp.

Primaria: Vertex AI gemini-2.5-flash con schema JSON estricto (ADC, sin API keys).
Fallback: extractor determinista por regex (mismo contrato de salida).
Salida: data/processed/extracciones.json — una fila por conversacion_id.
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
PROJECT = os.environ.get("GCP_PROJECT", "motos-servicios-assessment-ia")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
MODEL = "gemini-2.5-flash"

SCHEMA = {
    "type": "object",
    "properties": {
        "modelo_interes": {"type": "string", "description": "Modelo de moto mencionado por el cliente, textual. Vacío si no se menciona."},
        "cuota_inicial": {"type": "string", "enum": ["SI", "NO", "NO_INFORMA"], "description": "SI si el cliente manifiesta monto/presupuesto de cuota inicial"},
        "cuota_inicial_monto": {"type": "string", "description": "Monto textual mencionado, ej '2 millones'. Vacío si no aplica."},
        "forma_pago": {"type": "string", "enum": ["contado", "credito", "no_informa"]},
        "intencion": {"type": "string", "enum": ["compra_inmediata", "explorando_precios", "agendando", "sin_intencion_clara"]},
        "objecion_principal": {"type": "string", "description": "Objeción del cliente en máximo 8 palabras. Vacío si no hay."},
        "pidio_cita": {"type": "boolean"},
        "pidio_cotizacion": {"type": "boolean"},
    },
    "required": ["modelo_interes", "cuota_inicial", "cuota_inicial_monto", "forma_pago", "intencion", "objecion_principal", "pidio_cita", "pidio_cotizacion"],
}

PROMPT = """Eres un asistente de un CRM de una comercializadora de motos en Colombia.
Analiza la conversación de WhatsApp entre un cliente y un asesor y extrae los campos del esquema.

Reglas:
- Solo información MANIFESTADA por el cliente (mensajes con emisor=cliente), no suposiciones del asesor.
- cuota_inicial: SI solo si el cliente declara un monto o presupuesto para la entrada/cuota inicial.
- forma_pago: según lo que el cliente dice querer ("de contado", "financiada", "a crédito", "cuotas").
- intencion: compra_inmediata (quiere cerrar ya), explorando_precios (solo mira precios/compara), agendando (agenda visita/cita), sin_intencion_clara.
- pidio_cita / pidio_cotizacion: true solo si el CLIENTE lo pide explícitamente.

Conversación:
{transcripcion}
"""


def _transcribir(conv: dict) -> str:
    lineas = [f"[{m['hora']}] {m['emisor']}: {m['texto']}" for m in conv["mensajes"]]
    return "\n".join(lineas)


# ---------------------------------------------------------------- LLM
import threading

_tls = threading.local()


def _get_client():
    # Client por hilo: no es thread-safe con ADC (httpx interno se cierra entre hilos)
    if getattr(_tls, "client", None) is None:
        from google import genai

        _tls.client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    return _tls.client


def extraer_llm(conv: dict) -> dict | None:
    try:
        from google.genai import types

        resp = _get_client().models.generate_content(
            model=MODEL,
            contents=PROMPT.format(transcripcion=_transcribir(conv)),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SCHEMA,
                temperature=0,
            ),
        )
        data = json.loads(resp.text)
        data["cuota_inicial_monto"] = str(data.get("cuota_inicial_monto") or "")
        data["modelo_interes"] = str(data.get("modelo_interes") or "")
        data["objecion_principal"] = str(data.get("objecion_principal") or "")
        return data
    except Exception as e:  # noqa: BLE001 — el fallback absorbe cualquier fallo
        return {"_error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- Fallback regex
_RE_CITA = re.compile(r"\b(cita|visita|pasar mañ?ana|ir hoy|acercarme|punto de venta)\b", re.I)
_RE_COTIZ = re.compile(r"\b(cotiza|cotización|cotizacion|precio|valor|cuánto cuesta|cuanto cuesta)\b", re.I)
_RE_CONTADO = re.compile(r"\bcontado\b", re.I)
_RE_CREDITO = re.compile(r"\b(cr[eé]dito|credito|financiad|cuotas|financiar)\b", re.I)
_RE_CUOTA = re.compile(r"\b(cuota inicial|entrada|inicial de|presupuesto)\b", re.I)
_RE_MONTO = re.compile(r"(\d[\d.,]*\s*(millones|mill[oó]n|mill|k|\.\d{3}\.000))", re.I)
_MOTORES = re.compile(r"\b(honda|bajaj|suzuki|suzuky|akt|hero|pulsar|boxer|discover|dominar|xr|xre|cb|dio|navi|twister|gn|gixxer|best|v-strom|vstrom|nkd|ttr|evo|dynamic|dash|hunk|eco|xpulse)\b", re.I)
_RE_EXPLORA = re.compile(r"\b(solo (estoy )?(mirando|viendo)|solo mirando|comparando|otra marca|precios?)\b", re.I)
_RE_COMPRA = re.compile(r"\b(la quiero|me la llevo|hacer el negocio|cerrar|comprar|listo para|mañana paso|hoy mismo)\b", re.I)


def extraer_regex(conv: dict) -> dict:
    cliente = " ".join(m["texto"] for m in conv["mensajes"] if m["emisor"] == "cliente")
    monto = _RE_MONTO.search(cliente)
    m = _MOTORES.search(cliente)
    modelo = m.group(0) if m else ""
    if _RE_COMPRA.search(cliente):
        intencion = "compra_inmediata"
    elif _RE_CITA.search(cliente):
        intencion = "agendando"
    elif _RE_EXPLORA.search(cliente):
        intencion = "explorando_precios"
    else:
        intencion = "sin_intencion_clara"
    if _RE_CONTADO.search(cliente) and not _RE_CREDITO.search(cliente):
        forma = "contado"
    elif _RE_CREDITO.search(cliente):
        forma = "credito"
    else:
        forma = "no_informa"
    return {
        "modelo_interes": modelo,
        "cuota_inicial": "SI" if (_RE_CUOTA.search(cliente) or monto) else "NO_INFORMA",
        "cuota_inicial_monto": monto.group(1) if monto else "",
        "forma_pago": forma,
        "intencion": intencion,
        "objecion_principal": "",
        "pidio_cita": bool(_RE_CITA.search(cliente)),
        "pidio_cotizacion": bool(_RE_COTIZ.search(cliente)),
    }


# ---------------------------------------------------------------- Orquestación
def ejecutar(limite: int | None = None, workers: int = 8) -> dict:
    convs = json.load(open(PROCESSED / "conversaciones.json", encoding="utf-8"))
    if limite:
        convs = convs[:limite]

    resultados: dict[str, dict] = {}
    errores = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(extraer_llm, c): c["conversacion_id"] for c in convs}
        for fut in as_completed(futures):
            cid = futures[fut]
            out = fut.result()
            if "_error" in out:
                errores += 1
                reg = extraer_regex(next(c for c in convs if c["conversacion_id"] == cid))
                resultados[cid] = {**reg, "metodo": "regex", "error_llm": out["_error"]}
            else:
                resultados[cid] = {**out, "metodo": "llm"}

    with open(PROCESSED / "extracciones.json", "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=1)

    stats = {
        "conversaciones": len(convs),
        "metodo_llm": sum(1 for r in resultados.values() if r["metodo"] == "llm"),
        "metodo_regex": sum(1 for r in resultados.values() if r["metodo"] == "regex"),
        "pidio_cita": sum(1 for r in resultados.values() if r.get("pidio_cita")),
        "cuota_si": sum(1 for r in resultados.values() if r.get("cuota_inicial") == "SI"),
        "contado": sum(1 for r in resultados.values() if r.get("forma_pago") == "contado"),
    }
    return stats


if __name__ == "__main__":
    print(json.dumps(ejecutar(), ensure_ascii=False, indent=1))
