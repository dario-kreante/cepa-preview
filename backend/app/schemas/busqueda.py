from pydantic import BaseModel

from app.schemas.control_medico import ControlMedicoRead
from app.schemas.farmacos import EsquemaIndicacionRead, RecetaRead, RegistroFarmacologicoRead
from app.schemas.ingreso import IngresoRead, PacienteRead
from app.schemas.licencia import LicenciaRead
from app.schemas.reintegro import CasoReintegroRead


class FarmacosIngresoRead(RegistroFarmacologicoRead):
    """Registro farmacológico de un ingreso con su esquema de indicaciones y recetas.

    `indicaciones` incluye el historial completo del esquema (las vigentes llevan
    `vigente=True`, CEPA-021 RN-2).
    """

    indicaciones: list[EsquemaIndicacionRead] = []
    recetas: list[RecetaRead] = []


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
    reintegro: list[CasoReintegroRead] = []
