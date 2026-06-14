from typing import Any

from pydantic import BaseModel

from app.schemas.ingreso import IngresoRead, PacienteRead


class Vista360(BaseModel):
    """Estado consolidado del paciente (CEPA-012).

    `ingresos` ya se llena en EPIC-01. Las demás dimensiones son ranuras que las
    épicas de Oleada 3 (Fármacos, Licencias, Controles, Reintegro) poblarán por
    folio/RUT; hoy se devuelven como listas vacías.
    """

    paciente: PacienteRead
    ingresos: list[IngresoRead]
    farmacos: list[Any] = []
    licencias: list[Any] = []
    controles: list[Any] = []
    reintegro: list[Any] = []
