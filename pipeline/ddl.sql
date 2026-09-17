-- Esquema propio — Motos y Servicios (SQLite dev, portable a PostgreSQL)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS empresas (
  empresa_id TEXT PRIMARY KEY,
  nombre     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS puntos_venta (
  punto_venta_id TEXT PRIMARY KEY,
  empresa_id     TEXT NOT NULL REFERENCES empresas(empresa_id),
  ciudad         TEXT
);

CREATE TABLE IF NOT EXISTS asesores (
  asesor_id            TEXT PRIMARY KEY,
  nombre               TEXT NOT NULL,
  punto_venta_id       TEXT NOT NULL REFERENCES puntos_venta(punto_venta_id),
  empresa_id           TEXT NOT NULL REFERENCES empresas(empresa_id),
  capacidad_diaria_leads INTEGER NOT NULL,
  activo               INTEGER NOT NULL DEFAULT 1,
  fecha_ingreso        DATE
);

CREATE TABLE IF NOT EXISTS catalogo (
  sku                 TEXT PRIMARY KEY,
  marca               TEXT NOT NULL,
  linea               TEXT NOT NULL,
  cilindraje          INTEGER,
  segmento            TEXT,
  precio_lista        INTEGER,
  unidades_disponibles INTEGER
);

CREATE TABLE IF NOT EXISTS catalogo_disponibilidad (
  sku              TEXT NOT NULL REFERENCES catalogo(sku),
  punto_venta_id   TEXT NOT NULL REFERENCES puntos_venta(punto_venta_id),
  PRIMARY KEY (sku, punto_venta_id)
);

CREATE TABLE IF NOT EXISTS leads (
  lead_id                TEXT PRIMARY KEY,
  telefono_e164          TEXT,
  email                  TEXT,
  nombre_cliente         TEXT,
  ciudad_canonica        TEXT,
  empresa_id             TEXT NOT NULL REFERENCES empresas(empresa_id),
  punto_venta_id         TEXT NOT NULL REFERENCES puntos_venta(punto_venta_id),
  canal                  TEXT NOT NULL,
  canales_merged         TEXT,
  fecha_registro_iso     TEXT,
  fecha_primer_contacto_iso TEXT,
  estado_gestion         TEXT,
  campania               TEXT,
  modelo_interes_texto   TEXT,
  sku_sugerido           TEXT REFERENCES catalogo(sku),
  confianza_match        REAL,
  metodo_match           TEXT,
  es_duplicado           INTEGER NOT NULL DEFAULT 0,
  lead_maestro_id        TEXT
);
CREATE INDEX IF NOT EXISTS idx_leads_empresa ON leads(empresa_id);

CREATE TABLE IF NOT EXISTS conversaciones (
  conversacion_id TEXT PRIMARY KEY,
  lead_id         TEXT NOT NULL REFERENCES leads(lead_id),
  canal           TEXT,
  fecha_inicio_iso TEXT,
  n_mensajes      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_conv_lead ON conversaciones(lead_id);

CREATE TABLE IF NOT EXISTS extracciones_ia (
  conversacion_id    TEXT PRIMARY KEY REFERENCES conversaciones(conversacion_id),
  lead_id            TEXT NOT NULL REFERENCES leads(lead_id),
  modelo_interes     TEXT,
  cuota_inicial      TEXT CHECK (cuota_inicial IN ('SI','NO','NO_INFORMA')),
  cuota_inicial_monto TEXT,
  forma_pago         TEXT CHECK (forma_pago IN ('contado','credito','no_informa')),
  intencion          TEXT,
  objecion_principal TEXT,
  pidio_cita         INTEGER NOT NULL DEFAULT 0,
  pidio_cotizacion   INTEGER NOT NULL DEFAULT 0,
  metodo             TEXT NOT NULL,          -- 'llm' | 'regex'
  json_original      TEXT
);
CREATE INDEX IF NOT EXISTS idx_ext_lead ON extracciones_ia(lead_id);

CREATE TABLE IF NOT EXISTS scoring (
  lead_id            TEXT PRIMARY KEY REFERENCES leads(lead_id),
  empresa_id         TEXT NOT NULL REFERENCES empresas(empresa_id),
  score_total        INTEGER NOT NULL,
  banda              TEXT NOT NULL CHECK (banda IN ('Alta','Media','Baja')),
  componentes_json   TEXT NOT NULL,          -- explicable: {"Pidió cita": 20, ...}
  senales_json       TEXT NOT NULL,          -- señales booleanas de origen
  asignado_asesor_id TEXT REFERENCES asesores(asesor_id),
  fecha_asignacion   TEXT
);
CREATE INDEX IF NOT EXISTS idx_scoring_empresa ON scoring(empresa_id, score_total DESC);

CREATE TABLE IF NOT EXISTS rechazos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  archivo     TEXT NOT NULL,
  registro_id TEXT NOT NULL,
  motivo      TEXT NOT NULL,
  detalle     TEXT
);

CREATE TABLE IF NOT EXISTS ejecuciones_pipeline (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ejecutado_en TEXT NOT NULL,
  stats_json  TEXT NOT NULL
);
