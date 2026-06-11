"""CEPA-094 — Reporte de licencias médicas acumuladas.

Deviación D5: LicenciaMedica usa `cantidad_dias` (no `dias_reposo`) y
`origen: str` ("sistema"/"extra_sistema") en lugar de `origen_externo: bool`.
Las licencias "extra_sistema" equivalen a las "externas" del plan.
RN-4: las LM anuladas (anulada=True) se excluyen del cómputo.

DD-4 (EPIC-09 rework): el período fecha_desde/hasta se aplica sobre
LicenciaMedica.fecha_emision (tabla de hechos), no sobre ingreso.fecha_ingreso.
aplicar_filtros_ingreso ya no aplica el rango de fechas (se eliminó ese comportamiento).

DD-6 (EPIC-09 rework): se eliminó el `base_stmt` duplicado; se consolida en
GROUP BY con origen para reducir el número de queries.
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
from app.models.paciente import Paciente
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
    DD-4: período se aplica sobre LicenciaMedica.fecha_emision.
    DD-6: consolidado — un GROUP BY por (ingreso_id, origen) en lugar de tres queries separadas.
    """

    filtros = FiltrosDashboard(
        region=region,
        comuna=comuna,
        programa=programa,
    )

    # Subquery: IDs de ingresos que pasan los filtros de dimensión (Paciente join para region/comuna)
    stmt_ingresos = (
        select(Ingreso.id)
        .select_from(Ingreso)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
    )
    stmt_ingresos = aplicar_filtros_ingreso(
        stmt_ingresos, Ingreso, filtros, modelo_paciente=Paciente
    )
    ingreso_ids = [r.id for r in db.execute(stmt_ingresos).all()]

    if not ingreso_ids:
        return ReporteLicenciasResponse(
            periodo_desde=fecha_desde,
            periodo_hasta=fecha_hasta,
            items=[],
        )

    # DD-6: un solo GROUP BY (ingreso_id, origen) — reemplaza las 3 queries separadas
    base_where = [
        LicenciaMedica.ingreso_id.in_(ingreso_ids),
        LicenciaMedica.fecha_emision >= fecha_desde,
        LicenciaMedica.fecha_emision <= fecha_hasta,
        LicenciaMedica.anulada.is_(False),
    ]
    if tipo_licencia is not None:
        base_where.append(LicenciaMedica.tipo_lm == tipo_licencia)
    if tipo_reposo is not None:
        base_where.append(LicenciaMedica.tipo_reposo == tipo_reposo)

    stmt_agrupado = (
        select(
            LicenciaMedica.ingreso_id,
            LicenciaMedica.origen,
            func.count(LicenciaMedica.id).label("n"),
            func.sum(LicenciaMedica.cantidad_dias).label("dias"),
        )
        .where(*base_where)
        .group_by(LicenciaMedica.ingreso_id, LicenciaMedica.origen)
    )
    rows_agrupados = db.execute(stmt_agrupado).all()

    # Acumular por ingreso_id
    totales_dias: dict[int, int] = {}
    internas_cnt: dict[int, int] = {}
    externas_cnt: dict[int, int] = {}

    for r in rows_agrupados:
        folio_id = r.ingreso_id
        totales_dias[folio_id] = totales_dias.get(folio_id, 0) + (r.dias or 0)
        if r.origen == "sistema":
            internas_cnt[folio_id] = internas_cnt.get(folio_id, 0) + r.n
        elif r.origen == "extra_sistema":
            externas_cnt[folio_id] = externas_cnt.get(folio_id, 0) + r.n

    folio_ids_con_licencias = set(totales_dias.keys())

    items = [
        LicenciaAcumuladaItem(
            folio_id=folio_id,
            rut_paciente=None,
            total_dias_acumulados=totales_dias.get(folio_id, 0),
            licencias_internas=internas_cnt.get(folio_id, 0),
            licencias_externas=externas_cnt.get(folio_id, 0),
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
