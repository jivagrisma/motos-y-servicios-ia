# Correo de entrega — Assessment Analista de IA (copiar y enviar)

**Asunto:** Entrega Assessment Analista de IA — Motos y Servicios de Colombia S.A.S. — [Tu nombre]

---

Estimado equipo,

Adjunto y enuncio los entregables del assessment para el cargo de Analista de IA, correspondientes al caso de Motos y Servicios de Colombia S.A.S.:

**Enlaces de la solución**

- Repositorio (GitHub, público): https://github.com/jivagrisma/motos-y-servicios-ia
- Solución publicada (URL pública, operativa): https://motos-web-53117453818.us-central1.run.app
- API consumible: https://motos-api-53117453818.us-central1.run.app
  - Salud: `/api/health` · Tablero: `/api/tablero?empresa=EMP-01` · Leads del día: `/api/leads-del-dia?empresa=EMP-01` (el parámetro `empresa` es obligatorio: el aislamiento entre comercializadoras se aplica en cada capa)

**Archivos adjuntos**

- `Presentación.pptx` — presentación de sustentación (8 diapositivas)
- `arquitectura-solucion.png` — diagrama de la arquitectura

**Resumen de la solución (un párrafo)**

Pipeline automatizado de un solo disparo que ingiere los 5 archivos fuente, normaliza teléfono (E.164 Colombia), ciudades, fechas y modelos contra catálogo, y deduplica leads cross-channel dentro de cada empresa. Un componente de IA (Vertex AI, gemini-2.5-flash, salida JSON con schema estricto y fallback determinista) lee las 665 conversaciones de WhatsApp y extrae modelo de interés, cuota inicial, forma de pago, intención, objeción y solicitud de cita. Cada lead recibe un score de prioridad explicable (0-100) calibrado contra los 2.200 cierres históricos — el backtest muestra que la banda Alta cierra al 13,4% frente al 5,4% de la banda Baja (2,5×) — y todo persiste en base de datos relacional con modelo propio y aislamiento estricto por empresa_id. El resultado se publica en Cloud Run: tablero comercial y vista "Mis leads de hoy" priorizada por asesor, con despliegue continuo (GitHub Actions) y runbook de operación.

**Cumplimiento de condiciones obligatorias**

- Automatización de punta a punta: `python pipeline.py --run` o `POST /api/pipeline/run`
- Repositorio con historial real de commits y README (qué hace, cómo ejecutar, decisiones, supuestos y próximos pasos)
- Base de datos relacional con DDL versionado en el repo
- URL pública operativa el día de la sustentación
- Separación por empresa verificada con tests automatizados (0 fugas)
- Sin credenciales ni datos reales en el repositorio (autenticación por Application Default Credentials / Service Account)

Quedo atento para coordinar la sustentación de 30 minutos (demo en vivo, recorrido por el código y preguntas).

Cordialmente,

[Tu nombre]
[Tu teléfono de contacto]
