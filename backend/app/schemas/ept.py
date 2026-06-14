"""Schemas Pydantic v2 del módulo EPT (EPIC-03)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.domain.enums_ept import EstadoCumplimiento, EstadoEpt, FactorRiesgo
from app.util.rut import RutInvalidoError, normalizar_rut


# ──────────────────────────────
# CasoEpt
# ──────────────────────────────

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


class CasoEptUpdate(BaseModel):
    """Actualización parcial del caso EPT. Todos los campos son opcionales."""

    mes: str | None = None
    fecha_ingreso_ept: date | None = None
    nombre_trabajador: str | None = None
    rut_trabajador: str | None = None
    region_trabajador: str | None = None
    eista: str | None = None
    factor_riesgo: FactorRiesgo | None = None
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
    factor_riesgo: FactorRiesgo
    corresponde_ept: bool
    estado: EstadoEpt
    razon_social: str | None
    unidad_cargo_horario: str | None
    created_at: datetime
    updated_at: datetime


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
