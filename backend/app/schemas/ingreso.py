from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.enums import (
    EstadoCaso,
    Sexo,
    TipoAlta,
    TipoDerivacion,
    TipoIngreso,
)
from app.util.rut import RutInvalidoError, normalizar_rut


class IngresoCreate(BaseModel):
    """Alta de ingreso en formulario único (CEPA-010). Campos obligatorios = D6.

    DD-3 (EPIC-09 rework): se añaden como opcionales programa, tipo_convenio,
    profesional_id, especialidad y tipo_atencion para que el crear_ingreso los
    almacene en la tabla `ingreso` y los reportes puedan filtrar por ellos.
    """

    rut: str
    nombre: str
    sexo: Sexo
    edad: int
    region: str
    diagnostico: str
    tipo_derivacion: TipoDerivacion
    tipo_ingreso: TipoIngreso
    modelo_tratamiento: str
    fecha_ingreso: date
    # opcionales — datos paciente
    comuna: str | None = None
    telefono: str | None = None
    correo: str | None = None
    fecha_diep_diat: date | None = None
    razon_social: str | None = None
    numero_siniestro: str | None = None
    # folio manual (CEPA-011)
    folio: str | None = None
    es_reingreso: bool = False
    # DD-3: dimensiones de reporte (opcionales)
    programa: str | None = None
    tipo_convenio: str | None = None
    profesional_id: int | None = None
    especialidad: str | None = None
    tipo_atencion: str | None = None

    @field_validator("rut")
    @classmethod
    def _rut_valido(cls, v: str) -> str:
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v}") from exc

    @field_validator("edad")
    @classmethod
    def _edad_positiva(cls, v: int) -> int:
        if v <= 0 or v > 130:
            raise ValueError("edad fuera de rango")
        return v


class PacienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rut: str
    nombre: str
    sexo: str
    edad: int
    region: str
    comuna: str | None
    telefono: str | None
    correo: str | None


class IngresoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    folio: str
    folio_manual: bool
    numero_siniestro: str | None
    fecha_ingreso: date
    fecha_diep_diat: date | None
    tipo_derivacion: TipoDerivacion
    tipo_ingreso: TipoIngreso
    modelo_tratamiento: str
    diagnostico: str
    razon_social: str | None
    estado: EstadoCaso
    tipo_alta: TipoAlta | None
    fecha_alta: date | None
    flag_revision: bool
    observaciones: str | None
    tratamiento_iniciado: bool


class IngresoCierre(BaseModel):
    """Cierre/alta del caso (CEPA-014). Solo se permite estado cerrado o derivado."""

    estado: EstadoCaso
    tipo_alta: TipoAlta | None = None
    fecha_alta: date | None = None
    flag_revision: bool | None = None
    observaciones: str | None = None

    @field_validator("estado")
    @classmethod
    def _solo_cierre_o_derivacion(cls, v: EstadoCaso) -> EstadoCaso:
        if v not in (EstadoCaso.CERRADO, EstadoCaso.DERIVADO):
            raise ValueError("El cierre solo admite estado 'cerrado' o 'derivado'.")
        return v
