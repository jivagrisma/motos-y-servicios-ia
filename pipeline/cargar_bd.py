"""T4.2 — Carga de la BD desde los outputs de F1-F3. Upsert idempotente:
re-ejecutar el pipeline NO duplica filas (borra y recarga las tablas de datos
en una transacción — los IDs son la clave, sin estados acumulados en el MVP).
Ejecución: python -m pipeline.cargar_bd
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from .scoring import puntuar, senales_lead

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
DB = ROOT / "data" / "motos.db"

NOMBRES_EMPRESAS = {"EMP-01": "Motos y Motores del Norte S.A.S.", "EMP-02": "Comercializadora Andina S.A.S.", "EMP-03": "Motos Caribe S.A.S."}


def _agregar_extracciones_por_lead(extracciones: dict, conv_por_lead: dict) -> dict[str, dict]:
    """Consolida N conversaciones de un lead en una señal (any/or, prioridad declarada)."""
    por_lead: dict[str, list[dict]] = {}
    for cid, ext in extracciones.items():
        lid = conv_por_lead.get(cid)
        if lid:
            por_lead.setdefault(lid, []).append(ext)

    consolidado = {}
    for lid, exts in por_lead.items():
        forma = next((e["forma_pago"] for e in exts if e.get("forma_pago") not in (None, "no_informa")), "no_informa")
        intenciones = {"compra_inmediata": 3, "agendando": 2, "explorando_precios": 1, "sin_intencion_clara": 0}
        intencion = max((e.get("intencion", "sin_intencion_clara") for e in exts), key=lambda i: intenciones.get(i, 0))
        cuota_monto = next((e.get("cuota_inicial_monto") for e in exts if e.get("cuota_inicial_monto")), "")
        consolidado[lid] = {
            "pidio_cita": any(e.get("pidio_cita") for e in exts),
            "pidio_cotizacion": any(e.get("pidio_cotizacion") for e in exts),
            "cuota_inicial": "SI" if any(e.get("cuota_inicial") == "SI" for e in exts) else ("NO" if all(e.get("cuota_inicial") == "NO" for e in exts) else "NO_INFORMA"),
            "cuota_inicial_monto": cuota_monto,
            "forma_pago": forma,
            "intencion": intencion,
            "objecion_principal": next((e.get("objecion_principal") for e in exts if e.get("objecion_principal")), ""),
        }
    return consolidado


def _asignar_asesores(conn: sqlite3.Connection):
    """Asigna leads activos a asesores del mismo punto_venta+empresa por score
    descendente, respetando capacidad_diaria_leads (menor carga primero)."""
    asesores = conn.execute(
        "SELECT a.asesor_id, a.capacidad_diaria_leads FROM asesores a WHERE a.activo=1"
    ).fetchall()
    capacidad = {a[0]: a[1] for a in asesores}
    carga = {a[0]: 0 for a in asesores}
    pv_asesor = conn.execute(
        "SELECT punto_venta_id, empresa_id, asesor_id FROM asesores WHERE activo=1"
    ).fetchall()
    por_pv: dict[tuple, list[str]] = {}
    for pv, emp, aid in pv_asesor:
        por_pv.setdefault((pv, emp), []).append(aid)

    leads = conn.execute(
        """SELECT s.lead_id, l.punto_venta_id, l.empresa_id
           FROM scoring s JOIN leads l ON l.lead_id = s.lead_id
           WHERE l.es_duplicado = 0
             AND l.estado_gestion IN ('Sin gestión','Contactado','En proceso','No contesta','Cotización enviada')
           ORDER BY s.score_total DESC"""
    ).fetchall()

    ahora = datetime.now().isoformat(timespec="seconds")
    asignaciones = []
    for lead_id, pv, emp in leads:
        candidatos = por_pv.get((pv, emp), [])
        if not candidatos:
            continue
        disp = [a for a in candidatos if carga[a] < capacidad[a]]
        if not disp:
            continue
        elegido = min(disp, key=lambda a: carga[a])
        carga[elegido] += 1
        asignaciones.append((elegido, ahora, lead_id))

    conn.executemany("UPDATE scoring SET asignado_asesor_id=?, fecha_asignacion=? WHERE lead_id=?", asignaciones)
    return len(asignaciones)


def run() -> dict:
    conn = sqlite3.connect(DB)
    conn.executescript(open(ROOT / "pipeline" / "ddl.sql", encoding="utf-8").read())

    # Si ya había datos de una ejecución anterior → recarga limpia (idempotente)
    for t in ("rechazos", "scoring", "extracciones_ia", "conversaciones", "leads",
              "catalogo_disponibilidad", "catalogo", "asesores", "puntos_venta", "empresas"):
        conn.execute(f"DELETE FROM {t}")

    leads = pd.read_csv(PROCESSED / "leads_normalizados.csv", dtype=str).fillna("")
    catalogo = pd.read_csv(PROCESSED / "catalogo.csv", dtype=str).fillna("")
    asesores = pd.read_csv(PROCESSED / "asesores.csv", dtype=str).fillna("")
    conversaciones = json.load(open(PROCESSED / "conversaciones.json", encoding="utf-8"))
    extracciones = json.load(open(PROCESSED / "extracciones.json", encoding="utf-8")) if (PROCESSED / "extracciones.json").exists() else {}
    rechazos = json.load(open(PROCESSED / "rechazos.json", encoding="utf-8"))

    # dimensiones
    conn.executemany("INSERT INTO empresas VALUES (?,?)", [(e, n) for e, n in NOMBRES_EMPRESAS.items()])
    pv_empresa = dict(zip(leads["punto_venta_id"], leads["empresa_id"]))
    pv_empresa.update(dict(zip(asesores["punto_venta_id"], asesores["empresa_id"])))
    # ciudad del PV = ciudad más frecuente de sus leads (supuesto documentado)
    pv_ciudad = leads[leads["ciudad_canonica"] != ""].groupby("punto_venta_id")["ciudad_canonica"].agg(lambda s: s.mode().iat[0] if len(s.mode()) else "").to_dict()
    pvs = [(pv, emp, pv_ciudad.get(pv, "")) for pv, emp in sorted(pv_empresa.items())]
    conn.executemany("INSERT INTO puntos_venta VALUES (?,?,?)", pvs)
    conn.executemany(
        "INSERT INTO asesores VALUES (?,?,?,?,?,?,?)",
        [(r.asesor_id, r.nombre, r.punto_venta_id, r.empresa_id, int(r.capacidad_diaria_leads), 1 if r.activo.upper() == "SI" else 0, r.fecha_ingreso) for r in asesores.itertuples()],
    )
    conn.executemany(
        "INSERT INTO catalogo VALUES (?,?,?,?,?,?,?)",
        [(r.sku, r.marca, r.linea, int(r.cilindraje), r.segmento, int(r.precio_lista), int(r.unidades_disponibles)) for r in catalogo.itertuples()],
    )
    disp = [(r.sku, pv) for r in catalogo.itertuples() for pv in r.puntos_venta_disponibles.split("|") if pv]
    conn.executemany("INSERT INTO catalogo_disponibilidad VALUES (?,?)", disp)

    # leads (vacíos → NULL en columnas FK/numéricas)
    def nulos(row: tuple, idx: set[int]) -> tuple:
        return tuple(None if (i in idx and v == "") else v for i, v in enumerate(row))

    cols_leads = [
        "lead_id", "telefono_e164", "email", "nombre_cliente", "ciudad_canonica",
        "empresa_id", "punto_venta_id", "canal", "canales_merged", "fecha_registro_iso",
        "fecha_primer_contacto_iso", "estado_gestion", "campania", "modelo_interes_texto",
        "sku_sugerido", "confianza_match", "metodo_match", "es_duplicado", "lead_maestro_id",
    ]
    idx_null = {cols_leads.index(c) for c in ("sku_sugerido", "confianza_match", "lead_maestro_id", "fecha_primer_contacto_iso")}
    conn.executemany(
        """INSERT INTO leads (lead_id, telefono_e164, email, nombre_cliente, ciudad_canonica,
           empresa_id, punto_venta_id, canal, canales_merged, fecha_registro_iso,
           fecha_primer_contacto_iso, estado_gestion, campania, modelo_interes_texto,
           sku_sugerido, confianza_match, metodo_match, es_duplicado, lead_maestro_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [nulos(tuple(r), idx_null) for r in leads[cols_leads].itertuples(index=False)],
    )

    conn.executemany(
        "INSERT INTO conversaciones VALUES (?,?,?,?,?)",
        [(c["conversacion_id"], c["lead_id"], c["canal"], c["fecha_inicio_iso"], c["n_mensajes"]) for c in conversaciones],
    )
    conv_por_lead = {c["conversacion_id"]: c["lead_id"] for c in conversaciones}
    conn.executemany(
        """INSERT INTO extracciones_ia VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(
            cid, conv_por_lead[cid], e.get("modelo_interes", ""), e.get("cuota_inicial", "NO_INFORMA"),
            e.get("cuota_inicial_monto", ""), e.get("forma_pago", "no_informa"), e.get("intencion", ""),
            e.get("objecion_principal", ""), int(bool(e.get("pidio_cita"))), int(bool(e.get("pidio_cotizacion"))),
            e.get("metodo", "regex"), json.dumps(e, ensure_ascii=False),
        ) for cid, e in extracciones.items() if cid in conv_por_lead],
    )
    conn.executemany("INSERT INTO rechazos (archivo, registro_id, motivo, detalle) VALUES (?,?,?,?)",
                     [(r["archivo"], r["registro_id"], r["motivo"], r["detalle"]) for r in rechazos])

    # scoring
    consolidadas = _agregar_extracciones_por_lead(extracciones, conv_por_lead)
    ahora = datetime.now()
    filas_scoring = []
    for r in leads.itertuples(index=False):
        senales = senales_lead(r._asdict(), consolidadas.get(r.lead_id, {}), ahora)
        score, comp, banda = puntuar(senales)
        filas_scoring.append((r.lead_id, r.empresa_id, score, banda, json.dumps(comp, ensure_ascii=False), json.dumps(senales)))
    conn.executemany("INSERT INTO scoring (lead_id, empresa_id, score_total, banda, componentes_json, senales_json) VALUES (?,?,?,?,?,?)", filas_scoring)

    n_asig = _asignar_asesores(conn)
    conn.execute("INSERT INTO ejecuciones_pipeline (ejecutado_en, stats_json) VALUES (?,?)",
                 (ahora.isoformat(timespec="seconds"), json.dumps({"leads": len(leads), "asignaciones": n_asig})))
    conn.commit()

    stats = {
        "empresas": 3, "puntos_venta": len(pvs), "asesores": len(asesores),
        "catalogo": len(catalogo), "disponibilidad": len(disp), "leads": len(leads),
        "conversaciones": len(conversaciones), "extracciones": len(extracciones),
        "scoring": len(filas_scoring), "asignaciones": n_asig,
    }
    conn.close()
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return stats


if __name__ == "__main__":
    run()
