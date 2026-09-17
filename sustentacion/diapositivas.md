# 8 diapositivas — borrador (pulir formato al cierre)

1. **El problema en 3 cifras** — +3.000 leads/mes · 4/10 sin tocar en 24h · <1/10 cerrados. Todo entra a una bandeja por orden de llegada y la información valiosa queda enterrada en WhatsApp.

2. **Qué construí** — La lista priorizada de gestión diaria por asesor: pipeline automatizado + IA que lee los chats + score explicable + vista web pública. (diagrama de arquitectura)

3. **Datos: lo que encontré de verdad** — 9 grafías de canal, 5 formatos de fecha (+481 ambiguas), teléfonos en 3 formatos, 91 duplicados cruzando empresas, 12 conversaciones huérfanas. Todo resuelto con reglas documentadas y 96 rechazos visibles.

4. **La IA que recupera el chat** — gemini-2.5-flash (Vertex AI) lee las 665 conversaciones y extrae: moto, cuota inicial, forma de pago, intención, objeción, cita. 665/665 con schema estricto, 0 fallos, validación manual 6/6.

5. **El score y su evidencia** — cada punto nace del histórico: cita +20, cuota +15, contado +10, rapidez +15... **Backtest: Alta 13,4% de cierre vs Baja 5,4% (2,5×)**. El score separa a los que cierran.

6. **La vista del asesor** — "Mis leads de hoy": ordenado por prioridad, con el "por qué" en español, teléfono a un toque, filtros por empresa/asesor. Mobile-first. (screenshots)

7. **Aislamiento y automatización** — 3 empresas, cero fugas (test automatizado). Pipeline de un solo disparo (`python pipeline.py --run` o `POST /api/pipeline/run`). Desplegado en Cloud Run, proyecto dedicado.

8. **Con más tiempo** — Auth real de asesores · migrar a Cloud SQL · re-entrenar score con los nuevos cierres · integración bidireccional con el CRM · alerta de leads a punto de cumplir 24h sin contacto.
