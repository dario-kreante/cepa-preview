"""CEPA-094 — Reporte de licencias médicas acumuladas.

Deviación D5: LicenciaMedica usa `cantidad_dias` (no `dias_reposo`) y
`origen: str` ("sistema"/"extra_sistema") en lugar de `origen_externo: bool`.
Las licencias "extra_sistema" equivalen a las "externas" del plan.
RN-4: las LM anuladas (anulada=True) se excluyen del cómputo.
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
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.schemas.reportes import LicenciaAcumuladaItem, ReporteLicenciasResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/licencias", response_model=ReporteLicenciasResponse)
def get_reporte_licencias(
    fecha_desde: Annotated[date, Query(description="Inicio del período de emisión")],
    fecha_hasta: Annotated[date, Query(description="Fin del período de emisión")],
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    tipo_licencia: str | None = Query(None),
    tipo_reposo: str | None = Query(None),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteLicenciasResponse:
    """CA-1..CA-3: total de días acumulados por folio, distinguiendo licencias externas (D7).

    Deviación D5: 'externas' = origen == 'extra_sistema'; 'internas' = origen == 'sistema'.
    """

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        region=region,
        comuna=comuna,
        programa=programa,
    )

    # Subquery: IDs de ingresos que pasan los filtros de dimensión
    stmt_ingresos = select(Ingreso.id).select_from(Ingreso)
    stmt_ingresos = aplicar_filtros_ingreso(stmt_ingresos, Ingreso, filtros)
    ingreso_ids = [r.id for r in db.execute(stmt_ingresos).all()]

    if not ingreso_ids:
        return ReporteLicenciasResponse(
            periodo_desde=fecha_desde,
            periodo_hasta=fecha_hasta,
            items=[],
        )

    # Base: solo vigentes (no anuladas), en el período de emisión
    base_stmt = (
        select(LicenciaMedica.ingreso_id)
        .where(LicenciaMedica.ingreso_id.in_(ingreso_ids))
        .where(LicenciaMedica.fecha_emision >= fecha_desde)
        .where(LicenciaMedica.fecha_emision <= fecha_hasta)
        .where(LicenciaMedica.anulada.is_(False))
    )
    if tipo_licencia is not None:
        base_stmt = base_stmt.where(LicenciaMedica.tipo_lm == tipo_licencia)
    if tipo_reposo is not None:
        base_stmt = base_stmt.where(LicenciaMedica.tipo_reposo == tipo_reposo)

    # Total días por folio
    stmt_total = (
        select(
            LicenciaMedica.ingreso_id,
            func.sum(LicenciaMedica.cantidad_dias).label("total_dias"),
        )
        .where(LicenciaMedica.ingreso_id.in_(ingreso_ids))
        .where(LicenciaMedica.fecha_emision >= fecha_desde)
        .where(LicenciaMedica.fecha_emision <= fecha_hasta)
        .where(LicenciaMedica.anulada.is_(False))
        .group_by(LicenciaMedica.ingreso_id)
    )
    if tipo_licencia is not None:
        stmt_total = stmt_total.where(LicenciaMedica.tipo_lm == tipo_licencia)
    if tipo_reposo is not None:
        stmt_total = stmt_total.where(LicenciaMedica.tipo_reposo == tipo_reposo)

    rows_total = db.execute(stmt_total).all()
    total_map = {r.ingreso_id: r.total_dias or 0 for r in rows_total}

    # Conteo internas (origen='sistema') por folio
    stmt_internas = (
        select(
            LicenciaMedica.ingreso_id,
            func.count(LicenciaMedica.id).label("n"),
        )
        .where(LicenciaMedica.ingreso_id.in_(ingreso_ids))
        .where(LicenciaMedica.fecha_emision >= fecha_desde)
        .where(LicenciaMedica.fecha_emision <= fecha_hasta)
        .where(LicenciaMedica.anulada.is_(False))
        .where(LicenciaMedica.origen == "sistema")
        .group_by(LicenciaMedica.ingreso_id)
    )
    internas_map = {r.ingreso_id: r.n for r in db.execute(stmt_internas).all()}

    # Conteo externas (origen='extra_sistema') por folio
    stmt_externas = (
        select(
            LicenciaMedica.ingreso_id,
            func.count(LicenciaMedica.id).label("n"),
        )
        .where(LicenciaMedica.ingreso_id.in_(ingreso_ids))
        .where(LicenciaMedica.fecha_emision >= fecha_desde)
        .where(LicenciaMedica.fecha_emision <= fecha_hasta)
        .where(LicenciaMedica.anulada.is_(False))
        .where(LicenciaMedica.origen == "extra_sistema")
        .group_by(LicenciaMedica.ingreso_id)
    )
    externas_map = {r.ingreso_id: r.n for r in db.execute(stmt_externas).all()}

    # Folios que tienen al menos una licencia en el período
    folio_ids_con_licencias = set(total_map.keys())

    items = [
        LicenciaAcumuladaItem(
            folio_id=folio_id,
            rut_paciente=None,
            total_dias_acumulados=total_map.get(folio_id, 0),
            licencias_internas=internas_map.get(folio_id, 0),
            licencias_externas=externas_map.get(folio_id, 0),
        )
        for folio_id in folio_ids_con_licencias
    ]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_licencias",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()

    return ReporteLicenciasResponse(
        periodo_desde=fecha_desde,
        periodo_hasta=fecha_hasta,
        items=items,
    )
