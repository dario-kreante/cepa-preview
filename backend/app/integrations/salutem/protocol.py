"""Contrato del cliente SALUTEM — solo lectura (D12).

El CEPA es receptor de datos clínicos: los persiste en su propio dominio y
nunca muta el sistema de origen. Por eso acá no existe ningún método de
escritura, y los nombres evitan deliberadamente los verbos que vigila el guard
de D12 (create/update/delete/push/write/patch).

── Anclaje por RUT ──────────────────────────────────────────────────────────
SALUTEM no conoce el `folio` del CEPA: es un identificador de nuestro dominio.
El puente entre ambos mundos es el RUT del paciente:

    Ingreso.folio → Ingreso.paciente.rut → resolver_persona() → salutem_id
                  → listar_atenciones(salutem_id) → obtener_atencion(...)

`salutem_id` es obligatorio en `/atencion`: pedir una atención solo con
`cita_id` devuelve ERROR_PERSONA_NO_EXISTE.

── Por qué `listar_citas` recibe un día y no un rango ───────────────────────
SALUTEM rechaza con ERROR_INTERVALO_SUPERADO cualquier ventana que cruce la
medianoche, incluso de 24 horas. En vez de aceptar un rango que la API va a
rechazar, la firma toma un solo día: quien sincroniza un período itera. La
restricción queda expresada en el tipo en lugar de en un comentario.

Verificado contra el ambiente QA (empresa 96) el 2026-09-07.
"""

from datetime import date
from typing import Protocol, runtime_checkable

from app.integrations.salutem.models import (
    AtencionSalutem,
    CitaSalutem,
    EstadoCitaSalutem,
    PersonaSalutem,
    TipoFechaCita,
)


@runtime_checkable
class SalutemClientProtocol(Protocol):
    """Interfaz de solo lectura hacia SALUTEM (D12).

    Todos los métodos pueden levantar `SalutemAuthError`, `SalutemRequestError`
    o `SalutemUnavailableError`. La ausencia de datos NO es un error: se expresa
    como `None` o lista vacía.
    """

    def resolver_persona(self, rut: str) -> PersonaSalutem | None:
        """Resuelve el RUT de un paciente CEPA a su persona en SALUTEM.

        Devuelve None si SALUTEM no tiene a esa persona. El `salutem_id` del
        resultado es la llave que exigen el resto de los métodos.
        """
        ...

    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        """Trae una persona por su id de SALUTEM. None si no existe.

        El sync conoce a las personas por el `personaId` de sus citas, no por RUT.
        """
        ...

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:
        """Lista las atenciones de una persona, sin el contenido clínico.

        Es el índice que permite decidir qué atenciones caen dentro de la
        ventana de un ingreso antes de traer cada ficha completa.
        """
        ...

    def obtener_atencion(self, salutem_id: int, cita_id: int) -> AtencionSalutem | None:
        """Trae una atención con su contenido clínico completo.

        Devuelve None si la atención no existe para esa persona.
        """
        ...

    def listar_citas(
        self,
        dia: date,
        estado: EstadoCitaSalutem,
        por: TipoFechaCita = TipoFechaCita.FECHA_CITA,
    ) -> list[CitaSalutem]:
        """Lista las citas de UN día para un estado dado.

        `estado` no es opcional: SALUTEM lo exige. Para barrer varios estados o
        varios días, se itera desde el llamador.
        """
        ...
