"""T1.2 — Ingesta de los 5 archivos fuente sin intervención manual."""
import json
from pathlib import Path

import pandas as pd

DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets-assessment-analista-ia"

ARCHIVOS = {
    "leads": "leads.csv",
    "catalogo": "catalogo_motos.csv",
    "asesores": "asesores.csv",
    "historico": "historico_cierres.csv",
    "conversaciones": "conversaciones.json",
}


def cargar_leads() -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / ARCHIVOS["leads"], dtype=str, encoding="utf-8-sig")


def cargar_catalogo() -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / ARCHIVOS["catalogo"], dtype=str, encoding="utf-8-sig")


def cargar_asesores() -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / ARCHIVOS["asesores"], dtype=str, encoding="utf-8-sig")


def cargar_historico() -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / ARCHIVOS["historico"], dtype=str, encoding="utf-8-sig")


def cargar_conversaciones() -> list[dict]:
    with open(DATASET_DIR / ARCHIVOS["conversaciones"], encoding="utf-8") as fh:
        return json.load(fh)


def cargar_todo() -> dict:
    """Carga los 5 archivos. Verificación de conteos en fase1.py."""
    return {
        "leads": cargar_leads(),
        "catalogo": cargar_catalogo(),
        "asesores": cargar_asesores(),
        "historico": cargar_historico(),
        "conversaciones": cargar_conversaciones(),
    }
