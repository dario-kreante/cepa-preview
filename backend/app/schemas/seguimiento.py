from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.enums import EstadoEvaluacion


class SeguimientoUpdate(BaseModel):
    """Actualización parcial de hitos del seguimiento (§7.1.2). Todos opcionales."""

    fecha_acogida: date | None = None
    programa: str | None = None
    eval_medica_estado: EstadoEvaluacion | None = None
    eval_medica_medico: str | None = None
    eval_medica_fecha: date | None = None
    eval_psico_estado: EstadoEvaluacion | None = None
    eval_psico_psicologo: str | None = None
    eval_psico_fecha: date | None = None
    obstaculizacion: bool | None = None
    plazo_informe: int | None = None
    fecha_envio_informe: date | None = None
    reca_ep_ec: str | None = None


class SeguimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    fecha_acogida: date | None
    programa: str | None
    eval_medica_estado: EstadoEvaluacion | None
    eval_medica_medico: str | None
    eval_medica_fecha: date | None
    eval_psico_estado: EstadoEvaluacion | None
    eval_psico_psicologo: str | None
    eval_psico_fecha: date | None
    obstaculizacion: bool
    plazo_informe: int | None
    fecha_envio_informe: date | None
    reca_ep_ec: str | None


class ValidacionPlazo(BaseModel):
    cumplimiento: str  # "en_plazo" | "fuera_de_plazo" | "sin_datos"
    detalle: str
