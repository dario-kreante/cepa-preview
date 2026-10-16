from datetime import date, datetime

from pydantic import BaseModel, Field


class PacientePendienteRead(BaseModel):
    """Fila de la lista de pacientes borrador pendientes de folio."""

    id: int
    nombre: str
    rut: str | None
    identificacion_salutem: str | None
    salutem_persona_id: int | None
    creado_en: datetime
    primera_atencion: date | None
    ultima_atencion: date | None
    atenciones: int
    especialidades: list[str]


class DescarteIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)
