"""Schemas Pydantic v2 del módulo EPT (EPIC-03)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.domain.enums_ept import (
    EstadoCumplimiento,
    EstadoEpt,
    FactorRiesgo,
    FactorRiesgoLegado,
)
from app.util.rut import RutInvalidoError, normalizar_rut


# ──────────────────────────────
# CasoEpt
# ──────────────────────────────

MAX_FACTORES_ADICIONALES = 2  # 3 factores en total con el principal (D11)


def _validar_adicionales(v: list[FactorRiesgo] | None) -> list[FactorRiesgo] | None:
    if v is None:
        return v
    if len(v) > MAX_FACTORES_ADICIONALES:
        raise ValueError("Se pueden elegir hasta 3 factores de riesgo en total.")
    if len(set(v)) != len(v):
        raise ValueError("Los factores de riesgo no se pueden repetir.")
    return v


def _sin_repetir_principal(principal: FactorRiesgo | None, adicionales: list[FactorRiesgo] | None) -> None:
    if principal is not None and adicionales and principal in adicionales:
        raise ValueError("El factor principal no se repite entre los adicionales.")


class CasoEptCreate(BaseModel):
    """Alta de caso EPT (CEPA-030). Campos obligatorios = RN-1."""

    ingreso_id: int
    mes: str
    fecha_ingreso_ept: date
    nombre_trabajador: str
    rut_trabajador: str
    region_trabajador: str
    eista: str
    factor_riesgo: FactorRiesgo
    factores_adicionales: list[FactorRiesgo] = []
    corresponde_ept: bool = True
    # datos empleador (opcionales; al menos razon_social recomendada)
    razon_social: str | None = None
    unidad_cargo_horario: str | None = None

    @field_validator("rut_trabajador")
    @classmethod
    def _rut_valido(cls, v: str) -> str:
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v}") from exc

    _adicionales = field_validator("factores_adicionales")(_validar_adicionales)

    @model_validator(mode="after")
    def _principal_unico(self) -> "CasoEptCreate":
        _sin_repetir_principal(self.factor_riesgo, self.factores_adicionales)
        return self


class CasoEptUpdate(BaseModel):
    """Actualización parcial del caso EPT. Todos los campos son opcionales."""

    mes: str | None = None
    fecha_ingreso_ept: date | None = None
    nombre_trabajador: str | None = None
    rut_trabajador: str | None = None
    region_trabajador: str | None = None
    eista: str | None = None
    factor_riesgo: FactorRiesgo | None = None
    # Lista completa de adicionales: [] los borra; ausente no los toca.
    factores_adicionales: list[FactorRiesgo] | None = None
    corresponde_ept: bool | None = None
    estado: EstadoEpt | None = None
    razon_social: str | None = None
    unidad_cargo_horario: str | None = None

    @field_validator("rut_trabajador")
    @classmethod
    def _rut_valido(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v}") from exc

    _adicionales = field_validator("factores_adicionales")(_validar_adicionales)

    @model_validator(mode="after")
    def _principal_unico(self) -> "CasoEptUpdate":
        _sin_repetir_principal(self.factor_riesgo, self.factores_adicionales)
        return self


class CasoEptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    mes: str
    fecha_ingreso_ept: date
    nombre_trabajador: str
    rut_trabajador: str
    region_trabajador: str
    eista: str
    # Lectura tolerante: los casos creados antes de QA-003 conservan un valor
    # legado. La escritura (Create/Update) solo acepta FactorRiesgo.
    factor_riesgo: FactorRiesgo | FactorRiesgoLegado
    factores_adicionales: list[str] = []
    corresponde_ept: bool
    estado: EstadoEpt
    razon_social: str | None
    unidad_cargo_horario: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("factores_adicionales", mode="before")
    @classmethod
    def _separar(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, str):
            return [f for f in v.split(",") if f]
        return v


# ──────────────────────────────
# ContactoEpt
# ──────────────────────────────

class ContactoEptPayload(BaseModel):
    """Payload de creación de contacto EPT — solo correo (caso_ept_id viene de la URL)."""

    correo: EmailStr


class ContactoEptCreate(BaseModel):
    """Alta de contacto de coordinación EPT (CEPA-030 CA-3 / RN-4)."""

    caso_ept_id: int
    correo: EmailStr


class ContactoEptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_ept_id: int
    correo: str
    created_at: datetime


# ──────────────────────────────
# ProcesoEpt
# ──────────────────────────────

class ProcesoEptCreate(BaseModel):
    """Creación del proceso EPT (CEPA-031). Solo aplica si corresponde_ept=True."""

    caso_ept_id: int
    plazo_evid_denunciante: date | None = None
    plazo_insumos_empresa: date | None = None
    hay_testigos: bool = False
    testigos_cantidad: int = 0
    num_entrevistas: int = 0
    insumos_eista: str | None = None
    doc_incumplimiento: str | None = None
    observaciones: str | None = None


class ProcesoEptUpdate(BaseModel):
    """Actualización del proceso EPT (todos opcionales)."""

    plazo_evid_denunciante: date | None = None
    plazo_insumos_empresa: date | None = None
    hay_testigos: bool | None = None
    testigos_cantidad: int | None = None
    num_entrevistas: int | None = None
    insumos_eista: str | None = None
    doc_incumplimiento: str | None = None
    observaciones: str | None = None


class ProcesoEptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_ept_id: int
    plazo_evid_denunciante: date | None
    plazo_insumos_empresa: date | None
    hay_testigos: bool
    testigos_cantidad: int
    num_entrevistas: int
    insumos_eista: str | None
    doc_incumplimiento: str | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime


# ──────────────────────────────
# PlazoEpt
# ──────────────────────────────

class PlazoEptCreate(BaseModel):
    """Registro de plazos regulatorios ISL (CEPA-032). Solo aplica si corresponde_ept=True."""

    caso_ept_id: int
    plazo_informe_ept: date | None = None
    plazo_portal_isl: date | None = None
    fecha_entrega_isl: date | None = None


class PlazoEptUpdate(BaseModel):
    """Actualización de plazos ISL, fecha de envío y estado."""

    plazo_informe_ept: date | None = None
    plazo_portal_isl: date | None = None
    fecha_entrega_isl: date | None = None
    fecha_envio: date | None = None


class PlazoEptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_ept_id: int
    plazo_informe_ept: date | None
    plazo_portal_isl: date | None
    fecha_entrega_isl: date | None
    fecha_envio: date | None
    estado_informe: EstadoCumplimiento
    estado_entrega_isl: EstadoCumplimiento
    created_at: datetime
    updated_at: datetime
