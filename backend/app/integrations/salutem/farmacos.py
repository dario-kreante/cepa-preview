"""Extractor de fármacos desde las recetas de SALUTEM.

SALUTEM guarda la receta como texto libre en una indicación de tipo
"Receta Medicamentos", una línea por medicamento:

    "Clotiazepam 5 mg SOS\\r\\n\\r\\nSertralina 100 mg 1 al día"
    "Sertralina 100 mg 1 comp cada 24 horas"

Cada línea con una dosis reconocible (número + unidad) se estructura como
medicamento, dosis y frecuencia del esquema del CEPA. Las líneas sin dosis se
descartan: en el ambiente de pruebas hay recetas como "fsdfsdff" o "561651".

Es una sugerencia: el resultado lo revisa una persona antes de registrarlo.
"""

import html
import re
import unicodedata
from dataclasses import dataclass, field

from app.domain.enums import FrecuenciaFarmaco

_RE_BR = re.compile(r"<br\s*/?>|</p>|</div>", re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_DOSIS = re.compile(
    r"(?P<cant>\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)\s*(?P<unidad>mg|mcg|µg|ug|gr|g|ml|gotas|gts|ui)\b",
    re.IGNORECASE,
)
_RE_LETRAS = re.compile(r"[a-záéíóúñü]{3,}", re.IGNORECASE)
_RE_CADA_HORAS = re.compile(r"cada\s*(\d{1,2})\s*(?:h|hr|hrs|hora|horas)\b")
_RE_VECES_DIA = re.compile(
    r"\b(\d|un[oa]?|dos|tres|cuatro)\s*(?:comp\w*\s*|tab\w*\s*|caps\w*\s*)?"
    r"(?:vez|veces)?\s*(?:al|por|x|el)\s*dia\b"
)
_RE_SOS = re.compile(r"\bsos\b|segun necesidad|en caso de|si es necesario")
_RE_DIARIO = re.compile(r"\bdiari[oa]\b|\bnoche\b|\bmanana\b|\bal acostarse\b")

_NUMEROS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4}
_POR_HORAS = {
    24: FrecuenciaFarmaco.C24H,
    12: FrecuenciaFarmaco.C12H,
    8: FrecuenciaFarmaco.C8H,
    6: FrecuenciaFarmaco.C6H,
}
_POR_VECES = {
    1: FrecuenciaFarmaco.C24H,
    2: FrecuenciaFarmaco.C12H,
    3: FrecuenciaFarmaco.C8H,
    4: FrecuenciaFarmaco.C6H,
}

AVISO_SOS = "Uso SOS (según necesidad): el esquema no tiene esa frecuencia, queda como «Otro»."
AVISO_SIN_FRECUENCIA = "No se reconoció la frecuencia: revísala antes de registrar."


@dataclass(frozen=True)
class MencionFarmaco:
    medicamento: str
    dosis: str
    frecuencia: FrecuenciaFarmaco
    texto: str
    avisos: list[str] = field(default_factory=list)


def _sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _lineas(texto: str) -> list[str]:
    plano = _RE_TAG.sub("", _RE_BR.sub("\n", html.unescape(texto)))
    lineas: list[str] = []
    for linea in re.split(r"[\r\n;]+", plano):
        linea = " ".join(linea.split()).strip(" -•*·.,")
        if linea:
            lineas.append(linea)
    return lineas


def _frecuencia(posologia: str) -> tuple[FrecuenciaFarmaco, list[str], bool]:
    """(frecuencia, avisos, es_sos) según lo que sigue a la dosis."""
    p = _sin_tildes(posologia.lower())
    if _RE_SOS.search(p):
        return FrecuenciaFarmaco.OTRO, [AVISO_SOS], True
    if m := _RE_CADA_HORAS.search(p):
        horas = int(m.group(1))
        if horas in _POR_HORAS:
            return _POR_HORAS[horas], [], False
        return FrecuenciaFarmaco.OTRO, [f"Cada {horas} horas: queda como «Otro»."], False
    if m := _RE_VECES_DIA.search(p):
        crudo = m.group(1)
        veces = int(crudo) if crudo.isdigit() else _NUMEROS.get(crudo, 0)
        if veces in _POR_VECES:
            return _POR_VECES[veces], [], False
    if "semanal" in p or "a la semana" in p:
        return FrecuenciaFarmaco.SEMANAL, [], False
    if "mensual" in p or "al mes" in p:
        return FrecuenciaFarmaco.MENSUAL, [], False
    if _RE_DIARIO.search(p):
        return FrecuenciaFarmaco.C24H, [], False
    return FrecuenciaFarmaco.OTRO, [AVISO_SIN_FRECUENCIA], False


def _linea(linea: str) -> MencionFarmaco | None:
    m = _RE_DOSIS.search(linea)
    if m is None:
        return None
    # "1. Sertralina" o "- Sertralina": fuera la numeración de la lista.
    nombre = re.sub(r"^\d+[.)]\s*", "", linea[: m.start()].strip(" -•*·.,:"))
    if not _RE_LETRAS.search(nombre):
        return None
    cantidad = m.group("cant").replace(" ", "").replace(",", ".")
    frecuencia, avisos, sos = _frecuencia(linea[m.end() :])
    return MencionFarmaco(
        medicamento=nombre[:1].upper() + nombre[1:],
        dosis=f"{cantidad} {m.group('unidad').lower()}" + (" SOS" if sos else ""),
        frecuencia=frecuencia,
        texto=linea,
        avisos=avisos,
    )


def extraer_farmacos(texto: object) -> list[MencionFarmaco]:
    """Los medicamentos que la receta menciona, uno por línea con dosis."""
    if not isinstance(texto, str) or not texto.strip():
        return []
    return [m for linea in _lineas(texto) if (m := _linea(linea)) is not None]
