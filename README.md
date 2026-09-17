# Motos y Servicios — Lista priorizada de leads con IA

Assessment Analista de IA · Motos y Servicios de Colombia S.A.S.

**Problema de negocio**: +3.000 leads/mes gestionados por orden de llegada; 4 de cada 10 no se tocan en 24h (ahí se pierden) y se cierra menos de 1 de cada 10. La información valiosa (moto, cuota inicial, forma de pago) queda enterrada en el chat de WhatsApp.

**Solución**: pipeline automatizado de punta a punta que normaliza los leads, lee las conversaciones con IA (Vertex AI `gemini-2.5-flash`), asigna un score de prioridad explicable calibrado contra el histórico real de cierres, persiste todo en SQLite con aislamiento estricto por empresa, y publica la vista **"Mis leads de hoy"** para que cada asesor ataque primero lo que más cierra.

## URLs desplegadas (Cloud Run)

- **Web (tablero + Mis leads de hoy)**: https://motos-web-53117453818.us-central1.run.app
- **API**: https://motos-api-53117453818.us-central1.run.app (`/api/health`, `/api/tablero?empresa=EMP-01`, `/api/leads-del-dia?empresa=EMP-01`)

## CI/CD

`.github/workflows/deploy.yml`: build de ambas imágenes → deploy a Cloud Run → smoke test automático. Se dispara por push a `main` o manualmente. Runbook completo (disparo, monitoreo, verificación, reglas, rollback): `docs/runbook-deploy.md`.

```bash
gh workflow run deploy.yml --repo jivagrisma/motos-y-servicios-ia
gh run watch
```

## Arquitectura

```
datasets (5 archivos)
   │
   ▼  pipeline.py --run  (un solo disparo)
[1] Ingesta → [2] Normalización (tel +57 E.164, ciudad, fecha ISO, modelo→SKU,
               dedup intra-empresa) → [3] Extracción IA (schema JSON estricto,
               fallback regex) → [4] Scoring calibrado → [5] SQLite (11 tablas)
                                                        │
                          FastAPI (Cloud Run) ◄──────────┘
                          /api/leads-del-dia · /api/tablero · /api/pipeline/run
                                                        │
                          Next.js (Cloud Run) — "Mis leads de hoy" + tablero
```

Ver diagrama completo: `sustentacion/arquitectura.mmd`.

## Cómo ejecutar

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Pipeline completo (ingesta → normalización → IA → scoring → BD):
.venv/bin/python pipeline.py --run

# Sin llamadas al LLM (usa extracción ya calculada / fallback):
.venv/bin/python pipeline.py --run --sin-ia

# Tests de aislamiento, capacidad e idempotencia:
.venv/bin/python tests/test_bd.py

# API (dev):
.venv/bin/uvicorn api.app:app --port 8001

# Web (dev, en otro terminal):
cd web && npm install && NEXT_PUBLIC_API_URL=http://localhost:8001 npm run build && npm run start
```

La extracción con LLM requiere credenciales de GCP (Application Default Credentials):
`gcloud auth application-default login`. Sin credenciales, el pipeline usa el fallback regex.

## Decisiones (resumen — detalle en sustentacion/decisiones.md)

| # | Decisión | Por qué |
|---|---|---|
| D1 | SQLite embebido | Elimina modos de falla de infra en el MVP; DDL portable a Postgres |
| D2 | Vertex AI gemini-2.5-flash + ADC | Modelo estable para volumen/latencia; cero llaves en el repo; fallback regex |
| D3 | Score ponderado explicable | Pesos = lift medido en 2.200 cierres; backtest monótono (Alta 13,4% > Media 8,0% > Baja 5,4%) |
| D4 | Dedup intra-empresa | 91 teléfonos cruzan empresas; fusionarlos rompería el aislamiento |
| D5 | Fechas ambiguas → día-primero | Convención Colombia; impacto ≤2 días; documentado |
| D6 | Rechazos visibles | 96 registros con motivo, no descartados en silencio |
| D7 | 2 servicios Cloud Run | api + web independientes, proyecto GCP dedicado |

## Supuestos sobre los datos

Ver `docs/supuestos.md` (9 supuestos: fechas ambiguas, dedup, lead maestro, teléfono válido, marca sola sin SKU, ciudades, huérfanos, histórico separado, sufijo año).

## Verificación

- Calidad de F1: `docs/calidad_fase1.md` · calibración: `docs/calibracion.json` · backtest: `docs/backtest.json`
- Tests: `tests/test_bd.py` (aislamiento 0 fugas, capacidad, idempotencia)
- Evidencia de UI: `sustentacion/vista_*.png`

## Con más tiempo

Auth real por asesor · migración a Cloud SQL · recalibrar el score con los cierres nuevos que genere la propia lista · integración bidireccional con el CRM · alerta proactiva de leads por cumplir 24h sin contacto.

## Estructura del repo

```
pipeline/    ingesta, normalización, matching, dedup, extracción IA, calibración, scoring, carga BD
api/         FastAPI (aislamiento por empresa en cada endpoint)
web/         Next.js 16 (tablero + Mis leads de hoy)
tests/       aislamiento, capacidad, idempotencia
docs/        calidad, supuestos, calibración, backtest
sustentacion/ decisiones, arquitectura, diapositivas, screenshots
data/        outputs del pipeline + SQLite (generado)
```
