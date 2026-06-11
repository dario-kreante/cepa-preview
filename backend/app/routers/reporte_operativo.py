"""CEPA-091 — Reportes operativos descargables (citas, atenciones, inasistencias, anulaciones).

La descarga en Excel/PDF se delega a la capa frontend (el endpoint devuelve JSON;
el frontend serializa). La trazabilidad de generación (RN-5) se registra via record_audit.

D15: portable — no usa func.count().filter() (Postgres-only). Usa subcounts separados.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import ReporteOperativoItem, ReporteOperativoResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/operativo", response_model=ReporteOperativoResponse)
def get_reporte_operativo(
    fecha_desde: Annotated[date, Query(description="Inicio del período (obligatorio)")],
    fecha_hasta: Annotated[date, Query(description="Fin del período (obligatorio)")],
    programa: str | None = Query(None),
    profesional_id: int | None = Query(None),
    tipo_convenio: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteOperativoResponse:
    """CA-1..CA-3: cifras de citas/atenciones/inasistencias/anulaciones por período y filtros."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        programa=programa,
        profesional_id=profesional_id,
        tipo_convenio=tipo_convenio,
    )

    def _count_estado(estado: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Cita)
            .join(Ingreso, Cita.ingreso_id == Ingreso.id)
            .where(Cita.estado == estado)
            .where(Cita.fecha >= fecha_desde)
            .where(Cita.fecha <= fecha_hasta)
        )
        stmt = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
        return db.execute(stmt).scalar_one()

    realizadas = _count_estado("realizada")
    inasistencias = _count_estado("inasistencia")
    anuladas = _count_estado("anulada")
    agendadas = _count_estado("agendada")

    # Detalle diario agrupado por fecha (portable: sin FILTER aggregate)
    # Contamos total de citas en cada fecha/programa/profesional
    stmt_detalle = (
        select(
            Cita.fecha,
            Ingreso.programa,
            Ingreso.profesional_id,
            func.count(Cita.id).label("total_citas"),
        )
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.fecha >= fecha_desde)
        .where(Cita.fecha <= fecha_hasta)
        .group_by(Cita.fecha, Ingreso.programa, Ingreso.profesional_id)
        .order_by(Cita.fecha)
    )
    stmt_detalle = aplicar_filtros_ingreso(stmt_detalle, Ingreso, filtros)
    rows_detalle = db.execute(stmt_detalle).all()

    # Para el detalle por fila, calculamos los conteos de estado con subquery join
    # (D15: portable). Agrupamos por fecha+programa+profesional.
    stmt_por_estado = (
        select(
            Cita.fecha,
            Ingreso.programa,
            Ingreso.profesional_id,
            Cita.estado,
            func.count(Cita.id).label("n"),
        )
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.fecha >= fecha_desde)
        .where(Cita.fecha <= fecha_hasta)
        .group_by(Cita.fecha, Ingreso.programa, Ingreso.profesional_id, Cita.estado)
    )
    stmt_por_estado = aplicar_filtros_ingreso(stmt_por_estado, Ingreso, filtros)
    rows_estado = db.execute(stmt_por_estado).all()

    # Construir mapa: (fecha, programa, prof_id, estado) → count
    estado_map: dict[tuple, int] = {}
    for r in rows_estado:
        estado_map[(r.fecha, r.programa, r.profesional_id, r.estado)] = r.n

    items = [
        ReporteOperativoItem(
            fecha=r.fecha,
            programa=r.programa,
            profesional_id=r.profesional_id,
            total_citas=r.total_citas,
            realizadas=estado_map.get((r.fecha, r.programa, r.profesional_id, "realizada"), 0),
            inasistencias=estado_map.get((r.fecha, r.programa, r.profesional_id, "inasistencia"), 0),
            anuladas=estado_map.get((r.fecha, r.programa, r.profesional_id, "anulada"), 0),
        )
        for r in rows_detalle
    ]

    # RN-5: trazar generación en log de auditoría
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_operativo",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()

    return ReporteOperativoResponse(
        items=items,
        totales={
            "realizadas": realizadas,
            "inasistencias": inasistencias,
            "anuladas": anuladas,
            "agendadas": agendadas,
        },
    )
