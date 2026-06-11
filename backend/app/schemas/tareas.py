"""Schemas Pydantic v2 para el módulo de tareas pendientes por rol (EPIC-10, CEPA-103)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums_alertas import EstadoTarea


class TareaItemCreate(BaseModel):
    titulo: str
    descripcion: str | None = None
    tipo_tarea: str
    usuario_id: int
    caso_id: int | None = None
    caso_tipo: str | None = None


class TareaItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str | None
    estado: str
    tipo_tarea: str
    usuario_id: int
    caso_id: int | None
    caso_tipo: str | None
    creada_en: datetime
    completada_en: datetime | None
    completada_por: str | None


class TareaItemUpdate(BaseModel):
    estado: EstadoTarea
