"""Schemas de la integración IMED (CEPA-122).

Reutiliza los principios de §8.1 (JWT, JSON, versionado) — no introduce contrato paralelo.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ImedLicenciaCreate(BaseModel):
    """Payload de recepción de licencia médica electrónica desde IMED."""

    folio: str
    tipo: Literal["licencia_medica"]
    datos: dict[str, Any]


class ImedRecetaCreate(BaseModel):
    """Payload de recepción de receta electrónica desde IMED."""

    folio: str
    tipo: Literal["receta_electronica"]
    datos: dict[str, Any]


class ImedPayloadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    tipo: str
    datos: dict[str, Any]
    created_at: datetime
