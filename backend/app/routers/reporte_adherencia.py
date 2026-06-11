"""CEPA-095 — Métricas de adherencia y avance de tratamiento (P1).

Endpoint por folio/ingreso. El cómputo delegado a app.services.adherencia (funciones puras).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.plan_tratamiento import PlanTratamiento
from app.schemas.reportes import AdherenciaPaciente
from app.services.adherencia import calcular_pct_adherencia, calcular_pct_avance

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/adherencia/{folio_id}", response_model=AdherenciaPaciente)
def get_adherencia_folio(
    folio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> AdherenciaPaciente:
    """CA-1..CA-2: % adherencia y % avance del tratamiento por folio (D5)."""

    # Verificar que el folio existe
    ingreso = db.get(Ingreso, folio_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folio no encontrado")

    # Citas agendadas: todas las citas del folio (en cualquier estado)
    citas_agendadas = db.execute(
        select(func.count()).select_from(Cita).where(Cita.ingreso_id == folio_id)
    ).scalar_one()

    citas_realizadas = db.execute(
        select(func.count())
        .select_from(Cita)
        .where(Cita.ingreso_id == folio_id)
        .where(Cita.estado == "realizada")
    ).scalar_one()

    # Plan de tratamiento (puede no existir)
    plan = db.scalars(
        select(PlanTratamiento).where(PlanTratamiento.ingreso_id == folio_id)
    ).first()

    sesiones_plan = plan.sesiones_plan if plan else None
    aumentos_isl = plan.aumentos_isl if plan else 0

    pct_adherencia = calcular_pct_adherencia(citas_realizadas, citas_agendadas)
    pct_avance = calcular_pct_avance(citas_realizadas, sesiones_plan, aumentos_isl)

    return AdherenciaPaciente(
        folio_id=folio_id,
        citas_agendadas=citas_agendadas,
        citas_realizadas=citas_realizadas,
        pct_adherencia=pct_adherencia,
        sesiones_realizadas=citas_realizadas,
        sesiones_plan=sesiones_plan,
        aumentos_isl=aumentos_isl,
        pct_avance=pct_avance,
    )
