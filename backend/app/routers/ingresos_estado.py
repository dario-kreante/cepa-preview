"""Endpoint PATCH /api/v1/ingresos/{id}/estado — CEPA-121 CA-2.

Expone la actualización de estado de un ingreso con trazabilidad.
Solo expone consulta (GET) y actualización de estado (PATCH); complementa
el router de ingresos de EPIC-01 sin duplicar rutas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.enums import EstadoCaso, MotivoCierre, TipoAlta
from app.models.ingreso import Ingreso
from app.schemas.ingreso import HistorialCierreRead, IngresoRead
from app.services.cierre import cambiar_estado, historial_cierres

router = APIRouter(prefix="/api/v1/ingresos", tags=["ingresos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


class EstadoUpdate(BaseModel):
    estado: EstadoCaso
    motivo_cierre: MotivoCierre | None = None
    tipo_alta: TipoAlta | None = None
    observaciones: str | None = None
    # Solo al reabrir un caso cerrado (QA-007): queda en el historial de cierres.
    motivo_reapertura: str | None = Field(default=None, max_length=300)

    @field_validator("motivo_reapertura")
    @classmethod
    def _blanco_es_none(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None


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


@router.get(
    "/{ingreso_id}/cierres",
    response_model=list[HistorialCierreRead],
    dependencies=[Depends(_reader)],
)
def listar_cierres(ingreso_id: int, db: Session = Depends(get_db)) -> list:
    """Historial de cierres y reaperturas del caso, el más reciente primero (QA-007)."""
    return historial_cierres(db, ingreso_id)


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
    """Actualiza el estado del ingreso con trazabilidad (CA-2, RN-4 CEPA-121).

    Cerrar exige ``motivo_cierre`` (QA-011); reabrir un caso cerrado, solo Coordinación.
    """
    ingreso = cambiar_estado(
        db,
        ingreso_id,
        payload.estado,
        motivo_cierre=payload.motivo_cierre,
        actor=current_user.username,
        rol=current_user.role,
        motivo_reapertura=payload.motivo_reapertura,
    )
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
