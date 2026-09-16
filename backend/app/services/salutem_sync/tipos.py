"""Tipos compartidos por los módulos del sync."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

MODOS = ("backfill", "caliente", "tibia", "fria", "vincular")


class Resultado(Enum):
    """Qué pasó al guardar un registro en la copia."""

    NUEVO = "nuevo"
    CAMBIADO = "cambiado"
    IGUAL = "igual"


@dataclass
class Contadores:
    nuevos: int = 0
    cambiados: int = 0
    desaparecidos: int = 0

    def registrar(self, resultado: Resultado) -> None:
        if resultado is Resultado.NUEVO:
            self.nuevos += 1
        elif resultado is Resultado.CAMBIADO:
            self.cambiados += 1

    def sumar(self, otros: "Contadores") -> None:
        self.nuevos += otros.nuevos
        self.cambiados += otros.cambiados
        self.desaparecidos += otros.desaparecidos


def a_utc(ahora: datetime) -> datetime:
    """Normaliza a UTC antes de guardar o comparar.

    En Oracle `DateTime(timezone=True)` compila a DATE y python-oracledb descarta el
    tzinfo al bindear: un `ahora` en otro huso quedaría corrido. Un naive se rechaza
    porque no hay forma de saber en qué huso está.
    """
    if ahora.tzinfo is None:
        raise ValueError("ahora debe ser un datetime aware (con tzinfo)")
    return ahora.astimezone(timezone.utc)
