"""T1.5 — Deduplicación cross-channel INTRA-EMPRESA por teléfono E.164.
D5: la misma persona en dos empresas distintas son dos clientes distintos
(el CRM compartido exige aislamiento); dentro de la misma empresa se consolida.
Lead maestro: se prefiere WhatsApp > Meta Ads > Formulario Web (tasa de cierre
medida en histórico: 9.5% / 8.1% / 9.0%, y WhatsApp concentra la intención declarada),
desempate por fecha de registro más antigua.
"""
import pandas as pd

PRIORIDAD_CANAL = {"WhatsApp": 0, "Meta Ads": 1, "Formulario Web": 2, "Desconocido": 3}


def deduplicar(leads: pd.DataFrame) -> pd.DataFrame:
    """Marca es_duplicado y lead_maestro_id dentro de cada empresa."""
    out = leads.copy()
    out["es_duplicado"] = 0
    out["lead_maestro_id"] = ""

    valido = out[(out["telefono_e164"] != "") & out["telefono_e164"].notna()]
    for (empresa, tel), grupo in valido.groupby(["empresa_id", "telefono_e164"]):
        if len(grupo) < 2:
            continue
        g = grupo.assign(_p=grupo["canal"].map(PRIORIDAD_CANAL)).sort_values(["_p", "fecha_registro_iso"])
        maestro = g.index[0]
        for idx in g.index[1:]:
            out.loc[idx, "es_duplicado"] = 1
            out.loc[idx, "lead_maestro_id"] = out.loc[maestro, "lead_id"]
    return out


def consolidar_duplicados(leads: pd.DataFrame) -> pd.DataFrame:
    """Para el lead maestro: anota canales y merges de información (email/ciudad/modelo faltantes)."""
    out = leads.copy()
    out["canales_merged"] = out["canal"]
    dups = out[out["es_duplicado"] == 1]
    for _, dup in dups.iterrows():
        m = out.index[out["lead_id"] == dup["lead_maestro_id"]]
        if len(m) == 0:
            continue
        m = m[0]
        canales = {out.loc[m, "canales_merged"], dup["canal"]}
        out.loc[m, "canales_merged"] = "|".join(sorted(canales))
        for campo in ("email", "ciudad_canonica", "sku_sugerido", "modelo_interes_texto"):
            maestro_vacio = not str(out.loc[m, campo] or "").strip()
            dup_lleno = str(dup[campo] or "").strip()
            if maestro_vacio and dup_lleno:
                out.loc[m, campo] = dup[campo]
    return out
