from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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


class IngresoUpdate(BaseModel):
    """Edición de la ficha de ingreso (BUG-2608-01 / CEPA-010). Actualización parcial.

    RUT y folio no se editan: el RUT ancla la integración con SALUTEM y el folio
    tiene reglas propias (PA-v5-01). Enviarlos es un 422, no se ignoran en silencio.
    """

    model_config = ConfigDict(extra="forbid")

    # datos del paciente
    nombre: str | None = None
    sexo: Sexo | None = None
    edad: int | None = None
    region: str | None = None
    comuna: str | None = None
    telefono: str | None = None
    correo: str | None = None
    # datos del ingreso
    diagnostico: str | None = None
    tipo_derivacion: TipoDerivacion | None = None
    tipo_ingreso: TipoIngreso | None = None
    modelo_tratamiento: str | None = None
    fecha_ingreso: date | None = None
    fecha_diep_diat: date | None = None
    razon_social: str | None = None
    numero_siniestro: str | None = None

    @field_validator("edad")
    @classmethod
    def _edad_positiva(cls, v: int | None) -> int | None:
        if v is not None and (v <= 0 or v > 130):
            raise ValueError("edad fuera de rango")
        return v

    @model_validator(mode="after")
    def _obligatorios_no_se_vacian(self) -> "IngresoUpdate":
        obligatorios = (
            "nombre", "sexo", "edad", "region", "diagnostico",
            "tipo_derivacion", "tipo_ingreso", "modelo_tratamiento", "fecha_ingreso",
        )
        vaciados = [c for c in obligatorios if c in self.model_fields_set and getattr(self, c) is None]
        if vaciados:
            raise ValueError(f"Campos obligatorios no pueden quedar vacíos: {', '.join(vaciados)}")
        return self


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
