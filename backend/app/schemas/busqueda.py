from datetime import date

from pydantic import BaseModel

from app.schemas.control_medico import ControlMedicoRead
from app.schemas.farmacos import EsquemaIndicacionRead, RecetaRead, RegistroFarmacologicoRead
from app.schemas.ingreso import IngresoRead, PacienteRead
from app.schemas.licencia import LicenciaRead
from app.schemas.oda import OdaRead
from app.schemas.reintegro import CasoReintegroRead


class FarmacosIngresoRead(RegistroFarmacologicoRead):
    """Registro farmacológico de un ingreso con su esquema de indicaciones y recetas.

    `indicaciones` incluye el historial completo del esquema (las vigentes llevan
    `vigente=True`, CEPA-021 RN-2).
    """

    indicaciones: list[EsquemaIndicacionRead] = []
    recetas: list[RecetaRead] = []


class CitaSalutemResumen(BaseModel):
    """Cita de SALUTEM de un paciente que aún no tiene ingreso donde importarla."""

    cita_id: int
    fecha: date | None
    hora: str | None = None
    estado: str | None = None
    especialidad: str | None = None
    profesional: str | None = None


class Vista360(BaseModel):
    """Estado consolidado del paciente (CEPA-012).

    Cada dimensión trae los registros de todos los ingresos del paciente; el
    `ingreso_id` de cada elemento indica a qué ingreso pertenece.
    """

    paciente: PacienteRead
    ingresos: list[IngresoRead]
    farmacos: list[FarmacosIngresoRead] = []
    licencias: list[LicenciaRead] = []
    controles: list[ControlMedicoRead] = []
    odas: list[OdaRead] = []
    reintegro: list[CasoReintegroRead] = []
    # Solo para pacientes sin ingreso (los borradores de SALUTEM): con ingreso, las citas
    # se importan a él y esta lista queda vacía.
    citas_salutem: list[CitaSalutemResumen] = []
