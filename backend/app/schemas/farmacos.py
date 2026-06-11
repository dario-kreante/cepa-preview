"""Schemas Pydantic v2 para EPIC-02 — Gestión de Fármacos.

Incluye validaciones de negocio:
- Estado farmacológico como Enum (CEPA-020 RN-3).
- Frecuencia de fármaco como Enum (CEPA-021 RN-1).
- Fechas de receta: revisión y envío no anteriores a emisión (CEPA-022 RN-5).
- Seguimiento: plan/detalle obligatorio cuando la bandera es True (CEPA-023 RN-1/RN-2).
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.enums import EstadoFarmacologico, FrecuenciaFarmaco


# ── RegistroFarmacologico ─────────────────────────────────────────────────────

class RegistroFarmacologicoCreate(BaseModel):
    ingreso_id: int
    medico_tratante: str
    estado_farmacologico: EstadoFarmacologico
    antecedentes_previos: str | None = None
    tratamiento_previo: str | None = None


class RegistroFarmacologicoUpdate(BaseModel):
    medico_tratante: str | None = None
    estado_farmacologico: EstadoFarmacologico | None = None
    antecedentes_previos: str | None = None
    tratamiento_previo: str | None = None
    activo: bool | None = None


class RegistroFarmacologicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    medico_tratante: str
    estado_farmacologico: EstadoFarmacologico
    antecedentes_previos: str | None
    tratamiento_previo: str | None
    activo: bool
    created_at: datetime
    updated_at: datetime


# ── EsquemaIndicacion ─────────────────────────────────────────────────────────

class EsquemaIndicacionCreate(BaseModel):
    registro_id: int
    medicamento: str
    dosis: str
    frecuencia: FrecuenciaFarmaco
    extra_sistema: bool = False


class EsquemaIndicacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registro_id: int
    medicamento: str
    dosis: str
    frecuencia: FrecuenciaFarmaco
    extra_sistema: bool
    vigente: bool
    created_at: datetime


# ── Receta ────────────────────────────────────────────────────────────────────

class RecetaCreate(BaseModel):
    registro_id: int
    fecha_emision: date
    fecha_revision: date
    fecha_envio: date | None = None
    marca_medicamento: str

    @model_validator(mode="after")
    def _validar_orden_fechas(self) -> "RecetaCreate":
        if self.fecha_revision < self.fecha_emision:
            raise ValueError(
                "fecha_revision no puede ser anterior a fecha_emision (CEPA-022 RN-5)"
            )
        if self.fecha_envio is not None and self.fecha_envio < self.fecha_emision:
            raise ValueError(
                "fecha_envio no puede ser anterior a fecha_emision (CEPA-022 RN-5)"
            )
        return self


class RecetaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registro_id: int
    fecha_emision: date
    fecha_revision: date
    fecha_envio: date | None
    marca_medicamento: str
    created_at: datetime
    updated_at: datetime


# ── SeguimTratamiento ─────────────────────────────────────────────────────────

class SeguimTratamientoCreate(BaseModel):
    registro_id: int
    disminucion_farmacos: bool
    plan_disminucion: str | None = None
    cambio_esquema: bool
    detalle_cambio: str | None = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def _validar_detalles_obligatorios(self) -> "SeguimTratamientoCreate":
        if self.disminucion_farmacos and not self.plan_disminucion:
            raise ValueError(
                "plan_disminucion es obligatorio cuando disminucion_farmacos=True (CEPA-023 RN-1)"
            )
        if self.cambio_esquema and not self.detalle_cambio:
            raise ValueError(
                "detalle_cambio es obligatorio cuando cambio_esquema=True (CEPA-023 RN-2)"
            )
        return self


class SeguimTratamientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registro_id: int
    disminucion_farmacos: bool
    plan_disminucion: str | None
    cambio_esquema: bool
    detalle_cambio: str | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime


# ── Alerta ────────────────────────────────────────────────────────────────────

class AlertaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receta_id: int
    tipo: str
    mensaje: str
    leida: bool
    created_at: datetime
