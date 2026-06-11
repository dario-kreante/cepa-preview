"""Schemas Pydantic v2 para ventanas de proceso (CEPA-096)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


PROCESOS_VALIDOS = frozenset({"licencias", "farmacos", "auditoria", "reintegro", "controles"})


class VentanaProcesoCreate(BaseModel):
    proceso: str
    columnas_visibles: list[str]
    orden_por_defecto: str | None = None

    @model_validator(mode="after")
    def _validar_proceso(self) -> "VentanaProcesoCreate":
        if self.proceso not in PROCESOS_VALIDOS:
            raise ValueError(f"proceso debe ser uno de: {sorted(PROCESOS_VALIDOS)}")
        return self


class VentanaProcesoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proceso: str
    columnas_visibles: list[str]
    orden_por_defecto: str | None
    creado_por: str | None
    created_at: datetime
