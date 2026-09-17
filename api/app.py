"""API — FastAPI sobre data/motos.db. Aislamiento: TODA consulta de datos
exige `empresa` y filtra por ella; no existe endpoint que cruce empresas.
Ejecución: uvicorn api.app:app --port 8000
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "motos.db"

app = FastAPI(title="Motos y Servicios — Leads IA", version="1.0")


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def exigir_empresa(empresa: str | None) -> str:
    if not empresa or empresa not in ("EMP-01", "EMP-02", "EMP-03"):
        raise HTTPException(400, "Parámetro 'empresa' obligatorio (EMP-01|EMP-02|EMP-03)")
    return empresa


@app.get("/api/health")
def health():
    return {"ok": DB.exists(), "db": str(DB)}


@app.get("/api/meta")
def meta(empresa: str | None = None):
    with conn() as c:
        emp = [dict(r) for r in c.execute("SELECT empresa_id, nombre FROM empresas")]
        asesores = [
            dict(r) for r in c.execute(
                """SELECT asesor_id, nombre, punto_venta_id, empresa_id, capacidad_diaria_leads
                   FROM asesores WHERE activo=1 AND (? IS NULL OR empresa_id=?)""",
                (empresa, empresa),
            )
        ]
        pvs = [dict(r) for r in c.execute(
            "SELECT punto_venta_id, empresa_id, ciudad FROM puntos_venta WHERE ? IS NULL OR empresa_id=?",
            (empresa, empresa),
        )]
    return {"empresas": emp, "asesores": asesores, "puntos_venta": pvs}


@app.get("/api/leads-del-dia")
def leads_del_dia(
    empresa: str | None = Query(None, description="EMP-01|EMP-02|EMP-03 (obligatorio)"),
    asesor: str | None = Query(None, description="filtrar por asesor asignado"),
    banda: str | None = Query(None, pattern="^(Alta|Media|Baja)$"),
    limite: int = Query(100, le=500),
):
    emp = exigir_empresa(empresa)
    q = """
        SELECT s.lead_id, l.nombre_cliente, l.telefono_e164, l.ciudad_canonica,
               l.canal, l.canales_merged, l.punto_venta_id, l.estado_gestion,
               l.fecha_registro_iso, l.modelo_interes_texto, l.sku_sugerido,
               c.marca, c.linea, c.precio_lista,
               e.cuota_inicial, e.cuota_inicial_monto, e.forma_pago, e.intencion,
               e.objecion_principal, e.pidio_cita, e.pidio_cotizacion,
               s.score_total, s.banda, s.componentes_json, s.asignado_asesor_id
        FROM scoring s
        JOIN leads l   ON l.lead_id = s.lead_id AND l.empresa_id = s.empresa_id
        LEFT JOIN catalogo c ON c.sku = l.sku_sugerido
        LEFT JOIN extracciones_ia e ON e.lead_id = l.lead_id
        WHERE s.empresa_id = ? AND l.es_duplicado = 0
    """
    params: list = [emp]
    if asesor:
        q += " AND s.asignado_asesor_id = ?"
        params.append(asesor)
    if banda:
        q += " AND s.banda = ?"
        params.append(banda)
    # leads gestionables primero (los cerrados/descartados al final)
    q += " ORDER BY CASE WHEN l.estado_gestion IN ('Descartado') THEN 1 ELSE 0 END, s.score_total DESC LIMIT ?"
    params.append(limite)

    with conn() as c:
        rows = [dict(r) for r in c.execute(q, params)]
    for r in rows:
        r["razones"] = [k for k, v in json.loads(r.pop("componentes_json") or "{}").items() if v > 0]
    return {"empresa": emp, "n": len(rows), "leads": rows}


@app.get("/api/lead/{lead_id}")
def detalle_lead(lead_id: str, empresa: str | None = Query(None)):
    emp = exigir_empresa(empresa)
    with conn() as c:
        lead = c.execute(
            """SELECT * FROM leads WHERE lead_id=? AND empresa_id=?""", (lead_id, emp)
        ).fetchone()
        if not lead:
            raise HTTPException(404, "Lead no encontrado en esta empresa")
        lead = dict(lead)
        score = dict(c.execute("SELECT score_total, banda, componentes_json, asignado_asesor_id FROM scoring WHERE lead_id=?", (lead_id,)).fetchone() or {})
        convs = [dict(r) for r in c.execute(
            """SELECT conversacion_id, fecha_inicio_iso, n_mensajes FROM conversaciones
               WHERE lead_id=? ORDER BY fecha_inicio_iso DESC""", (lead_id,))]
        exts = [dict(r) for r in c.execute(
            "SELECT * FROM extracciones_ia WHERE lead_id=?", (lead_id,))]
    score["razones"] = [k for k, v in json.loads(score.get("componentes_json") or "{}").items() if v > 0]
    score.pop("componentes_json", None)
    return {"empresa": emp, "lead": lead, "scoring": score, "conversaciones": convs, "extracciones": exts}


@app.get("/api/tablero")
def tablero(empresa: str | None = Query(None)):
    emp = exigir_empresa(empresa)
    with conn() as c:
        kpi = dict(c.execute(
            """SELECT COUNT(*) leads,
                      SUM(CASE WHEN banda='Alta' THEN 1 ELSE 0 END) alta,
                      SUM(CASE WHEN banda='Media' THEN 1 ELSE 0 END) media,
                      SUM(CASE WHEN banda='Baja' THEN 1 ELSE 0 END) baja,
                      SUM(CASE WHEN (fecha_primer_contacto_iso IS NULL OR fecha_primer_contacto_iso='')
                        AND estado_gestion='Sin gestión' THEN 1 ELSE 0 END) sin_tocar
               FROM scoring s JOIN leads l ON l.lead_id=s.lead_id AND l.empresa_id=s.empresa_id
               WHERE s.empresa_id=? AND l.es_duplicado=0""",
            (emp,),
        ).fetchone())
        por_canal = {r["canal"]: r["n"] for r in c.execute(
            """SELECT canal, COUNT(*) n FROM leads WHERE empresa_id=? AND es_duplicado=0 GROUP BY canal""", (emp,))}
        por_pv = [dict(r) for r in c.execute(
            """SELECT l.punto_venta_id, COUNT(*) n, ROUND(AVG(s.score_total),1) score_promedio
               FROM leads l JOIN scoring s ON s.lead_id=l.lead_id AND s.empresa_id=l.empresa_id
               WHERE l.empresa_id=? AND l.es_duplicado=0 GROUP BY l.punto_venta_id""", (emp,))]
        calidad = dict(c.execute(
            """SELECT (SELECT COUNT(*) FROM rechazos) rechazos,
                      (SELECT COUNT(*) FROM extracciones_ia WHERE metodo='llm') ext_llm,
                      (SELECT COUNT(*) FROM extracciones_ia WHERE metodo='regex') ext_regex"""
        ).fetchone())
    return {"empresa": emp, "kpi": kpi, "por_canal": por_canal, "por_punto_venta": por_pv, "calidad": calidad}


@app.post("/api/pipeline/run")
def pipeline_run(sin_ia: bool = False):
    """Un disparo: ingesta → normalización → extracción IA → scoring → BD."""
    r = subprocess.run(
        [sys.executable, "pipeline.py", "--run"] + (["--sin-ia"] if sin_ia else []),
        capture_output=True, text=True, cwd=ROOT,
    )
    if r.returncode != 0:
        raise HTTPException(500, f"pipeline falló: {r.stdout[-500:]} {r.stderr[-500:]}")
    try:
        return {"ok": True, "resultado": json.loads(r.stdout.splitlines()[-1])}
    except (json.JSONDecodeError, IndexError):
        return {"ok": True, "log": r.stdout[-1000:]}
