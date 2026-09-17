# Notas de decisiones y su justificación (para la sustentación)

## D1 — SQLite embebido, no Postgres/Supabase/Cloud SQL
**Negocio**: en 8 horas, lo que más arriesga la URL pública del día de la sustentación es la infraestructura externa. SQLite elimina un modo de falla completo y sigue siendo SQL relacional con modelo propio (11 tablas, FKs).
**Frase de 1 línea**: "La base vive dentro del servicio; no hay nada que pueda caerse aparte del servicio mismo."
**Siguiente paso declarado**: migrar a Cloud SQL/Postgres con la misma DDL.

## D2 — Vertex AI gemini-2.5-flash con ADC + fallback regex
**Negocio**: la extracción de WhatsApp es el componente que recupera la información enterrada en los chats. Modelo estable recomendado por Google para volumen/latencia; salida JSON con schema estricto; cero llaves gestionadas (ADC/service account).
**Resultado real**: 665/665 conversaciones extraídas con LLM, 0 fallbacks. Validación manual 6/6 coherente.
**Frase**: "El asesor ya no arranca de cero: la IA lee el chat y le dice qué moto quiere, con cuánta entrada y si la quiere a crédito."

## D3 — Score ponderado explicable, no modelo entrenado
**Negocio**: el gerente necesita confiar en la lista. Cada punto del score corresponde a un aumento real de probabilidad de cierre medido en los 2.200 casos históricos:
- pidió cita +20 (cierra 10,9% vs 8,9% global) · cuota manifiesta +15 (10,9%) · compra inmediata +15 (proxy cita+cuota: 13,9%) · <24h sin contactar +15 (contacto<24h cierra 11,5% vs 6,8%) · contado +10 (11,0% vs 7,7% crédito) · multicanal +10 · modelo concreto +10 · WhatsApp +5 (9,4%).
**Backtest monótono**: Alta 13,4% > Media 8,0% > Baja 5,4% — el score separa 2,5× el extremo alto del bajo.
**Frase**: "Si hoy solo alcansas a llamar a 10, llama a los de banda Alta: cierran 2,5 veces más que los de banda Baja."

## D4 — Deduplicación solo dentro de cada empresa
**Negocio**: el CRM es compartido entre 3 empresas y cada una solo ve sus clientes. Encontramos 91 teléfonos que aparecen en 2+ empresas: fusionarlos rompería el aislamiento. Dentro de la empresa sí consolidamos (49 duplicados cross-channel).
**Frase**: "La misma persona en dos empresas son dos clientes; en una misma empresa, un solo lead con todo su historial multicanal."

## D5 — Fechas ambiguas → día primero (convención Colombia)
481 fechas con día y mes ≤12. Resolución sistemática documentada; impacto máximo ±2 días, no altera el orden de prioridad de forma relevante.

## D6 — Rechazos visibles, no descartados en silencio
96 registros rechazados con motivo (teléfono inválido, lead huérfano, fecha ilegible) — tabla `rechazos` visible en el tablero de calidad. "Detectar y reportar" > "fingir limpio".

## D7 — Dos servicios en Cloud Run (api + web)
Separación pipeline/API/UI explicable en una frase; cada uno escala independiente; URL pública HTTPS automática.

## Qué se dejó fuera (y por qué)
- **Auth de asesores real** — fuera del alcance del enunciado; el selector de asesor asume buena fe (MVP).
- **Re-entrenamiento / ML supervisado** — 2.200 filas y señal débil individual: un score explicable calibrado es más defendible que un modelo caja negra.
- **Escritura al CRM productivo** — solo lectura/enriquecimiento.
- **Citas/agenda en la UI** — la vista prioriza; el cierre sigue sucediendo por WhatsApp/teléfono.

## Casos difíciles que pueden preguntar
- "¿Por qué ese lead salió Alta?" → abrir la tarjeta: las razones están en español ("Pidió cita · Manifestó cuota inicial").
- "¿Y si el LLM se cae?" → fallback regex con el mismo contrato; el pipeline sigue (demo no muere).
- "¿Los datos de una empresa se ven desde otra?" → test automatizado: 0 fugas (tests/test_bd.py).
