"""Schemas Pydantic v2 compartidos por los endpoints de EPIC-09."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Respuestas genéricas ───────────────────────────────────────────────────────

class MetricaSimple(BaseModel):
    """Metrica numérica etiquetada (para widgets del dashboard)."""
    etiqueta: str
    valor: int | float
    unidad: str | None = None


class ResumenDashboard(BaseModel):
    """Respuesta del endpoint GET /dashboard."""
    model_config = ConfigDict(from_attributes=True)

    total_ingresos: int
    total_atenciones: int
    total_inasistencias: int
    total_anulaciones: int
    total_citas_agendadas: int
    carga_por_profesional: list[dict[str, Any]]
    cumplimiento_convenios: list[dict[str, Any]]
    filtros_aplicados: dict[str, Any]


# ── Reportes operativos (CEPA-091) ────────────────────────────────────────────

class ReporteOperativoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date
    programa: str | None
    profesional_id: int | None
    total_citas: int
    realizadas: int
    inasistencias: int
    anuladas: int


class ReporteOperativoResponse(BaseModel):
    items: list[ReporteOperativoItem]
    totales: dict[str, int]


# ── Cumplimiento por convenio (CEPA-092) ─────────────────────────────────────

class CumplimientoConvenioItem(BaseModel):
    tipo_convenio: str
    periodo: str
    total_atenciones: int
    total_inasistencias: int
    total_anulaciones: int
    indicadores_comprometidos: dict[str, Any] | None = None


class ReporteCumplimientoResponse(BaseModel):
    convenio: str
    periodo: str
    items: list[CumplimientoConvenioItem]


# ── Carga laboral (CEPA-093) ──────────────────────────────────────────────────

class CargaProfesionalItem(BaseModel):
    profesional_id: int
    nombre_profesional: str | None
    especialidad: str | None
    total_casos: int
    total_atenciones: int


class ReporteCargaLaboralResponse(BaseModel):
    periodo_desde: date
    periodo_hasta: date
    items: list[CargaProfesionalItem]


# ── Licencias acumuladas (CEPA-094) ──────────────────────────────────────────

class LicenciaAcumuladaItem(BaseModel):
    folio_id: int
    rut_paciente: str | None
    total_dias_acumulados: int
    licencias_internas: int
    licencias_externas: int


class ReporteLicenciasResponse(BaseModel):
    periodo_desde: date | None
    periodo_hasta: date | None
    items: list[LicenciaAcumuladaItem]


# ── Adherencia y avance (CEPA-095) ───────────────────────────────────────────

class AdherenciaPaciente(BaseModel):
    folio_id: int
    citas_agendadas: int
    citas_realizadas: int
    pct_adherencia: float | None  # None si citas_agendadas == 0
    sesiones_realizadas: int
    sesiones_plan: int | None
    aumentos_isl: int
    pct_avance: float | None


class ReporteAdherenciaResponse(BaseModel):
    items: list[AdherenciaPaciente]


# ── ODAS vencidas (CEPA-097) ──────────────────────────────────────────────────

class ODAVencidaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio_id: int
    fecha_registro: date | None
    fecha_vencimiento: date
    programa: str | None
    region: str | None
    comuna: str | None


class ReporteODASVencidasResponse(BaseModel):
    fecha_consulta: date
    total: int
    items: list[ODAVencidaItem]
