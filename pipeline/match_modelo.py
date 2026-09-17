"""T1.4 — Matching de modelo de interés (texto libre) contra el catálogo.
Estrategia en cascada, cada nivel con confianza decreciente:
  exacto (normalizado) → fuzzy (typos tipo 'Hnda'/'Bajai') → sufijo año
  ('... 2026') → solo-línea ('CB 190R') → solo-marca ('Bajaj' → NULL, marca anotada).
"""
import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

from .normalizar import normalizar_texto


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def construir_indice(catalogo: pd.DataFrame) -> dict:
    """clave normalizada de 'marca linea' → sku. También índice solo-línea."""
    indice: dict[str, str] = {}
    por_linea: dict[str, list[str]] = {}
    for _, r in catalogo.iterrows():
        clave = _norm(f"{r['marca']} {r['linea']}")
        indice[clave] = r["sku"]
        por_linea.setdefault(_norm(r["linea"]), []).append(r["sku"])
    return {"completo": indice, "linea": por_linea, "filas": catalogo.to_dict("records")}


def match_modelo(texto: str, indice: dict) -> tuple[str, float, str]:
    """Devuelve (sku, confianza 0-1, metodo). sku vacío si no hay match."""
    t = _norm(normalizar_texto(texto))
    if not t:
        return "", 0.0, "vacio"

    # quitar sufijo de año si no matchea directo
    t_sin_anio = re.sub(r"\s*(19|20)\d{2}\s*$", "", t).strip()

    for cand in (t, t_sin_anio):
        if cand in indice["completo"]:
            return indice["completo"][cand], 1.0, "exacto"

    # fuzzy contra claves completas (typos cortos)
    mejor, mejor_ratio = "", 0.0
    for clave, sku in indice["completo"].items():
        r = SequenceMatcher(None, t_sin_anio or t, clave).ratio()
        if r > mejor_ratio:
            mejor, mejor_ratio = sku, r
    if mejor_ratio >= 0.82:
        return mejor, round(mejor_ratio, 2), "fuzzy"

    # solo línea ('CB 190R', 'Navi')
    for cand in (t_sin_anio, t):
        if cand in indice["linea"]:
            skus = indice["linea"][cand]
            return (skus[0], 0.9, "solo_linea") if len(skus) == 1 else ("", 0.0, "linea_ambigua")

    # fuzzy contra líneas
    for clave, skus in indice["linea"].items():
        r = SequenceMatcher(None, t_sin_anio or t, clave).ratio()
        if r >= 0.9 and len(skus) == 1:
            return skus[0], round(r, 2), "fuzzy_linea"

    # marca sola ('Bajaj') o marca+familia ambigua ('Bajaj Pulsar' → varios SKUs)
    marcas = {_norm(f["marca"]) for f in indice["filas"]}
    if t in marcas or t_sin_anio in marcas:
        return "", 0.0, "solo_marca"
    for marca in marcas:
        if (t_sin_anio or t).startswith(marca + " ") or (t_sin_anio or t) == marca:
            return "", 0.0, "familia_ambigua"
    return "", 0.0, "sin_match"


def enriquecer_leads_con_sku(leads: pd.DataFrame, catalogo: pd.DataFrame) -> pd.DataFrame:
    indice = construir_indice(catalogo)
    out = leads.copy()
    res = out["modelo_interes_texto"].apply(lambda t: match_modelo(t, indice))
    out["sku_sugerido"] = [r[0] for r in res]
    out["confianza_match"] = [r[1] for r in res]
    out["metodo_match"] = [r[2] for r in res]
    return out
