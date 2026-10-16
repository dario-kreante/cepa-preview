"""CEPA-093 — Reporte de carga laboral por profesional.

RN-4: el profesional es un dato de referencia en el registro (no un usuario del sistema — D1).
La carga se agrupa por cita.profesional_nombre (quien atendió) y cita.especialidad,
sobre casos/atenciones del período de citas SALUTEM.

DD-4 (EPIC-09 rework): el período fecha_desde/hasta se aplica sobre Cita.fecha (tabla
de hechos), NO sobre Ingreso.fecha_ingreso. Total_casos = ingresos distintos con al menos
una cita en el período; total_atenciones = citas realizadas en el período.
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
from app.models.profesional import SIN_PROFESIONAL_SALUTEM
from app.schemas.reportes import CargaProfesionalItem, ReporteCargaLaboralResponse
from app.services.reportes_filtros import (
    FiltrosDashboard,
    aplicar_filtros_ingreso,
    condicion_citas_reportables,
)

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
    """CA-1..CA-3: carga por profesional en el período, con filtros opcionales.

    DD-4: el período se aplica sobre Cita.fecha (no sobre fecha_ingreso del ingreso).
    Total_casos = ingresos distintos con al menos una cita en el período.
    """

    filtros = FiltrosDashboard(
        especialidad=especialidad,
        tipo_atencion=tipo_atencion,
        programa=programa,
    )

    # Decisión 11: la carga se atribuye a quien atendió (cita.profesional_nombre), no a
    # ingreso.profesional_id. Las citas sin nombre se agrupan como "Sin profesional informado".
    # nullif cubre el nombre en blanco (en Oracle '' ya es NULL), así se agrupa con los nulos.
    # La expresión lleva un parámetro ligado: repetida en SELECT y GROUP BY, Oracle la ve como
    # dos expresiones distintas (ORA-00979). Se calcula una vez en una subconsulta y se agrupa
    # por su columna.
    nombre_expr = func.coalesce(
        func.nullif(func.trim(Cita.profesional_nombre), ""), SIN_PROFESIONAL_SALUTEM
    )
    base = (
        select(
            nombre_expr.label("nombre"),
            Cita.profesional_id.label("profesional_id"),
            Cita.especialidad.label("especialidad"),
            Cita.id.label("cita_id"),
            Cita.estado.label("estado"),
            Cita.ingreso_id.label("ingreso_id"),
        )
        .where(condicion_citas_reportables())
        .where(Cita.fecha >= fecha_desde)
        .where(Cita.fecha <= fecha_hasta)
        .subquery("c")
    )

    # Total de casos (ingresos distintos) por profesional — citas en el período.
    # max(profesional_id): con homónimos elige uno cualquiera; es solo informativo.
    stmt_casos = (
        select(
            base.c.nombre,
            func.max(base.c.profesional_id).label("profesional_id"),
            base.c.especialidad,
            func.count(Ingreso.id.distinct()).label("total_casos"),
        )
        .select_from(base)
        .join(Ingreso, base.c.ingreso_id == Ingreso.id)
        .group_by(base.c.nombre, base.c.especialidad)
    )
    stmt_casos = aplicar_filtros_ingreso(stmt_casos, Ingreso, filtros)
    rows = db.execute(stmt_casos).all()

    # Total de atenciones realizadas por profesional y especialidad en el período
    stmt_atenciones = (
        select(
            base.c.nombre,
            base.c.especialidad,
            func.count(base.c.cita_id).label("total_atenciones"),
        )
        .select_from(base)
        .join(Ingreso, base.c.ingreso_id == Ingreso.id)
        .where(base.c.estado == "realizada")
        .group_by(base.c.nombre, base.c.especialidad)
    )
    stmt_atenciones = aplicar_filtros_ingreso(stmt_atenciones, Ingreso, filtros)
    atenciones_map: dict[tuple[str | None, str | None], int] = {
        (r.nombre, r.especialidad): r.total_atenciones
        for r in db.execute(stmt_atenciones).all()
    }

    items = [
        CargaProfesionalItem(
            profesional_id=r.profesional_id,
            nombre_profesional=r.nombre,
            especialidad=r.especialidad,
            total_casos=r.total_casos,
            total_atenciones=atenciones_map.get((r.nombre, r.especialidad), 0),
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
