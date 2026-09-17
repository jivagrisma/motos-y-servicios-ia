#!/usr/bin/env python
"""Pipeline de punta a punta — UN SOLO DISPARO.

Uso:  python pipeline.py --run [--sin-ia]

Etapas (en orden): ingesta+normalización → extracción IA (Vertex AI
gemini-2.5-flash con fallback regex) → carga BD + scoring + asignación.
Idempotente: re-ejecutar no duplica filas.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

ETAPAS = [
    ("ingesta+normalizacion", [PY, "-m", "pipeline.fase1"]),
    ("extraccion_ia", [PY, "-m", "pipeline.extraer_ia"]),
    ("carga_bd+scoring", [PY, "-m", "pipeline.cargar_bd"]),
]


def run(sin_ia: bool = False) -> int:
    t0 = time.time()
    resultados = {}
    for nombre, cmd in ETAPAS:
        if sin_ia and nombre == "extraccion_ia":
            print(f"[{nombre}] OMITIDO (--sin-ia)", flush=True)
            continue
        print(f"[{nombre}] ejecutando...", flush=True)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[{nombre}] FALLÓ:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}", file=sys.stderr)
            return 1
        try:
            resultados[nombre] = json.loads(r.stdout)
        except json.JSONDecodeError:
            resultados[nombre] = r.stdout[-300:]
        print(f"[{nombre}] ok", flush=True)
    resultados["duracion_s"] = round(time.time() - t0, 1)
    print(json.dumps(resultados, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="ejecutar el pipeline completo")
    ap.add_argument("--sin-ia", action="store_true", help="omitir extracción LLM (solo regex de lo existente)")
    args = ap.parse_args()
    if not args.run:
        ap.print_help()
        sys.exit(1)
    sys.exit(run(sin_ia=args.sin_ia))
