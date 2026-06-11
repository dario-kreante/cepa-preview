from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.enums import EstadoConsentimiento


class ConsentimientoUpdate(BaseModel):
    """Registro del estado del consentimiento (CEPA-016). Evidencia opcional (D9)."""

    estado: EstadoConsentimiento
    evidencia_ref: str | None = None
    fecha_firma: date | None = None


class ConsentimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    estado: EstadoConsentimiento
    evidencia_ref: str | None
    fecha_firma: date | None


class ConsentimientoAlerta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    estado: EstadoConsentimiento
