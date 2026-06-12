"""Schemas Pydantic v2 para configuración de formularios dinámicos (CEPA-110 / CEPA-111)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.form_validator import VALID_FIELD_TYPES


class FieldDefIn(BaseModel):
    """Campo recibido al crear/editar una versión de formulario."""

    field_key: str
    label: str
    field_type: str
    required: bool = False
    system_locked: bool = False
    domain_values: list[str] | None = None
    display_order: int = 0
    active: bool = True

    @field_validator("field_type")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        # Empty string is allowed in drafts; the form_validator catches it at publish time.
        # Non-empty values must be in the valid set.
        if v and v not in VALID_FIELD_TYPES:
            raise ValueError(
                f"field_type '{v}' no válido. Valores aceptados: {sorted(VALID_FIELD_TYPES)}"
            )
        return v


class FieldDefOut(BaseModel):
    """Campo devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field_key: str
    label: str
    field_type: str | None
    required: bool
    system_locked: bool
    domain_values: list[str] | None
    display_order: int
    active: bool


class FormVersionCreate(BaseModel):
    """Cuerpo de la petición de creación/actualización de borrador."""

    fields: list[FieldDefIn]


class FormVersionRead(BaseModel):
    """Versión de formulario devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    form_def_id: int
    version_num: int
    status: str
    published_at: datetime | None
    created_by: str
    created_at: datetime
    fields: list[FieldDefOut]


class FormDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    form_key: str
    created_at: datetime
    versions: list[FormVersionRead] = []


class PublishResult(BaseModel):
    """Resultado de un intento de publicación."""

    success: bool
    version_id: int | None
    errors: list[dict[str, str]]
