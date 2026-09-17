"""T4.3 — Tests de aislamiento por empresa, capacidad e idempotencia.
Ejecución: python tests/test_bd.py  (requiere BD cargada: python -m pipeline.cargar_bd)
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    conn = sqlite3.connect(ROOT / "data" / "motos.db")
    ok = True

    # 1) Aislamiento: ningún lead puntúa/aparece en scoring de otra empresa
    for emp in ("EMP-01", "EMP-02", "EMP-03"):
        otros = conn.execute(
            """SELECT COUNT(*) FROM leads l WHERE l.empresa_id != ?
               AND l.lead_id IN (SELECT lead_id FROM scoring WHERE empresa_id = ?)""",
            (emp, emp),
        ).fetchone()[0]
        print(f"{emp}: scoring cruzado con otras empresas: {otros}")
        ok &= otros == 0

    # 2) Asignaciones respetan empresa del asesor == empresa del lead
    mal = conn.execute(
        """SELECT COUNT(*) FROM scoring s
           JOIN asesores a ON a.asesor_id = s.asignado_asesor_id
           JOIN leads l ON l.lead_id = s.lead_id
           WHERE a.empresa_id != s.empresa_id OR l.empresa_id != s.empresa_id"""
    ).fetchone()[0]
    print(f"asignaciones que rompen aislamiento: {mal}")
    ok &= mal == 0

    # 3) Capacidad diaria respetada
    over = conn.execute(
        """SELECT COUNT(*) FROM (
             SELECT asignado_asesor_id aid, COUNT(*) n FROM scoring
             WHERE asignado_asesor_id IS NOT NULL GROUP BY asignado_asesor_id) x
           JOIN asesores a ON a.asesor_id = x.aid WHERE x.n > a.capacidad_diaria_leads"""
    ).fetchone()[0]
    print(f"asesores sobrecargados: {over}")
    ok &= over == 0

    # 4) Idempotencia: re-ejecutar la carga no duplica filas
    r = subprocess.run([sys.executable, "-m", "pipeline.cargar_bd"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    n = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
         for t in ("leads", "conversaciones", "extracciones_ia", "scoring", "rechazos")}
    print(f"conteos tras re-ejecución: {n}")
    ok &= n["leads"] == 1501 and n["scoring"] == 1501 and n["extracciones_ia"] == 665

    print("\nRESULTADO:", "TODOS LOS TESTS PASAN" if ok else "FALLAN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
