"""Endpoint PATCH /api/v1/ingresos/{id}/estado — CEPA-121 CA-2.

Expone la actualización de estado de un ingreso con trazabilidad.
Solo expone consulta (GET) y actualización de estado (PATCH); complementa
el router de ingresos de EPIC-01 sin duplicar rutas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.enums import EstadoCaso, TipoAlta
from app.models.ingreso import Ingreso
from app.schemas.ingreso import IngresoRead

router = APIRouter(prefix="/api/v1/ingresos", tags=["ingresos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


class EstadoUpdate(BaseModel):
    estado: EstadoCaso
    tipo_alta: TipoAlta | None = None
    observaciones: str | None = None


@router.get(
    "/{ingreso_id}",
    response_model=IngresoRead,
    dependencies=[Depends(_reader)],
)
def obtener_ingreso(ingreso_id: int, db: Session = Depends(get_db)) -> Ingreso:
    """Consulta el estado actual de un ingreso (CA-2)."""
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado"
        )
    return ingreso


@router.patch(
    "/{ingreso_id}/estado",
    response_model=IngresoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_estado(
    ingreso_id: int,
    payload: EstadoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Ingreso:
    """Actualiza el estado del ingreso con trazabilidad (CA-2, RN-4 CEPA-121)."""
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado"
        )
    ingreso.estado = payload.estado.value
    if payload.tipo_alta is not None:
        ingreso.tipo_alta = payload.tipo_alta.value
    if payload.observaciones is not None:
        ingreso.observaciones = payload.observaciones
    db.flush()
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="ingreso",
        entity_id=str(ingreso_id),
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso
