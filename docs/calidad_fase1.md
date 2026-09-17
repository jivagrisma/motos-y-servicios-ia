# Reporte de calidad — Fase 1 (2026-09-17)

Ejecutado con: `.venv/bin/python -m pipeline.fase1` (idempotente, re-ejecutable).

## Ingesta (conteos exactos contra LEEME.txt)
| Archivo | Filas |
|---|---|
| leads.csv | 1.503 ✔ |
| conversaciones.json | 677 ✔ |
| catalogo_motos.csv | 24 ✔ |
| asesores.csv | 42 ✔ |
| historico_cierres.csv | 2.200 ✔ |

## Normalización
- **2 lead_id duplicados exactos** → segundo registro a rechazos.
- **Teléfonos**: 1.501/1.501 con E.164 válido salvo 1 inválido (6 dígitos) → rechazado con motivo. Formatos resueltos: `+57 350 2258611`, `310 482 4081`, `573156610968`.
- **Ciudades**: todas las variantes gráficas resueltas (Bogotá D.C./BOGOTA/bogotá/Bogota DC → `Bogotá D.C.`; B/quilla → Barranquilla; Sta Marta → Santa Marta; etc.). Quedan 79 vacías de origen (declaradas).
- **Fechas**: 5 formatos + slash mixtos → ISO-8601. 481 ambiguas resueltas día-primero (supuesto #1).
- **Canal/estado**: 9-10 variantes de casing → 3 canales y 6 estados canónicos; 1 canal vacío → "Desconocido" + rechazo.

## Matching de modelo (contra catálogo)
| Método | Leads | Confianza |
|---|---|---|
| exacto | 1.061 | 1.0 |
| fuzzy (typos "Hnda", "Bajai", "Suzuky") | 112 | 0.82-0.97 |
| solo_línea ("CB 190R", "Navi") | 86 | 0.9 |
| marca sola ("Bajaj") | 97 | sin SKU (ambiguo por diseño) |
| familia ambigua ("Bajaj Pulsar") | 65 | sin SKU |
| vacío | 80 | — |

**Con SKU: 1.259/1.501 (84%)**. Verificación manual de 8 casos fuzzy correcta.

## Deduplicación (intra-empresa)
- **49 leads marcados como duplicados** cross-channel dentro de su empresa, consolidados en lead maestro (preferencia WhatsApp, desempate fecha más antigua).
- 91 teléfonos aparecen en >1 empresa → **no se fusionan** (aislamiento).

## Conversaciones
- 665 válidas normalizadas (fecha ISO, n_mensajes).
- **12 huérfanas** → rechazos (lead_id no existe).

## Rechazos totales: 96 (todos con archivo, registro y motivo)
Ver detalle en `data/processed/rechazos.json`.
