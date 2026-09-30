"""Campos estructurados de las atenciones de SALUTEM.

Además del texto libre, los formularios de SALUTEM traen campos de selección
("GAF", "Tipo de reposo", "Tipo de alta"...) en la sección que corresponda al
ítem. Su `registro` llega con la opción elegida en formas distintas según el formulario:
`{"2": "Total"}`, `["Alta médica"]`, o esas mismas estructuras como texto
(`"{'1': '51-60'}"`). Este módulo las lleva a un string plano.
"""

import ast
import html
import re
from typing import Any

_RE_TAG = re.compile(r"<[^>]+>")
_RE_TRAMO = re.compile(r"^\s*(\d{1,3})\s*[-–]\s*(\d{1,3})\s*$")


def valor_campo(registro: Any) -> str | None:
    """La opción (u opciones) de un campo, como texto plano; None si viene vacío."""
    if isinstance(registro, dict):
        partes = [valor_campo(v) for v in registro.values()]
        return ", ".join(p for p in partes if p) or None
    if isinstance(registro, (list, tuple)):
        partes = [valor_campo(v) for v in registro]
        return ", ".join(p for p in partes if p) or None
    if isinstance(registro, (int, float)) and not isinstance(registro, bool):
        return str(registro)
    if not isinstance(registro, str):
        return None
    texto = registro.strip()
    if texto[:1] in ("{", "["):
        try:
            return valor_campo(ast.literal_eval(texto))
        except (ValueError, SyntaxError):
            pass
    texto = _RE_TAG.sub("", html.unescape(texto)).strip()
    return texto or None


def items(contenido: dict[str, Any]) -> list[dict[str, Any]]:
    """Los campos de todas las secciones de la atención (antecedentes, indicaciones...)."""
    todos: list[dict[str, Any]] = []
    for seccion in contenido.values():
        if isinstance(seccion, dict):
            seccion = [seccion]
        if isinstance(seccion, list):
            todos.extend(i for i in seccion if isinstance(i, dict) and "registro" in i)
    return todos


def campo(contenido: dict[str, Any], nombre: str) -> str | None:
    """El primer campo con ese nombre en cualquier sección, normalizado.

    SALUTEM ubica los campos del formulario en la sección que corresponda al ítem
    ("antecedentes", "indicaciones"...), así que se buscan en todas.
    """
    buscado = nombre.casefold()
    for item in items(contenido):
        if str(item.get("nombre", "")).strip().casefold() == buscado:
            valor = valor_campo(item.get("registro"))
            if valor is not None:
                return valor
    return None


def tramo_gaf(valor: str | None) -> str | None:
    """"51-60" (con o sin espacios) → "51-60"; cualquier otra cosa → None."""
    if valor is None:
        return None
    m = _RE_TRAMO.match(valor)
    if m is None:
        return None
    desde, hasta = int(m.group(1)), int(m.group(2))
    if not 1 <= desde <= hasta <= 100:
        return None
    return f"{desde}-{hasta}"
