"""QA-004 — Esquemas del reporte de ingresos del período."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class IngresoReporteItem(BaseModel):
    """Una fila por ingreso; los borradores de SALUTEM sin folio salen como pendientes."""

    paciente_id: int
    ingreso_id: int | None = None
    paciente_nombre: str
    paciente_rut: str | None = None
    folio: str | None = None
    pendiente: bool
    tipo_ingreso: str | None = None
    programa: str | None = None
    region: str | None = None
    tipo_convenio: str | None = None
    fecha: date


class ConteoIngreso(BaseModel):
    etiqueta: str
    total: int


class ReporteIngresosResponse(BaseModel):
    periodo_desde: date
    periodo_hasta: date
    total: int
    total_con_folio: int
    total_pendientes: int
    por_tipo_ingreso: list[ConteoIngreso]
    por_region: list[ConteoIngreso]
    por_programa: list[ConteoIngreso]
    por_convenio: list[ConteoIngreso]
    items: list[IngresoReporteItem]
