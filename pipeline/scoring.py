"""T3.2 — Score de prioridad explicable (0-100) + banda.

Pesos calibrados contra historico_cierres.csv (docs/calibracion.json).
Regla: puntos ∝ evidencia de lift. Cada componente se puede explicar al asesor
y al evaluador con su tasa de cierre real medida.

Componentes y evidencia (tasa cierre | grupo vs global 8,9%):
  pidio_cita        +20  → 10,9% (lift 1.22; combinada con rapidez 14,4%)
  cuota_manifiesta  +15  → 10,9% (lift 1.22)
  intencion_compra  +15  → proxy cita+cuota 13,9% (lift 1.55)
  urgencia_24h      +15  → contacto <24h 11,5% (lift 1.29) vs >=24h 6,8%
  pago_contado      +10  → 11,0% (lift 1.23) vs crédito 7,7%
  multicanal        +10  → no medible en histórico (cualitativo: re-contactó)
  modelo_concreto   +10  → no medible en histórico (interés específico vs difuso)
  canal_whatsapp     +5  → 9,4% (lift 1.06)

Bandas: Alta ≥50 · Media 25-49 · Baja <25.
"""
from datetime import datetime, timedelta

MAX_SCORE = 100
BANDA_ALTA = 50
BANDA_MEDIA = 25


def puntuar(f: dict) -> tuple[int, dict, str]:
    """f: diccionario de señales booleanas del lead (ver claves abajo)."""
    comp = {
        "Pidió cita": 20 if f.get("pidio_cita") else 0,
        "Manifestó cuota inicial": 15 if f.get("cuota_manifiesta") else 0,
        "Intención de compra inmediata": 15 if f.get("intencion_compra") else 0,
        "Menos de 24h sin contactar": 15 if f.get("urgencia_24h") else 0,
        "Pagaría de contado": 10 if f.get("pago_contado") else 0,
        "Escribió por 2+ canales": 10 if f.get("multicanal") else 0,
        "Modelo específico definido": 10 if f.get("modelo_concreto") else 0,
        "Viene por WhatsApp": 5 if f.get("canal_whatsapp") else 0,
    }
    score = min(MAX_SCORE, sum(comp.values()))
    banda = "Alta" if score >= BANDA_ALTA else ("Media" if score >= BANDA_MEDIA else "Baja")
    return score, comp, banda


def senales_lead(lead: dict, extraccion: dict | None, ahora: datetime | None = None) -> dict:
    """Construye las señales booleanas desde un lead normalizado + su extracción IA."""
    ahora = ahora or datetime.now()
    ext = extraccion or {}
    try:
        fr = datetime.fromisoformat(lead.get("fecha_registro_iso") or "")
        edad_h = (ahora - fr).total_seconds() / 3600
    except ValueError:
        edad_h = None
    sin_contactar = not (lead.get("fecha_primer_contacto_iso") or "").strip()
    canales = (lead.get("canales_merged") or lead.get("canal") or "").split("|")
    return {
        "pidio_cita": bool(ext.get("pidio_cita")) or (lead.get("estado_gestion") == "Cotización enviada"),
        "cuota_manifiesta": ext.get("cuota_inicial") == "SI",
        "intencion_compra": ext.get("intencion") == "compra_inmediata",
        "urgencia_24h": sin_contactar and edad_h is not None and edad_h < 24,
        "pago_contado": ext.get("forma_pago") == "contado",
        "multicanal": len([c for c in canales if c]) > 1,
        "modelo_concreto": bool(lead.get("sku_sugerido")),
        "canal_whatsapp": "WhatsApp" in canales,
    }


# ------------------------------------------------------------------ backtest
def run_backtest() -> dict:
    """T3.3 — Aplica el score a los 2.200 históricos (señales backtesteables)
    y mide la tasa de cierre por banda. Criterio de salida: Alta > Media > Baja."""
    import json
    from pathlib import Path

    import pandas as pd

    hist = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "processed" / "historico.csv", dtype=str)
    hist["horas"] = pd.to_numeric(hist["horas_al_primer_contacto"], errors="coerce")

    # Componentes backtesteables (los 3 de IA-only se excluyen y se documenta):
    PESOS_BT = {
        "pidio_cita": 20, "cuota_manifiesta": 15, "urgencia_24h": 15,
        "pago_contado": 10, "canal_whatsapp": 5,
    }  # máx 65 → bandas escaladas: Alta ≥ 0.5*65=32.5 → 33 · Media ≥ 16

    def score_row(r):
        s = 0
        if r["pidio_cita"] == "SI":
            s += PESOS_BT["pidio_cita"]
        if r["manifesto_cuota_inicial"] == "SI":
            s += PESOS_BT["cuota_manifiesta"]
        if pd.notna(r["horas"]) and r["horas"] < 24:
            s += PESOS_BT["urgencia_24h"]
        if r["forma_pago_declarada"] == "contado":
            s += PESOS_BT["pago_contado"]
        if r["canal"] == "WhatsApp":
            s += PESOS_BT["canal_whatsapp"]
        return s

    hist["score"] = hist.apply(score_row, axis=1)
    hist["banda"] = hist["score"].map(lambda s: "Alta" if s >= 33 else ("Media" if s >= 16 else "Baja"))

    out = {}
    for banda in ("Alta", "Media", "Baja"):
        sub = hist[hist["banda"] == banda]
        cerrados = int((sub["desenlace"] == "Cerrado").sum())
        out[banda] = {
            "n": len(sub),
            "cerrados": cerrados,
            "tasa": round(cerrados / len(sub), 4) if len(sub) else None,
            "lift": round((cerrados / len(sub)) / 0.0895, 2) if len(sub) else None,
        }
    out["monotono"] = out["Alta"]["tasa"] > out["Media"]["tasa"] > out["Baja"]["tasa"]

    dest = Path(__file__).resolve().parent.parent / "docs" / "backtest.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run_backtest()
