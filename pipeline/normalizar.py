"""T1.3 — Normalización: teléfono E.164 (+57), ciudad canónica, fechas ISO-8601,
canal/estado canónicos. Reglas documentadas en docs/supuestos.md."""
import re
import unicodedata

import pandas as pd
from dateutil import parser as dtparser

# ---------------------------------------------------------------- canales/estados
CANAL_CANONICO = {"whatsapp": "WhatsApp", "meta ads": "Meta Ads", "formulario web": "Formulario Web"}
ESTADO_CANONICO = {
    "contactado": "Contactado",
    "cotizacion enviada": "Cotización enviada",
    "en proceso": "En proceso",
    "no contesta": "No contesta",
    "descartado": "Descartado",
    "sin gestion": "Sin gestión",
}

# ---------------------------------------------------------------- ciudades
# Diccionario de variantes detectadas en el diagnóstico → ciudad canónica (DANE-ish).
CIUDADES_CANONICAS = {
    "bogota": "Bogotá D.C.",
    "bogota dc": "Bogotá D.C.",
    "b/quilla": "Barranquilla",
    "sta marta": "Santa Marta",
    "medellin": "Medellín",
    "rionegro": "Rionegro",
    "rio negro": "Rionegro",
    "soacha": "Soacha",
    "soledad": "Soledad",
    "cartagena": "Cartagena de Indias",
    "cartagena de indias": "Cartagena de Indias",
    "santa marta": "Santa Marta",
    "monteria": "Montería",
    "bello": "Bello",
    "itagui": "Itagüí",
    "envigado": "Envigado",
    "sabaneta": "Sabaneta",
    "turbo": "Turbo",
    "apartado": "Apartadó",
    "sincelejo": "Sincelejo",
    "valledupar": "Valledupar",
    "barranquilla": "Barranquilla",
    "pereira": "Pereira",
    "manizales": "Manizales",
    "cucuta": "Cúcuta",
    "ibague": "Ibagué",
}


def _quitar_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalizar_texto(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", " ", str(s).strip())


def normalizar_canal(v) -> str:
    return CANAL_CANONICO.get(normalizar_texto(v).lower(), "Desconocido")


def normalizar_estado(v) -> str:
    return ESTADO_CANONICO.get(normalizar_texto(v).lower(), "Otro")


def normalizar_ciudad(v) -> str:
    key = re.sub(r"[^a-z0-9 /]", "", _quitar_tildes(normalizar_texto(v).lower()))
    return CIUDADES_CANONICAS.get(key.strip(), "")


# ---------------------------------------------------------------- teléfono
# E.164 Colombia: +57 + 10 dígitos empezando en 3 (móvil).
# Reglas: quitar no-dígitos; si empieza en 57 y tiene 12 dígitos → quitar prefijo.
# Válido solo si termina en 10 dígitos que inician con 3. Lo demás → rechazo.


def normalizar_telefono(v) -> tuple[str, str]:
    """Devuelve (e164, motivo_rechazo). e164 vacío si es inválido."""
    digitos = re.sub(r"\D", "", normalizar_texto(v))
    if not digitos:
        return "", "telefono_vacio"
    if len(digitos) == 12 and digitos.startswith("57"):
        digitos = digitos[2:]
    if len(digitos) == 13 and digitos.startswith("57"):
        digitos = digitos[2:]
    if len(digitos) == 10 and digitos.startswith("3"):
        return f"+57{digitos}", ""
    return "", f"telefono_invalido({len(digitos)}dig)"


# ---------------------------------------------------------------- fechas
# Formatos detectados: ISO (2026-08-26), ISO-datetime (2026-08-26T14:26:00),
# datetime (2026-08-26 14:26:00), DD-MM-YYYY, DD/MM/YYYY [HH:MM], MM/DD/YYYY [HH:MM].
# SUPUESTO: slash con ambos valores <=12 → día primero (convención Colombia).


def normalizar_fecha(v) -> tuple[str, str]:
    """Devuelve (iso 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS', ''). Vacío + motivo si falla."""
    v = normalizar_texto(v)
    if not v:
        return "", "fecha_vacia"
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})(?:[ T](\d{1,2}):(\d{2}))?", v)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh, mm = m.group(4), m.group(5)
        if a > 12 and b > 12:
            return "", f"fecha_ilegible({v})"
        if a > 12:      # día primero evidente (a no cabe como mes)
            d, mo = a, b
        elif b > 12:    # mes primero evidente (formato US MM/DD)
            d, mo = b, a
        else:           # ambiguo → SUPUESTO: día primero (convención Colombia)
            d, mo = a, b
        iso = f"{y:04d}-{mo:02d}-{d:02d}"
        if hh is not None:
            iso += f"T{int(hh):02d}:{mm}:00"
        return iso, ""
    try:
        dt = dtparser.parse(v, dayfirst=True)
        tiene_hora = bool(re.search(r"\d{1,2}:\d{2}", v))
        return dt.strftime("%Y-%m-%d") + (dt.strftime("T%H:%M:%S") if tiene_hora else ""), ""
    except (ValueError, OverflowError):
        return "", f"fecha_ilegible({v})"
