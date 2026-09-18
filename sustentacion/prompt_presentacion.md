# PROMPT — Presentación ejecutiva (pegar en Claude web, adjuntando los archivos de /sustentacion)

---

Actúa como un **experto en comunicación ejecutiva + diseñador gráfico de presentaciones** con una regla de oro: **el contenido se lee desde el último asiento de una sala, sin esfuerzo**.

## Contexto

Sustentaré un assessment técnico ante un evaluador (30 min: 10 demo + 10 recorrido de código + 10 preguntas). La presentación es de **máximo 8 diapositivas**. El problema de negocio: una comercializadora de motos recibe +3.000 leads/mes, 4 de cada 10 no se tocan en 24h (ahí se pierden) y se cierra menos de 1 de cada 10 gestionados; la información valiosa queda enterrada en los chats de WhatsApp. La solución entregada: pipeline automatizado que normaliza los leads, extrae la información de los chats con IA (Vertex AI gemini-2.5-flash), asigna un **score de prioridad explicable calibrado contra 2.200 cierres históricos**, persiste en base de datos con aislamiento estricto por empresa, y publica la vista web "Mis leads de hoy" para el asesor comercial.

Los archivos que adjunto contienen TODO el contenido real: decisiones justificadas (decisiones.md), estructura y datos de las diapositivas (diapositivas.md), diagrama (arquitectura.mmd) y capturas de la aplicación (vista_*.png, url_publica_*.png). **Usa únicamente esos datos, no inventes cifras.**

## Reglas de diseño (OBLIGATORIAS — un ejemplo anterior mío salió ilegible y eso es exactamente lo que debes evitar)

1. **Tipografía grande**: títulos mínimo 36-40 pt, cuerpo mínimo 24-28 pt, cifras protagonistas 60 pt o más. Si un texto no cabe a ese tamaño, **borra texto, no reduzcas la fuente**.
2. **Máximo ~25 palabras por diapositiva** (excluyendo cifras y etiquetas de diagramas). Una idea por diapositiva. El detalle va en mi voz, no en la lámina.
3. **Nada de párrafos, viñetas largas ni tablas densas**. Una diapositiva = un mensaje + máximo 3 apoyos visuales.
4. **Las cifras son las protagonistas**: "4 de 10 leads sin tocar en 24h", "<1 de 10 cerrados", "Alta 13,4% vs Baja 5,4% (2,5×)", "665/665 conversaciones leídas con IA". Muéstralas grandes, con jerarquía visual clara.
5. **Alto contraste**, fondo limpio, una paleta de máximo 3 colores + acento (rojo para el problema, verde/azul para la solución).
6. **Diagramas grandes y simples**: redibuja el diagrama de arquitectura (pipeline → BD → API → web) con cajas grandes, flechas gruesas y máximo 8 bloques. Nada de diagramas microscópicos con texto de 10 pt. Genera los diagramas como imágenes propias, legibles, no como texto.
7. Las capturas de pantalla adjuntas deben ocupar buena parte de su diapositiva, con un pequeño texto de contexto, nunca como miniaturas.
8. Español, tono ejecutivo, cero jerga técnica innecesaria (el stack se menciona una vez, en la diapositiva de arquitectura).

## Orden lógico exigido (problema → solución → evidencia → cierre)

1. **El problema en 3 cifras** (hook: las 3 cifras gigantes del negocio).
2. **Qué construí** (una frase + diagrama de arquitectura legible).
3. **Los datos eran un desastre y los doméstiqué** (2-3 ejemplos de inconsistencias reales resueltas; rechazos visibles).
4. **La IA que lee los chats** (qué extrae + "665/665, validación manual 6/6"; opcional: extracto de un chat real con los campos extraídos).
5. **El score y su evidencia** (backtest: banda Alta 13,4% vs Baja 5,4%; por qué es explicable).
6. **La vista del asesor** (captura grande de "Mis leads de hoy"; URL visible).
7. **Ingeniería: automatización y aislamiento** (un solo disparo, CI/CD, 3 empresas sin fugas, URL pública en Cloud Run).
8. **Con más tiempo** (3-4 ítems) + cierre con las URLs.

## Entregable

Genera un archivo **PPTX** descargable (o HTML imprimible si te sale mejor) con las 8 diapositivas listas para proyectar, formato 16:9. Antes de terminar, autorevisa cada lámina contra las reglas de diseño: si alguna viola la regla de tamaño mínimo de fuente o de palabras, corrígela.

---

*(Recordatorio para mí: adjuntar decisiones.md, diapositivas.md, arquitectura.mmd y los PNG de /sustentacion; opcionalmente docs/backtest.json y docs/calibracion.json.)*
