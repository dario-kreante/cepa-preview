"""CEPA-092 — Reporte de cumplimiento por convenio (OI2: generación < 5 min).

Tipos de convenio válidos (D4): DIEP, DIAT, PAPT a flujo AT, Reingreso FUMP,
Reingreso SUSESO, Convenio U.Clínica, Proyecto, Particular, PAPT.
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
from app.schemas.reportes import CumplimientoConvenioItem, ReporteCumplimientoResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/convenio", response_model=ReporteCumplimientoResponse)
def get_reporte_convenio(
    tipo_convenio: Annotated[str, Query(description="Tipo de convenio (D4)")],
    fecha_desde: Annotated[date, Query(description="Inicio del período")],
    fecha_hasta: Annotated[date, Query(description="Fin del período")],
    profesional_id: int | None = Query(None),
    tipo_atencion: str | None = Query(None),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteCumplimientoResponse:
    """CA-1..CA-3: cumplimiento de convenio por período, con filtros opcionales."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo_convenio=tipo_convenio,
        profesional_id=profesional_id,
        tipo_atencion=tipo_atencion,
        programa=programa,
    )

    def _count_estado_conv(estado: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Cita)
            .join(Ingreso, Cita.ingreso_id == Ingreso.id)
            .where(Ingreso.tipo_convenio == tipo_convenio)
            .where(Cita.estado == estado)
            .where(Cita.fecha >= fecha_desde)
            .where(Cita.fecha <= fecha_hasta)
        )
        stmt = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
        return db.execute(stmt).scalar_one()

    total_atenciones = _count_estado_conv("realizada")
    total_inasistencias = _count_estado_conv("inasistencia")
    total_anulaciones = _count_estado_conv("anulada")

    periodo = f"{fecha_desde}/{fecha_hasta}"

    item = CumplimientoConvenioItem(
        tipo_convenio=tipo_convenio,
        periodo=periodo,
        total_atenciones=total_atenciones,
        total_inasistencias=total_inasistencias,
        total_anulaciones=total_anulaciones,
    )

    # RN-7: trazar generación
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_convenio",
        entity_id=f"{tipo_convenio}/{periodo}",
    )
    db.commit()

    return ReporteCumplimientoResponse(
        convenio=tipo_convenio,
        periodo=periodo,
        items=[item],
    )
