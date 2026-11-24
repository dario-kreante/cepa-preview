"""Schemas Pydantic v2 compartidos por los endpoints de EPIC-09."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

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


class ConteoEtiqueta(BaseModel):
    etiqueta: str
    total: int


class PuntoTendencia(BaseModel):
    semana: date  # lunes de la semana
    atendidas: int
    inasistencias: int


class DashboardOperativo(BaseModel):
    """Respuesta de GET /dashboard/operativo: atenciones SALUTEM + pendientes de gestión.

    Las cifras de atenciones y de ingresos/altas/controles son del período; el resto
    (activos, licencias, ODAs, EPT, borradores, alertas) es el estado a hoy.
    """

    periodo_desde: date
    periodo_hasta: date
    pacientes_activos: int
    ingresos_periodo: int
    altas_periodo: int
    atenciones: int
    inasistencias: int
    anulaciones: int
    tasa_inasistencia: float | None
    agendadas_periodo: int
    agendadas_proximas: int
    controles_periodo: int
    licencias_activas: int
    licencias_pendientes_isl: int
    odas_vencidas: int
    odas_por_vencer: int
    ept_abiertos: int
    pacientes_pendientes_folio: int
    alertas_abiertas: int
    alertas_por_tipo: list[ConteoEtiqueta]
    activos_por_programa: list[ConteoEtiqueta]
    atenciones_por_especialidad: list[ConteoEtiqueta]
    atenciones_por_profesional: list[ConteoEtiqueta]
    tendencia_semanal: list[PuntoTendencia]


class IngresosActivos(BaseModel):
    """Respuesta de GET /dashboard/activos (píldora "N activos" del Topbar)."""
    total: int


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
    agendadas: int = 0  # DD-6: incluido para que columnas reconcilien con total_citas
    recepcionadas: int = 0  # QA-002: el paciente llegó y la atención aún no se evoluciona


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
    # None cuando quien atendió no está en el catálogo de profesionales.
    profesional_id: int | None
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
    folio: str | None = None  # folio real del CEPA; `folio_id` es el id interno
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
    """Adherencia y avance de un folio.

    Criterio (Fase 2, decisión 10): ``citas_agendadas`` es el denominador y cuenta solo las
    citas ya resueltas, ``realizada`` más ``inasistencia``. Las anuladas y las agendadas
    futuras no cuentan. Solo se consideran citas de SALUTEM.
    """

    folio_id: int
    citas_agendadas: int  # denominador: realizadas + inasistencias
    citas_realizadas: int
    pct_adherencia: float | None  # None si el denominador es 0
    sesiones_realizadas: int
    sesiones_plan: int | None
    aumentos_isl: int
    pct_avance: float | None


class ReporteAdherenciaResponse(BaseModel):
    items: list[AdherenciaPaciente]


# ── ODAS vencidas (CEPA-097) ──────────────────────────────────────────────────

class OrdenCobertura(BaseModel):
    """Una orden (ODA u OPA) del paciente dentro del período del cruce de cobertura."""

    identificador: str
    # «ODA» (Ambulatoria) | «OPA» (OPA/OPAEP); None si la orden se cargó antes de guardar el tipo.
    tipo: str | None
    fecha_inicio: date | None
    fecha_termino: date


class ODAVencidaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # `id` es la ODA vencida sobre la que se gestiona (PATCH /odas/{id}/gestion).
    # Los campos propios de la ODA son None en las filas de atendidos sin ODA.
    id: int | None
    folio_id: int
    # N° de la orden en ISL, el folio del CEPA y el paciente: lo que el equipo
    # reconoce. `id` y `folio_id` son internos y no se muestran (QA-007).
    identificador: str | None
    folio: str
    paciente_nombre: str
    paciente_rut: str | None
    fecha_registro: date | None
    fecha_vencimiento: date | None
    programa: str | None
    region: str | None
    comuna: str | None
    # QA-007: cruce de cobertura (una fila por paciente; varias órdenes → varias entradas).
    ordenes: list[OrdenCobertura] = []
    fechas_atencion: list[date] = []
    cobertura: Literal["CUBRE", "SOLICITAR"] = "SOLICITAR"
    estado_gestion: Literal["pendiente", "solicitada", "recibida"] | None = "pendiente"


class ReporteODASVencidasResponse(BaseModel):
    fecha_consulta: date
    total: int
    items: list[ODAVencidaItem]


# ── Estado de ODA por paciente (QA-006) ────────────────────────────────────────

class ODAEstadoItem(BaseModel):
    ingreso_id: int
    folio: str
    paciente_nombre: str
    paciente_rut: str | None
    fecha_ingreso: date
    estado_caso: str
    programa: str | None
    estado_oda: Literal["vigente", "por_vencer", "vencida", "sin_oda"]
    fecha_vencimiento: date | None
    # Días hasta el vencimiento; negativo = vencida hace N días; None = sin ODA.
    dias_para_vencer: int | None


class ReporteODAEstadoResponse(BaseModel):
    fecha_consulta: date
    total: int
    dias_por_vencer: int
    items: list[ODAEstadoItem]
