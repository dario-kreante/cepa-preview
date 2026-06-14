"""PATCH /api/v1/citas/{id}/estado — DD-1 (EPIC-09 rework).

Transiciona una Cita de la tabla de hechos de reportes:
  agendada → realizada | inasistencia | anulada

RBAC: roles escritores (Administrativo, Coordinacion).
Auditoría + commit en cada transición.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.models.cita import Cita

router = APIRouter(prefix="/api/v1/citas", tags=["citas"])

_ESTADOS_VALIDOS = {"agendada", "realizada", "inasistencia", "anulada"}
_TRANSICIONES_PERMITIDAS: dict[str, set[str]] = {
    "agendada": {"realizada", "inasistencia", "anulada"},
    # ya confirmadas: solo anulación
    "realizada": {"anulada"},
    "inasistencia": {"anulada"},
}

_escritor = require_role("Coordinacion", "Administrativo")


class CitaEstadoUpdate(BaseModel):
    estado: str


class CitaRead(BaseModel):
    id: int
    ingreso_id: int
    estado: str
    fecha: date

    model_config = {"from_attributes": True}


@router.patch("/{cita_id}/estado", response_model=CitaRead)
def actualizar_estado_cita(
    cita_id: int,
    payload: CitaEstadoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_escritor),
) -> Cita:
    """Transiciona el estado de una Cita de reportes (DD-1).

    Transiciones válidas:
      agendada   → realizada | inasistencia | anulada
      realizada  → anulada
      inasistencia → anulada
    """
    nuevo = payload.estado
    if nuevo not in _ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Estado inválido: {nuevo}. Válidos: {sorted(_ESTADOS_VALIDOS)}",
        )

    cita = db.get(Cita, cita_id)
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    permitidos = _TRANSICIONES_PERMITIDAS.get(cita.estado, set())
    if nuevo not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede transicionar de '{cita.estado}' a '{nuevo}'",
        )

    anterior = cita.estado
    cita.estado = nuevo

    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="cita",
        entity_id=str(cita_id),
        valor_anterior=anterior,
        valor_nuevo=nuevo,
    )
    db.commit()
    db.refresh(cita)
    return cita
