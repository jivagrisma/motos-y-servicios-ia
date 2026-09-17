# Plan — Assessment Analista de IA: Motos y Servicios de Colombia S.A.S.

**Fecha**: 2026-09-17 · **Presupuesto de tiempo**: 8 horas hasta despliegue · **Metodología**: Kiro Spec-Driven (Requirements → Design → Tasks)

---

## 0. Diagnóstico de datos (verificado, no asumido)

| Archivo | Hallazgos reales |
|---|---|
| leads.csv (1.503) | canal y estado en 9-10 variantes de casing + 1 canal vacío; ≥5 formatos de fecha, ~830 en slash con 300 día-primero, 152 US mes-primero, **481 ambiguas**; teléfonos en 3 formatos válidos y 1 inválido (6 dígitos); ~15 ciudades con múltiples grafías, 79 vacías; modelo matchea catálogo solo 909/1.503 (typos, sufijo "2026", solo-marca/línea, 80 vacíos); 700 emails vacíos; 2 lead_id duplicados |
| conversaciones.json (677) | todas WhatsApp; 3-8 mensajes c/u; **12 huérfanas** (lead_id inexistente); 25 leads con 2 conversaciones; 473 leads WhatsApp sin conversación |
| catalogo_motos.csv (24) | limpio; `modelo_cotizado` del histórico = "marca + línea" concatenadas → el join requiere concatenar |
| asesores.csv (42) | 2 inactivos; mapping PV↔empresa consistente con leads; capacidad 12-25/día |
| historico_cierres.csv (2.200) | señal de calibración medida: global 9,0% cierre · <24h 11,4% vs 6,8% · cita 11,0% vs 8,1% · cuota manifiesta 10,9% vs 8,1% · contado 11,0% vs 7,7% · **cita+<24h 14,4%** · peor combinación 5,2% · 316 horas vacías (179 = Sin gestión) |
| Duplicados | 141 teléfonos repetidos; 92 en >1 canal; **91 en >1 empresa** → deduplicar solo dentro de cada empresa_id |

---

## 1. Requirements (QUÉ y para qué — lenguaje de negocio)

### R1 — Problema de negocio
El gerente comercial pierde ventas por dos cifras: **4/10 leads no se tocan en 24h** y **se cierra <1 de cada 10 gestionados**. La información valiosa (moto, cuota, forma de pago) queda enterrada en WhatsApp. El entregable central es la **lista priorizada de gestión diaria por asesor** que mueva esas dos cifras.

- **R1.1** Todo lead nuevo entra a la lista del día con un score explicable (0-100) y etiqueta Alta/Media/Baja.
- **R1.2** El score usa las variables que el histórico demuestra que separan cierres de perdidos (validado en sección 0), no intuición.
- **R1.3** La vista "Mis leads de hoy" le muestra al asesor, por prioridad: quién es, cómo contactarlo, qué quiere (lo extraído del chat), y por qué está arriba en la lista. Sin jerga técnica.

### R2 — Datos y calidad
- **R2.1** Ingesta sin intervención manual de los 5 archivos.
- **R2.2** Normalización: teléfono → E.164 Colombia (+57…), ciudad canónica, fechas ISO-8601, modelo → SKU del catálogo.
- **R2.3** Deduplicación cross-channel (misma persona por WhatsApp/Meta/Web) **dentro de cada empresa** — nunca cruzando empresas (aislamiento).
- **R2.4** Las inconsistencias detectadas (sección 0) se resuelven con reglas documentadas, no a mano.

### R3 — IA (extracción)
- **R3.1** De cada conversación WhatsApp extraer con LLM, estructurado: modelo de interés, cuota inicial/presupuesto, forma de pago (contado/crédito), intención declarada, objeción principal, pidió cita o cotización.
- **R3.2** Salida validada (schema estricto); toda extracción cita la conversación de origen (trazabilidad).

### R4 — Scoring
- **R4.1** Score ponderado explicable: cada componente aporta puntos visibles y su peso se justifica con el lift medido sobre historico_cierres.csv (ej.: cita+<24h → 14,4% vs 5,2% peor caso ≈ 2,7×).
- **R4.2** Validación obligatoria: backtest del score sobre el histórico mostrando tasa de cierre por banda de score (debe ser monótona: Alta > Media > Baja). Si no lo es, se recalibra.

### R5 — Base de datos y aislamiento
- **R5.1** Persistencia relacional con modelo propio (SQLite en dev por velocidad; portable a Postgres).
- **R5.2** Aislamiento estricto por empresa_id en pipeline, API y vista final. Un lead de EMP-02 jamás aparece en una consulta de EMP-01.

### R6 — Automatización y producto
- **R6.1** Pipeline de un solo disparo: `python pipeline.py --run` (o endpoint `/api/pipeline/run`) ejecuta ingesta→normalización→IA→scoring→BD.
- **R6.2** URL pública con tablero + vista "Mis leads de hoy" filtrable por asesor/empresa.
- **R6.3** Mobile-first (el asesor lo usa desde el celular en piso de venta).

### R7 — Entrega
Repo con historial real de commits, README con decisiones/supuestos, diagrama de arquitectura, 8 diapositivas máx, despliegue estable el día de la sustentación.

### Fuera de alcance (declarado)
Autenticación real de asesores, escritura al CRM productivo, reentrenamiento de modelos, CRM móvil completo, datos reales.

---

## 2. Design (CÓMO)

### 2.1 Arquitectura

```
datasets/ ──► pipeline.py (un disparo) ──► SQLite (motos.db)
              1. ingesta (5 archivos)          │
              2. normalización                 │   FastAPI (puerto 8000)
                 (tel/ciudad/fecha/modelo/     ├──► /api/leads-del-dia?empresa&asesor
                  dedup intra-empresa)         ├──► /api/tablero?empresa
              3. extracción LLM (677 convs,    └──► /api/pipeline/run
                 JSON estricto + fallback regex)
              4. scoring (pesos calibrados     Next.js (puerto 3000)
                 vs histórico + backtest)      └──► "Mis leads de hoy" + tablero
              5. carga BD (upsert idempotente)
```

**Stack**: Python 3 (pandas + sqlite3 + httpx para LLM) · FastAPI · Next.js (App Router, TypeScript) · SQLite archivo incluido en la imagen → **un solo estado**, cero dependencias externas en runtime salvo la key del LLM (solo se usa en build/pipeline, no en la vista).

### 2.2 Decisiones clave (con justificación de negocio)

| # | Decisión | Por qué (frase de negocio) |
|---|---|---|
| D1 | SQLite, no Postgres/Supabase | En 8 horas lo que arriesga la URL pública es la infra externa; SQLite embebido en el contenedor elimina un modo de falla completo y sigue siendo SQL relacional con modelo propio (cumple la rúbrica). Migrar a Postgres queda documentado como siguiente paso. |
| D2 | LLM vía **Vertex AI `gemini-2.5-flash`** con salida estructurada (`response_schema`), autenticado con Application Default Credentials (**cero llaves en el repo**) + fallback determinista por regex | La extracción es el componente de IA (20 pts); modelo estable recomendado por Google para alto volumen/baja latencia; ADC elimina gestión de secrets; el fallback garantiza que el pipeline corre (y la demo vive) aunque la cuota/región fallen. |
| D3 | Batch de 677 conversaciones en el pipeline (no on-demand) | Costo y latencia acotados; la lista del día se genera una vez, no por clic. |
| D4 | Score = suma ponderada de componentes binarios/escalados, pesos derivados del lift del histórico | Explicable en sustentación: "cada punto del score corresponde a un incremento real de probabilidad de cierre medido en 2.200 casos". |
| D5 | Deduplicación intra-empresa por teléfono normalizado | El mismo celular en EMP-01 y EMP-02 son dos clientes distintos (91 casos): fusionarlos rompería el aislamiento. Dentro de la empresa, se consolida el historial multicanal en un solo lead maestro. |
| D6 | Fechas slash ambiguas (481) → día-primero (convención Colombia), documentado como supuesto | Asumir en silencio resta puntos; preguntar por cada caso es inviable. Se deja registrado en supuestos y no afecta al orden de prioridad (misma incertidumbre ±1 día). |
| D7 | 12 conversaciones huérfanas → tabla de rechazos con motivo, visibles en el tablero de calidad | "El pipeline detectó y no ignoró" vale más que fingir datos limpios. |
| D8 | Next.js para la vista + FastAPI para API en dos servicios Cloud Run | Stack de experiencia previa (velocidad de desarrollo); separación limpia pipeline/API/UI que se explica en 1 frase. |

### 2.3 Esquema DDL (resumen)

```sql
empresas(empresa_id PK, nombre)
puntos_venta(punto_venta_id PK, empresa_id FK, ciudad)
asesores(asesor_id PK, nombre, punto_venta_id FK, empresa_id FK,
         capacidad_diaria, activo)
catalogo(sku PK, marca, linea, cilindraje, segmento, precio_lista,
         unidades_disponibles)
catalogo_disponibilidad(sku FK, punto_venta_id FK)          -- PV|PV|... normalizado a filas
leads(lead_id PK, telefono_e164, email, ciudad_canonica,
      empresa_id FK, punto_venta_id FK, canal, fecha_registro_iso,
      estado_gestion, campania, modelo_texto_original,
      sku_sugerido FK nullable, confianza_match,
      lead_maestro_id FK nullable,                          -- dedup intra-empresa
      es_duplicado INTEGER)
conversaciones(conversacion_id PK, lead_id FK, canal, fecha_inicio_iso,
               n_mensajes)
extracciones_ia(conversacion_id PK FK, modelo_sugerido, cuota_inicial,
               forma_pago, intencion, objecsion_principal,
               pidio_cita, pidio_cotizacion, metodo TEXT,        -- 'llm'|'regex'
               json_original TEXT)
scoring(lead_id PK FK, score_total, banda, componentes_json,   -- explicable
        asignado_asesor_id FK nullable, fecha_asignacion)
rechazos(tabla PK autoincrement, archivo, registro_id, motivo, detalle)
```
Todas las consultas de API/vista llevan `WHERE empresa_id = :empresa` sin excepción.

### 2.4 Contrato API/vista

- `GET /api/leads-del-dia?empresa=EMP-01&asesor=AS-003` → leads priorizados con score, banda, componentes en lenguaje comercial ("pidió cita", "respondió rápido"), datos de contacto y extracción IA.
- `GET /api/tablero?empresa=EMP-01` → KPIs: leads hoy, % sin tocar >24h, distribución por banda, por canal, calidad de datos (rechazos).
- `POST /api/pipeline/run` → dispara el pipeline completo.
- Vista Next.js: selector empresa → punto de venta/asesor → lista ordenada por score; tarjeta de lead expandible con el "por qué" del score en texto plano; tablero resumen.

### 2.5 Puntos de integración entre fases
- F1→F2: leads normalizados + sku_sugerido alimentan el prompt de extracción (el LLM recibe catálogo como lista cerrada).
- F2→F4: extracciones (cuota, forma de pago, cita) son entradas del score.
- F3 independiente: calibración solo contra histórico, ejecutable y verificable por separado (backtest).
- F4→F5: scoring persistido; asignación por capacidad del asesor (asesores.csv).

---

## 3. Tasks (por fase, verificables)

### Fase 1 — Datos & Limpieza (EDA + Normalización) ✅ (2026-09-17)
- [x] T1.1 Repo git init + estructura `pipeline/`, `api/`, `web/`, `docs/`, `datasets/` + commit inicial. *(verificación: `git log`)*
- [x] T1.2 `ingesta.py`: carga de los 5 archivos a DataFrames. *(verificación: conteos = 1503/677/24/42/2200 ✔)*
- [x] T1.3 `normalizar.py`: teléfono→E.164, ciudad→canónica, fechas→ISO-8601, canal/estado canónicos. *(1.500 teléfonos válidos, 1 rechazo; 79 ciudades vacías de origen; 5 formatos de fecha resueltos)*
- [x] T1.4 `match_modelo.py`: matching en cascada exacto→fuzzy→línea. *(1.259/1.501 = 84% con SKU; marca-sola y familia ambigua documentadas sin forzar)*
- [x] T1.5 `dedup.py`: intra-empresa por teléfono E.164. *(49 duplicados consolidados; 91 cross-empresa no fusionados por aislamiento)*
- [x] T1.6 Reporte de calidad: `docs/calidad_fase1.md` + `data/processed/rechazos.json` (96 rechazos con motivo). Spot-check de 8 casos fuzzy + 5 leads de control correcto.

### Fase 2 — Extracción IA ✅ (2026-09-17)
- [x] T2.1 `extraer_ia.py`: Vertex AI gemini-2.5-flash, schema JSON estricto, 8 workers con client thread-local. *(665/665 conversaciones con método `llm`, 0 fallbacks por error)*
- [x] T2.2 Fallback regex determinista implementado y probado (se activó en el piloto antes de corregir el threading; contrato idéntico).
- [x] T2.3 Validación: toda conversación produce registro con schema válido o rechazo.
- [x] T2.4 Muestra manual de 6 conversaciones vs extracción (lado a lado): 6/6 coherentes; caso borde "0 palos" documentado. Señales: 201 citas, 288 cuotas manifiestas, 55 contado.

### Fase 3 — Priorización & Scoring ✅ (2026-09-17)
- [x] T3.1 `calibrar.py` → `docs/calibracion.json` (lift reproducible por señal y combinación).
- [x] T3.2 `scoring.py`: score 0-100, pesos ∝ lift medido, 8 componentes explicables en español.
- [x] T3.3 Backtest monótono: **Alta 13,4% > Media 8,0% > Baja 5,4%** (2,5× entre extremos, global 8,9%) → `docs/backtest.json`.
- [x] T3.4 Documentación de calibración para sustentación (en /sustentacion, ver commit).

### Fase 4 — Base de Datos ✅ (2026-09-17)
- [x] T4.1 `pipeline/ddl.sql`: 11 tablas con FKs e índices por empresa.
- [x] T4.2 `pipeline/cargar_bd.py`: carga limpia transaccional idempotente + asignación por capacidad (614 leads asignados).
- [x] T4.3 `tests/test_bd.py`: aislamiento 0 fugas en las 3 empresas, 0 asignaciones cruzadas, 0 asesores sobrecargados, idempotencia verificada (2 ejecuciones = mismos conteos). **TODOS PASAN.**

### Fase 5 — Automatización & API/Frontend ⬜
- [ ] T5.1 `pipeline.py --run`: orquesta F1→F4 en un comando, con log por etapa y código de salida.
- [ ] T5.2 FastAPI: endpoints 2.4 + filtro empresa obligatorio (400 si falta).
- [ ] T5.3 Next.js: vista "Mis leads de hoy" (mobile-first) + tablero.
- [ ] T5.4 Verificación con Playwright CLI: navegación real, filtro por empresa/asesor, legibilidad no-técnica (screenshots). *(verificación: screenshots adjuntos a /sustentacion)*

### Fase 6 — Despliegue & Documentación ⬜
- [ ] T6.1 ~~Verificar cuota de proyectos GCP~~ **Verificado 2026-09-17**: cuenta `014D68-AABD6C-3B84F1` con 3 proyectos vinculados (viajemos-77223, esic-fabrica-ia, midyear-pattern-487319-b5) + 1 sin facturación; cupo exacto no legible por CLI pero hay espacio típico. Crear `motos-servicios-assessment-ia` sin tocar los existentes; si el create falla por cuota, tramitar aumento por Consola y reportar. Habilitar `run.googleapis.com`, `artifactregistry.googleapis.com`, `aiplatform.googleapis.com` vía CLI en el proyecto nuevo.
- [ ] T6.2 Dockerfiles (api + web) + deploy a Cloud Run, URL pública verificada con curl.
- [ ] T6.3 README (qué hace, cómo ejecutar, decisiones D1-D8, supuestos, "con más tiempo").
- [ ] T6.4 Diagrama de arquitectura final (Mermaid) + 8 diapositivas en /sustentacion.
- [ ] T6.5 Smoke test de la URL pública desplegada (Playwright).

### Material /sustentacion (en paralelo, incremental)
- [ ] decisiones.md (D1-D8 + decisiones de calibración) · supuestos.md · arquitectura.mmd · diapositivas (borrador desde F3).

---

## 4. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Cuota GCP sin cupo para proyecto nuevo | Verificar en T6.1 ANTES; fallback: desplegar en el mismo proyecto existente aislado por servicio, o VPS/Render (documentado) |
| Cuota/costo del LLM | Fallback regex garantiza pipeline completo; extracción LLM solo se corre en el pipeline, no en runtime |
| URL caída el día de la sustentación | Servicio serverless sin estado externo (SQLite embebido); smoke test previo |
| Score no monótono en backtest | Criterio de salida explícito en T3.3; recalibración es iterativa y documentada |
| 8 horas | Fases con entregable verificable independiente; si el tiempo aprieta, el orden de sacrificio es: tablero de calidad → asignación automática por capacidad → polishing UI. Nunca: aislamiento, backtest, URL pública |

---

**Estado**: ⬜ Pendiente de confirmación del usuario para iniciar Fase 1.
