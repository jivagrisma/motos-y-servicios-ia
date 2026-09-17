"""T3.1 — Calibración del score contra historico_cierres.csv.
Mide la tasa de cierre real por señal y su lift vs la tasa global.
La señal medida es la evidencia; los pesos del score nacen de aquí.
Ejecución: python -m pipeline.calibrar
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"


def tasa(sub: pd.DataFrame) -> tuple[int, int, float]:
    n = len(sub)
    c = int((sub["desenlace"] == "Cerrado").sum())
    return c, n, (c / n if n else 0.0)


def run() -> dict:
    h = pd.read_csv(PROCESSED / "historico.csv", dtype=str)
    h["horas"] = pd.to_numeric(h["horas_al_primer_contacto"], errors="coerce")

    c, n, tglobal = tasa(h)
    resultado = {"global": {"cerrados": c, "n": n, "tasa": round(tglobal, 4)}, "senales": {}}

    def medir(nombre: str, mascara: pd.Series, etiqueta: str):
        cc, nn, tt = tasa(h[mascara])
        resultado["senales"][nombre] = {
            "grupo": etiqueta,
            "cerrados": cc,
            "n": nn,
            "tasa": round(tt, 4),
            "lift": round(tt / tglobal, 2) if tglobal else None,
        }

    medir("cita", h["pidio_cita"] == "SI", "pidió cita")
    medir("no_cita", h["pidio_cita"] == "NO", "no pidió cita")
    medir("cuota_si", h["manifesto_cuota_inicial"] == "SI", "cuota inicial manifiesta")
    medir("cuota_no", h["manifesto_cuota_inicial"] == "NO", "cuota NO manifiesta")
    medir("cuota_noinforma", h["manifesto_cuota_inicial"] == "NO_INFORMA", "cuota no informa")
    medir("contado", h["forma_pago_declarada"] == "contado", "pago contado")
    medir("credito", h["forma_pago_declarada"] == "credito", "pago crédito")
    medir("respuesta_rapida", h["horas"] < 24, "primer contacto <24h")
    medir("respuesta_lenta", h["horas"] >= 24, "primer contacto >=24h")
    for canal in ("WhatsApp", "Meta Ads", "Formulario Web"):
        medir(f"canal_{canal.lower().replace(' ', '_')}", h["canal"] == canal, f"canal {canal}")
    # combinaciones
    medir("cita_y_rapida", (h["pidio_cita"] == "SI") & (h["horas"] < 24), "cita + <24h")
    medir("cita_y_cuota", (h["pidio_cita"] == "SI") & (h["manifesto_cuota_inicial"] == "SI"), "cita + cuota")
    medir("nada", (h["pidio_cita"] == "NO") & (h["manifesto_cuota_inicial"] != "SI") & (h["horas"] >= 24), "sin señales + >=24h")

    DOCS.mkdir(exist_ok=True)
    with open(DOCS / "calibracion.json", "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, ensure_ascii=False, indent=1)
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return resultado


if __name__ == "__main__":
    run()
