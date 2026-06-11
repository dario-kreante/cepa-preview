"""CEPA-093 — Reporte de carga laboral por profesional.

RN-4: el profesional es un dato de referencia en el registro (no un usuario del sistema — D1).
La carga se computa por profesional_id sobre casos/atenciones del período.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import CargaProfesionalItem, ReporteCargaLaboralResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/carga-laboral", response_model=ReporteCargaLaboralResponse)
def get_carga_laboral(
    fecha_desde: Annotated[date, Query(description="Inicio del período")],
    fecha_hasta: Annotated[date, Query(description="Fin del período")],
    especialidad: str | None = Query(None),
    tipo_atencion: str | None = Query(None),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteCargaLaboralResponse:
    """CA-1..CA-3: carga por profesional en el período, con filtros opcionales."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        especialidad=especialidad,
        tipo_atencion=tipo_atencion,
        programa=programa,
    )

    # Total de casos (ingresos) por profesional
    stmt_casos = (
        select(
            Ingreso.profesional_id,
            Ingreso.especialidad,
            func.count(Ingreso.id).label("total_casos"),
        )
        .select_from(Ingreso)
        .where(Ingreso.fecha_ingreso >= fecha_desde)
        .where(Ingreso.fecha_ingreso <= fecha_hasta)
        .where(Ingreso.profesional_id.is_not(None))
        .group_by(Ingreso.profesional_id, Ingreso.especialidad)
    )
    stmt_casos = aplicar_filtros_ingreso(stmt_casos, Ingreso, filtros)
    rows = db.execute(stmt_casos).all()

    # Total de atenciones por profesional (join citas realizadas)
    stmt_atenciones = (
        select(
            Ingreso.profesional_id,
            func.count(Cita.id).label("total_atenciones"),
        )
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.estado == "realizada")
        .where(Cita.fecha >= fecha_desde)
        .where(Cita.fecha <= fecha_hasta)
        .where(Ingreso.profesional_id.is_not(None))
        .group_by(Ingreso.profesional_id)
    )
    stmt_atenciones = aplicar_filtros_ingreso(stmt_atenciones, Ingreso, filtros)
    atenciones_map: dict[int | None, int] = {
        r.profesional_id: r.total_atenciones
        for r in db.execute(stmt_atenciones).all()
    }

    items = [
        CargaProfesionalItem(
            profesional_id=r.profesional_id,
            nombre_profesional=None,  # D1: el profesional no es usuario
            especialidad=r.especialidad,
            total_casos=r.total_casos,
            total_atenciones=atenciones_map.get(r.profesional_id, 0),
        )
        for r in rows
    ]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_carga_laboral",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()

    return ReporteCargaLaboralResponse(
        periodo_desde=fecha_desde,
        periodo_hasta=fecha_hasta,
        items=items,
    )
