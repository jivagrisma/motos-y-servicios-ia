# Preguntas probables en la sustentación — con respuesta preparada

## Negocio y encuadre

**1. ¿Qué problema de negocio resuelve esto, en una frase?**
Los asesores llamaban por orden de llegada; ahora llaman por probabilidad de cierre. La lista priorizada ataca las dos cifras del gerente: los 4/10 leads sin tocar en 24h (la vista los empuja arriba con el componente de urgencia) y el <1/10 de cierre (banda Alta cierra 13,4% vs 5,4% la Baja, medido en backtest).

**2. ¿Cómo sabe que su score funciona y no es una intuición?**
Backtest sobre los 2.200 cierres históricos: apliqué el score a ese histórico y la tasa de cierre por banda es monótona — Alta 13,4% > Media 8,0% > Baja 5,4%. Es reproducible con un comando (`python -m pipeline.scoring` → `docs/backtest.json`).

**3. ¿Por qué no entrenó un modelo de ML?**
El enunciado no lo exige y con 2.200 filas y señales débiles individualmente, un score explicable calibrado por lift es más defendible: cada punto se puede rastrear a una tasa de cierre real medida. Un modelo caja negra no habría aguantado la pregunta "¿por qué este lead es Alta?".

**4. ¿Cuánto le cuesta esto a la empresa?**
El batch completo (665 conversaciones cortas con gemini-2.5-flash) costó menos de $1 USD. Cloud Run escala a cero: sin tráfico no factura prácticamente nada.

## Componente de IA

**5. ¿Por qué gemini-2.5-flash y no otro modelo?**
Es el modelo estable que Google recomienda para alto volumen y baja latencia; soporta salida JSON con schema estricto (respuesta validada, no texto libre que hay que parsear). Y por qué Vertex AI y no una API key: autenticación por Application Default Credentials — cero llaves en el repo, cero rotación manual.

**6. ¿Qué pasa si el LLM se cae o la cuota se agota?**
Hay un fallback determinista por regex con el mismo contrato de salida; el pipeline no se detiene y la vista sigue funcionando. En la ejecución real no hizo falta: 665/665 con LLM.

**7. ¿Cómo evita que la IA invente (alucinaciones)?**
Tres barreras: el prompt restringe a lo MANIFESTADO por el cliente (solo mensajes con emisor=cliente), el schema enum-cerrado para forma de pago/intención, y validé manualmente una muestra lado a lado (6/6 correctas). El caso borde encontrado ("0 palos" como cuota SI con monto visible) quedó documentado.

**8. ¿Qué extrajo de los chats exactamente?**
Modelo de interés, cuota inicial (SI/NO + monto textual), forma de pago, intención declarada, objeción principal, y si pidió cita o cotización. Ejemplo real: objeción "Necesita consultar con esposa" — eso le ahorra al asesor media llamada.

## Datos y calidad

**9. ¿Qué inconsistencias encontró en los datos?**
Reales y verificadas: 9 grafías de canal, 5 formatos de fecha más 481 fechas slash ambiguas, teléfonos en 3 formatos válidos + 1 inválido, ~15 ciudades con múltiples grafías, 2 lead_id duplicados, 12 conversaciones huérfanas. Todo se resolvió con reglas documentadas, no a mano.

**10. ¿Por qué deduplica solo dentro de cada empresa?**
Encontré 91 teléfonos presentes en 2+ empresas. El CRM compartido exige que cada empresa solo vea sus clientes: si fusiono ese duplicado cruzando empresas, rompo el aislamiento. Dentro de la empresa sí consolido (49 duplicados cross-channel) prefiriendo WhatsApp como lead maestro.

**11. ¿Qué hace con los registros que no puede salvar?**
Nada se descarta en silencio: 96 rechazos con archivo, registro y motivo en la tabla `rechazos`, visible en el tablero de calidad. Detectar y reportar es parte del ejercicio.

**12. ¿Por qué SQLite y no PostgreSQL?**
Es relacional con modelo propio (11 tablas, FKs), cumple la condición. En un MVP de horas, una base administrada es un modo de falla extra para la URL pública. La DDL es portable a Postgres sin cambios — está versionada en `pipeline/ddl.sql` y es el siguiente paso declarado.

## Arquitectura e ingeniería

**13. ¿Cómo garantiza el aislamiento por empresa?**
En tres capas: BD (todas las consultas filtran empresa_id), API (parámetro empresa obligatorio — 400 si falta) y vista (selector de empresa). Y hay test automatizado que lo prueba: 0 fugas, 0 asignaciones cruzadas (`tests/test_bd.py`).

**14. ¿Cómo se ejecuta todo el flujo?**
Un disparo: `python pipeline.py --run` o `POST /api/pipeline/run`. Idempotente: re-ejecutar no duplica filas (testeado). En producción además hay CI/CD: push a main → GitHub Actions → build → deploy → smoke test automático.

**15. ¿Por qué dos servicios (API y web) separados?**
Separación de responsabilidades que se explica en una frase: el pipeline y los datos viven en el API; la experiencia del asesor en la web. Escalan y se despliegan independientes. La API es además consumible por terceros, como pide el enunciado.

**16. ¿Cómo asigna leads a asesores?**
Por punto de venta y empresa, en orden de score descendente, respetando la capacidad diaria de cada asesor (asesores.csv). Test incluido: 0 asesores sobrecargados.

**17. ¿Qué hay de las credenciales? ¿Dónde están las llaves?**
No hay llaves en el repo: Vertex AI usa Application Default Credentials; el CI/CD usa una service account con permisos mínimos cuya key vive solo en GitHub Secrets (y se rotaría igual). Es condición de descalificación y está cubierta.

## Producto y visión

**18. ¿Por qué no hizo un chat conversacional con IA, siendo lo de hoy conversacional?**
La experiencia conversacional ya existe: es el WhatsApp del cliente. Nuestro componente IA la MINA y la convierte en estructura accionable para el asesor, cuya tarea es escanear y llamar, no chatear. Lo que sí valdría la pena (roadmap): un copiloto que redacte el primer mensaje usando lo extraído — eso mueve la tasa de cierre directamente.

**19. ¿Qué haría con más tiempo?**
Auth real por asesor, migración a Cloud SQL, recalibrar el score con los cierres nuevos que genere la propia lista (el sistema aprendería de su propio impacto), integración bidireccional con el CRM, y alerta proactiva de leads por cumplir 24h sin contacto.

**20. Si mañana entran 3.000 leads nuevos, ¿funciona igual?**
Sí: el pipeline es idempotente y el único cuello es el batch de LLM (~665 conversaciones en minutos, lineal). Para volumen real, colas y ejecución programada (cron/cloud scheduler), ya previsto en el diseño de un solo disparo.
