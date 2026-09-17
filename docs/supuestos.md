# Supuestos sobre los datos sintéticos

1. **Fechas slash ambiguas** (481 casos donde día y mes son ≤12): se resuelven como **día-primero** (convención colombiana DD/MM). Cuando uno de los dos valores >12 la resolución es evidente (incluye formato US MM/DD, 152 casos). Impacto acotado: no altera el orden de prioridad de forma significativa (error máximo ±2 días en el peor caso).
2. **Misma persona en dos empresas = dos clientes distintos**: 91 teléfonos aparecen en >1 empresa. Por el aislamiento exigido del CRM compartido, la deduplicación es solo intra-empresa; no se fusiona nada cruzando empresas.
3. **Lead maestro en la fusión**: se prefiere WhatsApp > Meta Ads > Formulario Web, desempate por fecha más antigua. Justificación: WhatsApp concentra la intención declarada y la mejor tasa de cierre medida (9,5% vs 8,1%/9,0%).
4. **Teléfono válido = 10 dígitos iniciando en 3** (móvil Colombia) → E.164 `+57`. El único caso de 6 dígitos se rechaza con motivo explícito (no se inventa).
5. **Modelo "marca sola" o "familia ambigua"** ("Bajaj", "Bajaj Pulsar" → 3 SKUs posibles): no se fuerza un SKU; queda sin catálogo con etiqueta explicativa. Falsos positivos en catálogo valen más que un match forzado.
6. **Ciudades**: se mapean a un diccionario canónico de ~25 ciudades detectadas en los datos; las 79 vacías se declaran (no se imputan por punto de venta).
7. **Las 12 conversaciones huérfanas** (lead_id inexistente en leads.csv) van a la tabla de rechazos, no se descartan en silencio.
8. **historico_cierres.csv es histórico** (namespace HX-*): se usa para calibrar el score, no se mezcla con los leads operativos (LD-*).
9. **Sufijo "2026"** en modelo_interes_texto: se interpreta como año del modelo, se elimina para el matching.
