"""CEPA-090 — Dashboard multiprograma con filtros (D5).

Endpoint de solo lectura. Agrega indicadores sobre todos los programas.
Sin tablas nuevas: lee de ingreso (EPIC-09 D1 cols) y cita (EPIC-09 D2).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import ResumenDashboard
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


def _construir_filtros(
    fecha_desde: date | None,
    fecha_hasta: date | None,
    programa: str | None,
    profesional_id: int | None,
    sexo: str | None,
    tramo_etario: str | None,
    region: str | None,
    comuna: str | None,
    diagnostico: str | None,
    tipo_alta: str | None,
    modelo_tratamiento: str | None,
    tipo_ingreso: str | None,
    tipo_convenio: str | None,
    especialidad: str | None,
    tipo_atencion: str | None,
) -> FiltrosDashboard:
    return FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        programa=programa,
        profesional_id=profesional_id,
        sexo=sexo,
        tramo_etario=tramo_etario,
        region=region,
        comuna=comuna,
        diagnostico=diagnostico,
        tipo_alta=tipo_alta,
        modelo_tratamiento=modelo_tratamiento,
        tipo_ingreso=tipo_ingreso,
        tipo_convenio=tipo_convenio,
        especialidad=especialidad,
        tipo_atencion=tipo_atencion,
    )


@router.get("", response_model=ResumenDashboard)
def get_dashboard(
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    programa: str | None = Query(None),
    profesional_id: int | None = Query(None),
    sexo: str | None = Query(None),
    tramo_etario: str | None = Query(None),
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    diagnostico: str | None = Query(None),
    tipo_alta: str | None = Query(None),
    modelo_tratamiento: str | None = Query(None),
    tipo_ingreso: str | None = Query(None),
    tipo_convenio: str | None = Query(None),
    especialidad: str | None = Query(None),
    tipo_atencion: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(_lector),
) -> ResumenDashboard:
    """CA-1..CA-4: dashboard multiprograma con filtros combinables (AND). RN-4: tiempo real."""

    filtros = _construir_filtros(
        fecha_desde, fecha_hasta, programa, profesional_id, sexo,
        tramo_etario, region, comuna, diagnostico, tipo_alta,
        modelo_tratamiento, tipo_ingreso, tipo_convenio, especialidad, tipo_atencion,
    )

    # ── Total ingresos ────────────────────────────────────────────────────────
    stmt_ingresos = select(func.count()).select_from(Ingreso)
    stmt_ingresos = aplicar_filtros_ingreso(stmt_ingresos, Ingreso, filtros)
    total_ingresos = db.execute(stmt_ingresos).scalar_one()

    # ── Citas por estado (join ingreso para aplicar filtros de dimensión) ─────
    def _count_citas_estado(estado: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Cita)
            .join(Ingreso, Cita.ingreso_id == Ingreso.id)
            .where(Cita.estado == estado)
        )
        stmt = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
        return db.execute(stmt).scalar_one()

    total_atenciones = _count_citas_estado("realizada")
    total_inasistencias = _count_citas_estado("inasistencia")
    total_anulaciones = _count_citas_estado("anulada")
    total_citas_agendadas = _count_citas_estado("agendada")

    # ── Carga por profesional ─────────────────────────────────────────────────
    stmt_carga = (
        select(Ingreso.profesional_id, func.count(Ingreso.id).label("total"))
        .select_from(Ingreso)
        .group_by(Ingreso.profesional_id)
    )
    stmt_carga = aplicar_filtros_ingreso(stmt_carga, Ingreso, filtros)
    carga_rows = db.execute(stmt_carga).all()
    carga_por_profesional = [
        {"profesional_id": r.profesional_id, "total_ingresos": r.total}
        for r in carga_rows
    ]

    # ── Cumplimiento convenios (atenciones por tipo_convenio) ─────────────────
    stmt_conv = (
        select(Ingreso.tipo_convenio, func.count(Cita.id).label("total"))
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.estado == "realizada")
        .group_by(Ingreso.tipo_convenio)
    )
    stmt_conv = aplicar_filtros_ingreso(stmt_conv, Ingreso, filtros)
    conv_rows = db.execute(stmt_conv).all()
    cumplimiento_convenios = [
        {"tipo_convenio": r.tipo_convenio, "total_realizadas": r.total}
        for r in conv_rows
    ]

    return ResumenDashboard(
        total_ingresos=total_ingresos,
        total_atenciones=total_atenciones,
        total_inasistencias=total_inasistencias,
        total_anulaciones=total_anulaciones,
        total_citas_agendadas=total_citas_agendadas,
        carga_por_profesional=carga_por_profesional,
        cumplimiento_convenios=cumplimiento_convenios,
        filtros_aplicados=filtros.model_dump(exclude_none=True),
    )
