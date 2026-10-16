"""Schemas del catálogo de profesionales (agendamiento)."""

from datetime import datetime

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


class ImportacionSalutemResultado(BaseModel):
    creados: int
