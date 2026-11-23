"""Schemas del mantenedor de convenios."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _limpiar(valor: str | None) -> str | None:
    if valor is None:
        return None
    return " ".join(valor.split())


class ConvenioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    salutem_id: int | None
    activo_salutem: bool
    visible: bool
    seleccionable: bool
    sincronizado_en: datetime | None


class ConvenioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)

    @field_validator("nombre", mode="before")
    @classmethod
    def _sin_espacios_sobrantes(cls, v: str) -> str:
        return _limpiar(v) if isinstance(v, str) else v


class ConvenioUpdate(BaseModel):
    visible: bool | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("nombre", mode="before")
    @classmethod
    def _sin_espacios_sobrantes(cls, v: str | None) -> str | None:
        return _limpiar(v) if isinstance(v, str) else v


class ActualizacionConvenios(BaseModel):
    creados: int
    actualizados: int
    desactivados: int
    errores: list[str]


class ConvenioSugerido(BaseModel):
    convenio: ConvenioRead | None = None
