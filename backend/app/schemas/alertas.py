"""Schemas Pydantic v2 para el módulo de alertas unificadas (EPIC-10)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums_alertas import EstadoAlerta


class AlertaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    estado: str
    caso_id: int
    caso_tipo: str
    usuario_id: int | None
    plazo_objetivo: datetime
    ventana_dias: int
    generada_en: datetime
    resuelta_en: datetime | None
    email_enviado: bool
    # Paciente del caso, para abrir su ficha desde el panel. Solo se resuelve en el listado
    # y para los casos que cuelgan de un ingreso (ODA, ingreso); el resto queda en None.
    paciente_id: int | None = None


class AlertaUpdate(BaseModel):
    estado: EstadoAlerta


class JobResultado(BaseModel):
    alertas_generadas: int
    timestamp: datetime
    omitidas: int = 0
