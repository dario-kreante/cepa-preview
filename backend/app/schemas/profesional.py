"""Schemas del catálogo de profesionales (agendamiento)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _limpiar(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = " ".join(valor.split())
    return valor or None


class ProfesionalCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    especialidad: str | None = Field(default=None, max_length=80)

    @field_validator("nombre", "especialidad")
    @classmethod
    def _sin_espacios_sobrantes(cls, v: str | None) -> str | None:
        return _limpiar(v)

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, v: str | None) -> str:
        if not v:
            raise ValueError("El nombre es obligatorio")
        return v


class ProfesionalUpdate(BaseModel):
    """Campos opcionales: solo se cambia lo que viene."""

    nombre: str | None = Field(default=None, min_length=1, max_length=160)
    especialidad: str | None = Field(default=None, max_length=80)
    activo: bool | None = None

    @field_validator("nombre", "especialidad")
    @classmethod
    def _sin_espacios_sobrantes(cls, v: str | None) -> str | None:
        return _limpiar(v)

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, v: str | None) -> str:
        # Solo corre si el campo viene: omitirlo deja el nombre como está.
        if not v:
            raise ValueError("El nombre no puede quedar vacío")
        return v


class ProfesionalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    especialidad: str | None
    origen: str
    activo: bool
    created_at: datetime
    # Lo que arma el sync desde SALUTEM; nulos en los profesionales cargados a mano.
    salutem_profesional_id: int | None = None
    especialidades: list[str] | None = None
    sucursales: list[str] | None = None
    primera_atencion: date | None = None
    ultima_atencion: date | None = None
    sincronizado_en: datetime | None = None


class ImportacionSalutemResultado(BaseModel):
    creados: int
    actualizados: int = 0
    adoptados: int = 0
    vinculados: int = 0
    errores: list[str] = []


class AtencionPorEspecialidad(BaseModel):
    especialidad: str
    total: int


class AtencionProfesionalRead(BaseModel):
    ficha_id: int
    fecha: date | None
    especialidad: str | None
    folio: str
    ingreso_id: int
    paciente_id: int
    paciente: str


class ActividadProfesionalRead(BaseModel):
    """Actividad del profesional según las fichas y controles vinculados a él."""

    profesional_id: int
    total_atenciones: int
    atenciones_por_especialidad: list[AtencionPorEspecialidad]
    total_controles: int
    pacientes_distintos: int
    primera_atencion: date | None
    ultima_atencion: date | None
    ultimas_atenciones: list[AtencionProfesionalRead]
