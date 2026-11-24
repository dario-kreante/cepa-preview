"""Qué nota de SALUTEM es un addendum (QA-008).

En SALUTEM el addendum no es un campo: el equipo del CEPA lo registra como una nota de la
atención, y en esa lista también caen otras notas. Por ahora es addendum la nota cuyo texto
menciona la palabra (sin tildes ni mayúsculas, con una o dos d). La convención está por
confirmarse con la clienta: si cambia, se ajusta solo PALABRAS_ADDENDUM. Se evalúa al leer
el control, así que no hace falta volver a sincronizar.
"""

import unicodedata

PALABRAS_ADDENDUM: tuple[str, ...] = ("addendum", "adendum", "addenda", "adenda")


def _normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto)
    return "".join(c for c in base if unicodedata.category(c) != "Mn").casefold()


def es_addendum(texto: str | None) -> bool:
    normalizado = _normalizar(texto or "")
    return any(palabra in normalizado for palabra in PALABRAS_ADDENDUM)
