"""Códigos de un solo uso para entregar la sesión SAML al frontend.

El IdP hace POST al ACS, de modo que el navegador aterriza en el backend. En vez
de devolver los tokens ahí —quedarían en el historial y en cualquier proxy que
registre URLs— el ACS emite un código efímero y redirige al frontend, que lo
canjea por POST.

El almacén es en memoria a propósito: los códigos viven segundos y perderlos en
un reinicio solo obliga a repetir el login. Si el despliegue pasa a varios
workers habrá que moverlo a la base de datos o a un almacén compartido, porque
el canje podría caer en un proceso distinto al que emitió.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone


class CodigoInvalido(Exception):
    """El código no existe, ya se usó o expiró."""


class AlmacenCodigos:
    """Códigos de un solo uso con expiración corta."""

    def __init__(self, *, ttl_segundos: int = 60) -> None:
        self._ttl = timedelta(seconds=ttl_segundos)
        self._codigos: dict[str, tuple[int, datetime]] = {}

    def emitir(self, *, usuario_id: int) -> str:
        codigo = secrets.token_urlsafe(32)
        self._codigos[codigo] = (usuario_id, datetime.now(timezone.utc) + self._ttl)
        return codigo

    def canjear(self, codigo: str) -> int:
        """Devuelve el usuario asociado y consume el código."""
        self._purgar()
        entrada = self._codigos.pop(codigo, None)
        if entrada is None:
            raise CodigoInvalido("Código inexistente, ya usado o expirado")

        usuario_id, expira = entrada
        if expira <= datetime.now(timezone.utc):
            raise CodigoInvalido("Código expirado")
        return usuario_id

    def _purgar(self) -> None:
        ahora = datetime.now(timezone.utc)
        for codigo in [c for c, (_, exp) in self._codigos.items() if exp <= ahora]:
            self._codigos.pop(codigo, None)


# Instancia de proceso usada por los endpoints.
almacen_codigos = AlmacenCodigos()
