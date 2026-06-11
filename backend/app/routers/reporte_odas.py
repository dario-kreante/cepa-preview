"""CEPA-097 — Reporte de ODAS vencidas (D3).

RN-1: vencida = fecha_vencimiento < fecha actual (estricto menor, NO <=).
RN-2: las ODAS son manuales y tienen fecha_vencimiento (D3).
Deviación: modelo Oda (no ODA); fecha_registro nullable añadida EPIC-09 migración 09000.

DD-6 (EPIC-09 rework): se popula ODAVencidaItem.programa/region/comuna con datos
del Ingreso y Paciente (join ya disponible). También se incluye folio/nombre paciente
por CA-1.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.schemas.reportes import ODAVencidaItem, ReporteODASVencidasResponse

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/odas-vencidas", response_model=ReporteODASVencidasResponse)
def get_odas_vencidas(
    programa: str | None = Query(None),
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteODASVencidasResponse:
    """CA-1..CA-3: lista de ODAS cuya fecha_vencimiento < hoy (estricto).

    TC-097-02: ODA que vence exactamente hoy NO aparece (condición estricta < hoy).
    DD-6: programa/region/comuna se leen de Ingreso y Paciente respectivamente.
    """

    hoy = datetime.now(timezone.utc).date()

    stmt = (
        select(Oda, Ingreso, Paciente)
        .join(Ingreso, Oda.ingreso_id == Ingreso.id)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .where(Oda.fecha_vencimiento < hoy)
    )
    if programa is not None:
        stmt = stmt.where(Ingreso.programa == programa)
    if region is not None:
        stmt = stmt.where(Paciente.region == region)
    if comuna is not None:
        stmt = stmt.where(Paciente.comuna == comuna)

    rows = db.execute(stmt.order_by(Oda.fecha_vencimiento.asc())).all()

    items = [
        ODAVencidaItem(
            id=o.id,
            folio_id=o.ingreso_id,
            fecha_registro=o.fecha_registro,
            fecha_vencimiento=o.fecha_vencimiento,
            programa=ing.programa,
            region=pac.region,
            comuna=pac.comuna,
        )
        for o, ing, pac in rows
    ]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_odas_vencidas",
        entity_id=str(hoy),
    )
    db.commit()

    return ReporteODASVencidasResponse(
        fecha_consulta=hoy,
        total=len(items),
        items=items,
    )
