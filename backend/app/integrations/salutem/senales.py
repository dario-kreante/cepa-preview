"""Señales de licencia y receta en el formulario de una atención de SALUTEM.

Funciones puras sobre el `contenido` crudo de la atención: no tocan la base ni la red.
Las usan las alertas de los controles creados desde SALUTEM y los fármacos sugeridos.

- El certificado de reposo es una indicación de tipo "Documento" que SALUTEM genera
  ("…debe permanecer en reposo desde el … hasta el …"). El extractor de licencias no lo
  reconoce porque no dice "licencia" ni "LM".
- La receta es una indicación con "receta" en el tipo ("Receta Medicamentos", "Receta")
  o el campo "Indicaciones" del formulario del CEPA, cuando menciona algún fármaco.
  También cuenta un campo de selección con "receta" en el nombre marcado "Sí" (reunión
  29-10, D15): el médico responde sí/no y no hace falta interpretar texto libre.
"""

import html
import re
from typing import Any

from app.integrations.salutem.campos import items, valor_campo
from app.integrations.salutem.farmacos import extraer_farmacos

_RE_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_REPOSO = re.compile(r"\breposo\b", re.IGNORECASE)


def _texto(registro: Any) -> str:
    if not isinstance(registro, str):
        return ""
    return _RE_TAG.sub("", _RE_BR.sub("\n", html.unescape(registro)))


def _indicaciones(contenido: dict[str, Any]) -> list[dict[str, Any]]:
    valor = contenido.get("indicaciones") or []
    if isinstance(valor, dict):
        valor = [valor]
    return [i for i in valor if isinstance(i, dict)]


def certificado_reposo(contenido: dict[str, Any]) -> bool:
    """True si la atención trae el certificado de reposo que genera SALUTEM."""
    return any(
        str(i.get("tipo") or "").strip().casefold() == "documento"
        and _RE_REPOSO.search(_texto(i.get("registro")))
        for i in _indicaciones(contenido)
    )


def _es_receta(indicacion: Any) -> bool:
    if not isinstance(indicacion, dict):
        return False
    # SALUTEM separa por tipo: "Receta Medicamentos" (con nombre "Receta" o
    # "Indicaciones de tratamiento farmacológico"), "Indicación", "Documento"...
    return "receta" in str(indicacion.get("tipo") or "").casefold()


def _es_campo_indicaciones(item: dict[str, Any]) -> bool:
    # El campo "Indicaciones" del formulario del CEPA, en la sección que sea.
    return str(item.get("nombre") or "").strip().casefold() == "indicaciones"


def registros_receta(contenido: dict[str, Any]) -> list[Any]:
    """Los textos de la atención donde el médico escribe la receta."""
    return [
        i.get("registro") for i in items(contenido) if _es_receta(i) or _es_campo_indicaciones(i)
    ]


def _campo_receta_marcado(item: dict[str, Any]) -> bool:
    # Solo "receta" en el nombre: "Indicación previa de fármacos: Sí" es un antecedente.
    # Un "No" no apaga la alerta: si el texto menciona un fármaco, es mejor revisar.
    if "receta" not in str(item.get("nombre") or "").casefold():
        return False
    valor = (valor_campo(item.get("registro")) or "").strip().casefold()
    return valor in {"si", "sí"}


def tiene_receta(contenido: dict[str, Any]) -> bool:
    """True si el campo sí/no de receta está marcado o un texto menciona algún fármaco."""
    return any(_campo_receta_marcado(i) for i in items(contenido)) or any(
        extraer_farmacos(r) for r in registros_receta(contenido)
    )
