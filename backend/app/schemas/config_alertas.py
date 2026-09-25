"""Schemas de la configuración de alertas y festivos (COMP-2609-07)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums_alertas import TipoAlerta


class ConfigAlertaItem(BaseModel):
    tipo: TipoAlerta
    dias: int = Field(ge=0, le=365)
    habiles: bool
    activo: bool

    @model_validator(mode="after")
    def _umbral_gaf(self) -> "ConfigAlertaItem":
        # En gaf_licencia ``dias`` es el límite superior del tramo umbral (porcentaje GAF).
        if self.tipo == TipoAlerta.GAF_LICENCIA and self.dias > 100:
            raise ValueError("El umbral de GAF va de 0 a 100")
        return self


class ConfigAlertaRead(ConfigAlertaItem):
    actualizado_por: str | None = None


class FestivoCreate(BaseModel):
    fecha: date
    descripcion: str = Field(min_length=1, max_length=200)


class FestivoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    descripcion: str
