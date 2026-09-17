"""Fase 1 — Datos & Limpieza. Orquesta ingesta → normalización → match modelo → dedup.
Salidas en data/processed/ + reporte de calidad en docs/calidad_fase1.md.
Ejecución: python -m pipeline.fase1
"""
import json
from pathlib import Path

import pandas as pd

from .dedup import consolidar_duplicados, deduplicar
from .ingesta import cargar_todo
from .match_modelo import enriquecer_leads_con_sku
from .normalizar import (
    normalizar_canal,
    normalizar_ciudad,
    normalizar_estado,
    normalizar_fecha,
    normalizar_telefono,
    normalizar_texto,
)

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RECHAZOS: list[dict] = []


def rechazar(archivo: str, registro_id: str, motivo: str, detalle: str = ""):
    RECHAZOS.append({"archivo": archivo, "registro_id": registro_id, "motivo": motivo, "detalle": detalle})


def run() -> dict:
    RECHAZOS.clear()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    data = cargar_todo()
    conteos = {
        "leads": len(data["leads"]),
        "conversaciones": len(data["conversaciones"]),
        "catalogo": len(data["catalogo"]),
        "asesores": len(data["asesores"]),
        "historico": len(data["historico"]),
    }

    # ------------------------------------------------ leads
    leads = data["leads"]
    leads["nombre_cliente"] = leads["nombre_cliente"].apply(normalizar_texto)

    # lead_id duplicados exactos → el segundo se rechaza
    dup_ids = leads["lead_id"][leads["lead_id"].duplicated()].tolist()
    leads = leads[~leads["lead_id"].duplicated(keep="first")].copy()
    for lid in dup_ids:
        rechazar("leads.csv", lid, "lead_id_duplicado")

    # canal / estado
    leads["canal"] = leads["canal"].apply(normalizar_canal)
    leads["estado_gestion"] = leads["estado_gestion"].apply(normalizar_estado)
    sin_canal = leads[leads["canal"] == "Desconocido"]["lead_id"].tolist()
    for lid in sin_canal:
        rechazar("leads.csv", lid, "canal_vacio")

    # teléfono
    tels = leads["telefono"].apply(normalizar_telefono)
    leads["telefono_e164"] = [t[0] for t in tels]
    for (_, row), t in zip(leads.iterrows(), tels):
        if t[1]:
            rechazar("leads.csv", row["lead_id"], t[1], row["telefono"])

    # ciudad
    leads["ciudad_canonica"] = leads["ciudad"].apply(lambda v: normalizar_ciudad(normalizar_texto(v)))
    sin_ciudad = leads[leads["ciudad_canonica"] == ""]
    for _, r in sin_ciudad.iterrows():
        rechazar("leads.csv", r["lead_id"], "ciudad_no_mapeada", normalizar_texto(r["ciudad"]))

    # fechas
    fr = leads["fecha_registro"].apply(normalizar_fecha)
    leads["fecha_registro_iso"] = [f[0] for f in fr]
    fpc = leads["fecha_primer_contacto"].apply(lambda v: normalizar_fecha(v) if normalizar_texto(v) else ("", "sin_contacto"))
    leads["fecha_primer_contacto_iso"] = [f[0] for f in fpc]
    for (_, row), f in zip(leads.iterrows(), fr):
        if f[1]:
            rechazar("leads.csv", row["lead_id"], f[1], row["fecha_registro"])

    # match de modelo
    leads = enriquecer_leads_con_sku(leads, data["catalogo"])

    # dedup intra-empresa + consolidación
    leads = consolidar_duplicados(deduplicar(leads))

    # ------------------------------------------------ conversaciones
    lids = set(leads["lead_id"])
    conversaciones = []
    for c in data["conversaciones"]:
        if c["lead_id"] not in lids:
            rechazar("conversaciones.json", c["conversacion_id"], "lead_id_huerfano", c["lead_id"])
            continue
        fecha, motivo = normalizar_fecha(c["fecha_inicio"])
        if not fecha:
            rechazar("conversaciones.json", c["conversacion_id"], motivo, c["fecha_inicio"])
            continue
        conversaciones.append({**c, "fecha_inicio_iso": fecha, "n_mensajes": len(c["mensajes"])})

    # ------------------------------------------------ persistir
    leads.to_csv(PROCESSED / "leads_normalizados.csv", index=False)
    with open(PROCESSED / "conversaciones.json", "w", encoding="utf-8") as fh:
        json.dump(conversaciones, fh, ensure_ascii=False)
    data["catalogo"].to_csv(PROCESSED / "catalogo.csv", index=False)
    data["asesores"].to_csv(PROCESSED / "asesores.csv", index=False)
    data["historico"].to_csv(PROCESSED / "historico.csv", index=False)
    with open(PROCESSED / "rechazos.json", "w", encoding="utf-8") as fh:
        json.dump(RECHAZOS, fh, ensure_ascii=False, indent=1)

    stats = {
        "conteos": conteos,
        "leads_unicos": len(leads),
        "telefono_invalido": sum(1 for r in RECHAZOS if r["motivo"].startswith("telefono_invalido")),
        "telefono_vacio": sum(1 for r in RECHAZOS if r["motivo"] == "telefono_vacio"),
        "ciudad_no_mapeada": sum(1 for r in RECHAZOS if r["motivo"] == "ciudad_no_mapeada"),
        "lead_id_duplicado": len(dup_ids),
        "duplicados_cross_channel_intra_empresa": int(leads["es_duplicado"].sum()),
        "match_modelo": leads["metodo_match"].value_counts().to_dict(),
        "conversaciones_validas": len(conversaciones),
        "conversaciones_huerfanas": sum(1 for r in RECHAZOS if r["motivo"] == "lead_id_huerfano"),
        "rechazos_totales": len(RECHAZOS),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return stats


if __name__ == "__main__":
    run()
