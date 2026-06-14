from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FichaClinicaCreate(BaseModel):
    """Payload de push de datos clínicos (sistema externo → CEPA)."""

    folio: str
    origen: str
    contenido: dict[str, Any]


class FichaClinicaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    origen: str
    contenido: dict[str, Any]
    created_at: datetime


class PullSalutemRequest(BaseModel):
    """Solicitud de pull de ficha clínica desde SALUTEM."""

    folio: str
