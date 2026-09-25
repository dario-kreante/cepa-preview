"""Extracción de licencias médicas desde las indicaciones de SALUTEM.

SALUTEM no tiene un recurso de licencias: el médico las escribe como prosa en
`indicaciones[].registro`, en HTML. Este módulo convierte esa prosa en una
mención estructurada, sin escribir nada ni decidir si se registra en el CEPA.

Reconoce dos formas de escritura:
- La prosa real de los médicos, vista en QA: "Extiendo licencia médica tipo 6
  total desde el 09/05/2024 por 21 días", "licencia médica extrasistema hasta el
  17/04/24", "Alta laboral Total ... a partir del 14/06/2024".
- El formato acordado con el CEPA el 07-09-2026: "Días de licencia", "Fecha de
  inicio", "Fecha de término" y "Tipo de licencia".

Los médicos se equivocan de año ("desde el 18/04/2023" en una atención de 2024).
El extractor no corrige: entrega lo escrito y deja un aviso para revisión humana.
"""

import html
import re
from datetime import date, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

# Una fecha de inicio anterior a la atención en más de este margen es sospechosa.
_MARGEN_INICIO = timedelta(days=180)

_FECHA = r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
# "Considerar alta laboral total" es una sugerencia a futuro, no un alta: el grupo 1
# captura esos verbos para descartar la coincidencia.
_RE_ALTA = re.compile(
    r"(?:\b(considerar|evaluar|valorar|sugerir|sugiere|posible)\s+)?\balta\s+laboral\b",
    re.IGNORECASE,
)
_RE_REINCORPORACION = re.compile(r"(?:a\s+partir\s+del?|desde\s+el)\s*" + _FECHA, re.IGNORECASE)
_RE_SIN_LICENCIA = re.compile(r"\bsin\s+licencia\b", re.IGNORECASE)
# "LM" es como abrevian los médicos ("Se indica LM tipo 6 por 15 dias"); solo en
# mayúsculas, para no confundirla con "lm" dentro de otra palabra.
_RE_LICENCIA = re.compile(r"(?i:\blicencia\b)|\bLM\b")
_RE_EXTRA_SISTEMA = re.compile(r"extra\s*-?\s*sistema", re.IGNORECASE)
_RE_TIPO = re.compile(r"\btipo(?:\s+de\s+licencia)?\s*:?\s*(\d)\b", re.IGNORECASE)
_RE_REPOSO = re.compile(r"\b(total|parcial)\b", re.IGNORECASE)
_RE_INICIO = re.compile(r"(?:desde\s+el|fecha\s+de\s+inicio\s*:?)\s*" + _FECHA, re.IGNORECASE)
_RE_TERMINO = re.compile(
    r"(?:hasta\s+el|fecha\s+de\s+t[eé]rmino\s*:?|vencimiento\s+de\s+licencia[^()]*\()\s*" + _FECHA,
    re.IGNORECASE,
)
_RE_DIAS_CAMPO = re.compile(r"d[ií]as\s+de\s+licencia\s*:?\s*(\d+)", re.IGNORECASE)
_RE_DIAS_PROSA = re.compile(r"\bpor\s+(\d+)\s+d[ií]as\b", re.IGNORECASE)


class ClaseMencion(str, Enum):
    """Qué dice la indicación sobre la licencia del paciente."""

    LICENCIA = "licencia"
    ALTA_LABORAL = "alta_laboral"
    SIN_LICENCIA = "sin_licencia"


class MencionLicencia(BaseModel):
    """Lo que se pudo leer de una indicación. Los campos no escritos quedan en None."""

    model_config = ConfigDict(frozen=True)

    clase: ClaseMencion
    tipo_licencia: str | None = None
    extra_sistema: bool = False
    tipo_reposo: str | None = None
    fecha_inicio: date | None = None
    dias: int | None = None
    fecha_termino: date | None = None
    # True si el término no venía escrito y se calculó desde inicio + días.
    termino_calculado: bool = False
    fecha_reincorporacion: date | None = None
    avisos: list[str] = []
    texto: str = ""


def _texto_plano(registro: Any) -> str:
    # Las indicaciones de exámenes llegan como dict: no son prosa.
    if not isinstance(registro, str):
        return ""
    sin_etiquetas = re.sub(r"<[^>]+>", " ", registro)
    return re.sub(r"\s+", " ", html.unescape(sin_etiquetas)).strip()


def _fecha(match: re.Match[str] | None) -> date | None:
    if match is None:
        return None
    dia, mes, anio = (int(g) for g in match.groups()[-3:])
    if anio < 100:
        anio += 2000
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _formato(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def extraer_licencia(registro: Any, fecha_atencion: date) -> MencionLicencia | None:
    """Lee la licencia mencionada en una indicación de SALUTEM, si la hay."""
    texto = _texto_plano(registro)
    if not texto:
        return None

    alta = _RE_ALTA.search(texto)
    if alta is not None and alta.group(1) is None:
        return MencionLicencia(
            clase=ClaseMencion.ALTA_LABORAL,
            fecha_reincorporacion=_fecha(_RE_REINCORPORACION.search(texto)),
            texto=texto,
        )
    if _RE_SIN_LICENCIA.search(texto):
        return MencionLicencia(clase=ClaseMencion.SIN_LICENCIA, texto=texto)

    licencia = _RE_LICENCIA.search(texto)
    if licencia is None:
        return None

    tipo = _RE_TIPO.search(texto)
    reposo = _RE_REPOSO.search(texto)
    inicio = _fecha(_RE_INICIO.search(texto))
    termino = _fecha(_RE_TERMINO.search(texto))
    # "por N días" solo cuenta después de mencionar la licencia: antes suele ser un fármaco.
    dias_match = _RE_DIAS_CAMPO.search(texto) or _RE_DIAS_PROSA.search(texto, licencia.start())
    dias = int(dias_match.group(1)) if dias_match else None

    avisos: list[str] = []
    termino_calculado = False
    if termino is None and inicio is not None and dias is not None:
        termino = inicio + timedelta(days=dias - 1)
        termino_calculado = True

    if inicio is not None and inicio < fecha_atencion - _MARGEN_INICIO:
        avisos.append(
            f"La fecha de inicio ({_formato(inicio)}) es más de 6 meses anterior a la atención "
            f"({_formato(fecha_atencion)}): posible error de tipeo en el año."
        )
    if termino is not None and not termino_calculado and termino < fecha_atencion:
        avisos.append(
            f"La fecha de término ({_formato(termino)}) es anterior a la atención "
            f"({_formato(fecha_atencion)}): posible error de tipeo en el año."
        )
    if inicio is not None and termino is not None and dias is not None and not termino_calculado:
        dias_fechas = (termino - inicio).days + 1
        if dias_fechas != dias:
            avisos.append(
                f"Los días de licencia ({dias}) no coinciden con las fechas: del "
                f"{_formato(inicio)} al {_formato(termino)} son {dias_fechas} días."
            )

    return MencionLicencia(
        clase=ClaseMencion.LICENCIA,
        tipo_licencia=tipo.group(1) if tipo else None,
        extra_sistema=_RE_EXTRA_SISTEMA.search(texto) is not None,
        tipo_reposo=reposo.group(1).lower() if reposo else None,
        fecha_inicio=inicio,
        dias=dias,
        fecha_termino=termino,
        termino_calculado=termino_calculado,
        avisos=avisos,
        texto=texto,
    )
