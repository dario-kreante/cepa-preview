"""Schemas Pydantic v2 para el módulo de Controles Médicos (EPIC-06).

Tres schemas de escritura independientes para alinear con las tres historias:
- ControlMedicoCreate  → CEPA-060 (registro base + cálculo de semana)
- ProximoControlUpdate → CEPA-061 (próximo control y estado de agenda)
- LicenciaUpdate       → CEPA-062 (licencia, GAF y RECA)
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.enums_controles import EstadoReca, TipoLicencia, TipoReposo


class ControlMedicoCreate(BaseModel):
    """Alta de un control médico (CEPA-060).

    El campo semana_control NO se incluye: es calculado automáticamente
    en el servicio a partir de fecha_ingreso del Ingreso vinculado.
    """

    ingreso_id: int
    fecha_control: date
    medico_tratante: str
    region_derivacion: str


class ProximoControlUpdate(BaseModel):
    """Programación del próximo control (CEPA-061).

    Se aplica sobre un control ya existente vía PATCH.
    proximo_agendado por defecto False (RN-2).
    """

    proximo_control: date
    proximo_agendado: bool = False


class LicenciaUpdate(BaseModel):
    """Actualización de licencia y RECA asociados al control (CEPA-062).

    Si tiene_licencia=True: resumen_termino_lm, total_dias_lm, tipo_licencia y
    tipo_reposo son OBLIGATORIOS (RN-1).
    Si tiene_licencia=False: los campos de licencia quedan vacíos.
    GAF es siempre opcional pero, si se informa, debe estar en rango 0-100 (RN-3).
    estado_reca y observaciones siempre editables (RN-5).
    """

    tiene_licencia: bool
    resumen_termino_lm: str | None = None
    total_dias_lm: int | None = None
    tipo_licencia: TipoLicencia | None = None
    tipo_reposo: TipoReposo | None = None
    gaf: int | None = None
    estado_reca: EstadoReca | None = None
    observaciones: str | None = None

    @field_validator("total_dias_lm")
    @classmethod
    def _dias_positivos(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("total_dias_lm debe ser un entero ≥ 1")
        return v

    @field_validator("gaf")
    @classmethod
    def _gaf_rango(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("GAF debe estar entre 0 y 100 (RN-3 CEPA-062)")
        return v

    @model_validator(mode="after")
    def _licencia_campos_obligatorios(self) -> "LicenciaUpdate":
        """Si tiene_licencia=True, exige los cuatro campos de licencia (RN-1)."""
        if self.tiene_licencia:
            faltantes = []
            if self.resumen_termino_lm is None:
                faltantes.append("resumen_termino_lm")
            if self.total_dias_lm is None:
                faltantes.append("total_dias_lm")
            if self.tipo_licencia is None:
                faltantes.append("tipo_licencia")
            if self.tipo_reposo is None:
                faltantes.append("tipo_reposo")
            if faltantes:
                raise ValueError(
                    f"Con tiene_licencia=True los siguientes campos son obligatorios: "
                    f"{', '.join(faltantes)}"
                )
        return self


class ControlMedicoRead(BaseModel):
    """Respuesta unificada del control médico (todos los campos de las tres historias)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    fecha_control: date
    semana_control: int
    medico_tratante: str
    region_derivacion: str
    # CEPA-061
    proximo_control: date | None
    proximo_agendado: bool
    # CEPA-062
    tiene_licencia: bool
    resumen_termino_lm: str | None
    total_dias_lm: int | None
    tipo_licencia: TipoLicencia | None
    tipo_reposo: TipoReposo | None
    gaf: int | None
    estado_reca: EstadoReca | None
    observaciones: str | None
