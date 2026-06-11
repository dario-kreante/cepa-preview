"""Helper de filtros comunes para el dashboard y reportes de EPIC-09.

FiltrosDashboard centraliza los 14 filtros D5. aplicar_filtros_ingreso
aplica el subconjunto relevante a cualquier SELECT que incluya la tabla ingreso.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Select


class FiltrosDashboard(BaseModel):
    """Parámetros de filtrado combinables (AND) para dashboard y reportes.

    Todos los campos son opcionales; None significa «sin restricción».
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Temporal
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    granularidad: str | None = None  # "diario" | "semanal" | "mensual" | "anual"

    # Dimensiones de D5
    programa: str | None = None
    profesional_id: int | None = None
    especialidad: str | None = None
    tipo_atencion: str | None = None
    diagnostico: str | None = None
    tipo_alta: str | None = None
    tramo_etario: str | None = None
    sexo: str | None = None
    region: str | None = None
    comuna: str | None = None
    modelo_tratamiento: str | None = None
    tipo_ingreso: str | None = None
    tipo_convenio: str | None = None
    duracion: str | None = None  # relevante para telemedicina

    @model_validator(mode="after")
    def _validar_rango_fechas(self) -> "FiltrosDashboard":
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_desde > self.fecha_hasta:
                raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")
        return self


def aplicar_filtros_ingreso(stmt: Select, modelo_ingreso: Any, f: FiltrosDashboard) -> Select:
    """Aplica los filtros activos de FiltrosDashboard a una SELECT sobre la tabla ingreso.

    Solo aplica los filtros cuyo valor no es None. Portable: usa ORM (sin SQL específico).
    Para columnas de fecha, asume que el modelo tiene columna `fecha_ingreso: Date`.
    """
    if f.fecha_desde is not None:
        stmt = stmt.where(modelo_ingreso.fecha_ingreso >= f.fecha_desde)
    if f.fecha_hasta is not None:
        stmt = stmt.where(modelo_ingreso.fecha_ingreso <= f.fecha_hasta)
    if f.programa is not None:
        stmt = stmt.where(modelo_ingreso.programa == f.programa)
    if f.profesional_id is not None:
        stmt = stmt.where(modelo_ingreso.profesional_id == f.profesional_id)
    if f.especialidad is not None:
        stmt = stmt.where(modelo_ingreso.especialidad == f.especialidad)
    if f.tipo_atencion is not None:
        stmt = stmt.where(modelo_ingreso.tipo_atencion == f.tipo_atencion)
    if f.diagnostico is not None:
        stmt = stmt.where(modelo_ingreso.diagnostico == f.diagnostico)
    if f.tipo_alta is not None:
        stmt = stmt.where(modelo_ingreso.tipo_alta == f.tipo_alta)
    if f.tramo_etario is not None:
        stmt = stmt.where(modelo_ingreso.tramo_etario == f.tramo_etario)
    if f.sexo is not None:
        stmt = stmt.where(modelo_ingreso.sexo == f.sexo)
    if f.region is not None:
        stmt = stmt.where(modelo_ingreso.region == f.region)
    if f.comuna is not None:
        stmt = stmt.where(modelo_ingreso.comuna == f.comuna)
    if f.modelo_tratamiento is not None:
        stmt = stmt.where(modelo_ingreso.modelo_tratamiento == f.modelo_tratamiento)
    if f.tipo_ingreso is not None:
        stmt = stmt.where(modelo_ingreso.tipo_ingreso == f.tipo_ingreso)
    if f.tipo_convenio is not None:
        stmt = stmt.where(modelo_ingreso.tipo_convenio == f.tipo_convenio)
    return stmt
