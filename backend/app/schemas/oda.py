from datetime import date

from pydantic import BaseModel, ConfigDict


class OdaCreate(BaseModel):
    """Registro de ODA. La fecha de vencimiento es obligatoria (CEPA-015 RN-2)."""

    identificador: str
    fecha_vencimiento: date


class OdaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    identificador: str
    fecha_vencimiento: date
    vigente: bool


class OdaAlerta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    identificador: str
    fecha_vencimiento: date
