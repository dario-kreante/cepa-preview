"""Implementación del cliente SALUTEM para el entorno CEPA.

PA2: la disponibilidad y naturaleza real de la API de SALUTEM está por confirmar.
Por ahora se implementa el cliente como stub que registra el intento y devuelve None.
Al confirmarse la API real, se completa la implementación sin cambiar el contrato.

REGLA D12: este módulo SOLO contiene métodos de lectura. No se implementan
métodos de escritura porque el CEPA no escribe sobre SALUTEM.
"""

from typing import Any

from app.integrations.salutem.protocol import SalutemClientProtocol


class SalutemStubClient:
    """Stub del cliente SALUTEM (PA2 — API aún por confirmar).

    Devuelve None/[] en todos los métodos; sirve para que la integración
    compile y los tests de guardia D12 funcionen sin API real.
    """

    def get_paciente(self, rut: str) -> dict[str, Any] | None:
        # TODO (PA2): implementar con la API real de SALUTEM cuando esté disponible
        return None

    def get_ficha_clinica(self, folio: str) -> dict[str, Any] | None:
        # TODO (PA2): implementar con la API real de SALUTEM cuando esté disponible
        return None

    def get_licencias(self, folio: str) -> list[dict[str, Any]]:
        # TODO (PA2): implementar con la API real de SALUTEM cuando esté disponible
        return []


_DEFAULT_CLIENT: SalutemClientProtocol = SalutemStubClient()


def get_salutem_client() -> SalutemClientProtocol:
    """Fábrica del cliente SALUTEM. Inyectable en tests con monkeypatch."""
    return _DEFAULT_CLIENT
