"""Tramos de GAF (v5 D18, COMP-2609-12).

El GAF se registra como un tramo entre dos porcentajes ("41-50"), no como un entero libre.
El catálogo vigente vive en la tabla ``gaf_tramo``; ``TRAMOS_EEAG`` es la escala estándar
de 10 en 10 con la que se sembró, provisoria hasta que Pilar confirme la segmentación
(PA-v5-03). Los enteros cargados antes de D18 se conservan y se traducen al tramo que los
contiene.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Tramo:
    desde: int
    hasta: int
    etiqueta: str

    def contiene(self, valor: int) -> bool:
        return self.desde <= valor <= self.hasta


# 1-10, 11-20, …, 91-100 (provisorio, PA-v5-03).
TRAMOS_EEAG: tuple[Tramo, ...] = tuple(
    Tramo(desde, desde + 9, f"{desde}-{desde + 9}") for desde in range(1, 92, 10)
)


def tramo_que_contiene(valor: int | None, tramos: Iterable[Tramo]) -> Tramo | None:
    """Devuelve el tramo que contiene ``valor``, o None si no cae en ninguno."""
    if valor is None:
        return None
    return next((t for t in tramos if t.contiene(valor)), None)
