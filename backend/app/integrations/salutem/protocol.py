"""Contrato (Protocol) del cliente SALUTEM.

Define la interfaz de lectura que el CEPA usa para obtener datos de SALUTEM.
NO se definen métodos de escritura porque el CEPA nunca escribe sobre SALUTEM (D12).
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SalutemClientProtocol(Protocol):
    """Interfaz de solo lectura para la integración con SALUTEM/SAM (D12).

    El CEPA es receptor de datos clínicos y los persiste en su propio dominio;
    nunca muta el sistema de origen.
    """

    def get_paciente(self, rut: str) -> dict[str, Any] | None:
        """Obtiene datos de un paciente desde SALUTEM por RUT. Solo lectura."""
        ...

    def get_ficha_clinica(self, folio: str) -> dict[str, Any] | None:
        """Obtiene la ficha clínica de un folio desde SALUTEM. Solo lectura."""
        ...

    def get_licencias(self, folio: str) -> list[dict[str, Any]]:
        """Lista las licencias de un folio desde SALUTEM. Solo lectura."""
        ...
