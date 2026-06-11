"""Schemas para PlanTratamiento — DD-2 (EPIC-09 rework)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlanTratamientoUpsert(BaseModel):
    """Cuerpo del PUT /ingresos/{id}/plan-tratamiento (upsert)."""

    sesiones_plan: int | None = Field(None, ge=1)
    aumentos_isl: int = Field(0, ge=0)


class PlanTratamientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    sesiones_plan: int | None
    aumentos_isl: int
