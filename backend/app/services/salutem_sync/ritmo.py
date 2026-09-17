"""Ritmo de llamadas a SALUTEM: limita la frecuencia y reintenta caídas.

Solo se reintenta `SalutemUnavailableError` (timeout, cuerpo ilegible). Una
credencial rechazada o una petición inválida no mejoran insistiendo.
"""

import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.integrations.salutem.errors import SalutemUnavailableError

T = TypeVar("T")

ESPERAS_REINTENTO_S = (2.0, 4.0, 8.0)


class Ritmo:
    def __init__(
        self,
        llamadas_por_seg: float,
        *,
        dormir: Callable[[float], None] = time.sleep,
        reloj: Callable[[], float] = time.monotonic,
        esperas_reintento: tuple[float, ...] = ESPERAS_REINTENTO_S,
    ) -> None:
        self._intervalo = 1.0 / llamadas_por_seg if llamadas_por_seg > 0 else 0.0
        self._dormir = dormir
        self._reloj = reloj
        self._esperas = esperas_reintento
        self._ultima: float | None = None
        self.llamadas = 0

    def llamar(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        for intento in range(len(self._esperas) + 1):
            self._esperar_turno()
            self.llamadas += 1
            try:
                return fn(*args, **kwargs)
            except SalutemUnavailableError:
                if intento == len(self._esperas):
                    raise
                self._dormir(self._esperas[intento])
        raise AssertionError("inalcanzable")

    def _esperar_turno(self) -> None:
        if self._ultima is not None and self._intervalo:
            falta = self._intervalo - (self._reloj() - self._ultima)
            if falta > 0:
                self._dormir(falta)
        self._ultima = self._reloj()
