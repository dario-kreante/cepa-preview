"""Qué personas de SALUTEM entran al sync y cómo se cruzan con los pacientes del CEPA."""

from datetime import date

from sqlalchemy import ColumnElement, and_, or_

from app.integrations.salutem.models import (
    AtencionSalutem,
    CitaSalutem,
    EstadoCitaSalutem,
    PersonaSalutem,
    TipoFechaCita,
)
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemPersona


def cruce_con_paciente() -> ColumnElement[bool]:
    """Una persona de SALUTEM es un paciente del CEPA si comparten RUT o si el
    paciente apunta a ella por id (personas sin RUT, como los pacientes de prueba)."""
    return or_(
        Paciente.rut == SalutemPersona.rut,
        and_(
            Paciente.salutem_persona_id.is_not(None),
            Paciente.salutem_persona_id == SalutemPersona.salutem_id,
        ),
    )


class ClientePersonasPermitidas:
    """Envuelve el cliente SALUTEM y deja pasar solo a las personas permitidas.

    Las citas de otras personas se descartan al listarlas, y nunca se piden sus
    datos ni sus atenciones: lo que no está en la lista no llega a la copia.
    """

    def __init__(self, cliente: SalutemClientProtocol, permitidas: frozenset[int]) -> None:
        self._cliente = cliente
        self._permitidas = permitidas

    def resolver_persona(self, rut: str) -> PersonaSalutem | None:
        # Una búsqueda por RUT llegaría a identidades reales: con lista, no se hace.
        return None

    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        if salutem_id not in self._permitidas:
            return None
        return self._cliente.obtener_persona(salutem_id)

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:
        if salutem_id not in self._permitidas:
            return []
        return self._cliente.listar_atenciones(salutem_id)

    def obtener_atencion(self, salutem_id: int, cita_id: int) -> AtencionSalutem | None:
        if salutem_id not in self._permitidas:
            return None
        return self._cliente.obtener_atencion(salutem_id, cita_id)

    def listar_citas(
        self,
        dia: date,
        estado: EstadoCitaSalutem,
        por: TipoFechaCita = TipoFechaCita.FECHA_CITA,
    ) -> list[CitaSalutem]:
        return [
            c for c in self._cliente.listar_citas(dia, estado, por) if c.persona_id in self._permitidas
        ]


def envolver_si_corresponde(
    cliente: SalutemClientProtocol, permitidas: frozenset[int]
) -> SalutemClientProtocol:
    """Sin lista, el cliente queda tal cual (todas las personas)."""
    return ClientePersonasPermitidas(cliente, permitidas) if permitidas else cliente
