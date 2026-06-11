"""Schemas Pydantic v2 para Licencias Médicas — EPIC-07.

Valida en capa de aplicación las reglas de negocio de fechas (RN-4 CEPA-070),
catálogos cerrados (RN-3 CEPA-070) y trazabilidad ISL (RN-1/RN-2 CEPA-073).
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums_licencia import EstadoEnvioISL, OrigenLicencia, TipoLicencia, TipoReposo


class LicenciaCreate(BaseModel):
    """Alta de una licencia médica (CEPA-070, campos D8)."""

    ingreso_id: int
    folio_lm: str | None = None
    tipo_lm: TipoLicencia
    tipo_reposo: TipoReposo
    fecha_inicio: date
    fecha_termino: date
    fecha_emision: date
    inicio_reposo: date
    fin_reposo: date
    cantidad_dias: Annotated[int, Field(ge=1)]
    indicacion_reposo: str | None = None
    diagnostico: str
    origen: OrigenLicencia = OrigenLicencia.SISTEMA

    @model_validator(mode="after")
    def _validar_coherencia_fechas(self) -> "LicenciaCreate":
        # RN-4: fecha_termino >= fecha_inicio
        if self.fecha_termino < self.fecha_inicio:
            raise ValueError(
                "fecha_termino debe ser mayor o igual a fecha_inicio "
                f"(inicio={self.fecha_inicio}, termino={self.fecha_termino})"
            )
        # RN-4: fecha_emision <= fecha_inicio
        if self.fecha_emision > self.fecha_inicio:
            raise ValueError(
                "fecha_emision debe ser anterior o igual a fecha_inicio "
                f"(emision={self.fecha_emision}, inicio={self.fecha_inicio})"
            )
        # RN-4: fin_reposo >= inicio_reposo
        if self.fin_reposo < self.inicio_reposo:
            raise ValueError(
                "fin_reposo debe ser mayor o igual a inicio_reposo "
                f"(inicio_reposo={self.inicio_reposo}, fin_reposo={self.fin_reposo})"
            )
        return self


class LicenciaISLUpdate(BaseModel):
    """Actualización de trazabilidad ISL (CEPA-073 RN-1/RN-2)."""

    envio_isl: EstadoEnvioISL
    fecha_envio_isl: date | None = None
    eeag_gaf: Annotated[int | None, Field(ge=1, le=100)] = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def _fecha_obligatoria_cuando_enviado_o_rechazado(self) -> "LicenciaISLUpdate":
        if self.envio_isl in (EstadoEnvioISL.ENVIADO, EstadoEnvioISL.RECHAZADO):
            if self.fecha_envio_isl is None:
                raise ValueError(
                    f"fecha_envio_isl es obligatoria cuando envio_isl='{self.envio_isl.value}'"
                )
        return self


class LicenciaAnularUpdate(BaseModel):
    """Anulación/recalificación de una LM (77 BIS o admin)."""

    observaciones: str


class LicenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    folio_lm: str | None
    tipo_lm: TipoLicencia
    tipo_reposo: TipoReposo
    fecha_inicio: date
    fecha_termino: date
    fecha_emision: date
    inicio_reposo: date
    fin_reposo: date
    cantidad_dias: int
    indicacion_reposo: str | None
    diagnostico: str
    origen: OrigenLicencia
    envio_isl: EstadoEnvioISL
    fecha_envio_isl: date | None
    eeag_gaf: int | None
    observaciones: str | None
    anulada: bool


class AcumuladoRead(BaseModel):
    """Respuesta del endpoint de acumulado de días por paciente (CEPA-071, EPIC-12)."""

    model_config = ConfigDict(from_attributes=True)

    ingreso_id: int
    dias_acumulados_vigentes: int
    dias_acumulados_bruto: int
    hay_solapamiento: bool
    incluye_extra_sistema: bool


class AlertaLicenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    licencia_id: int
    ingreso_id: int
    fecha_termino_lm: date
    dias_habiles_restantes: int
    activa: bool
