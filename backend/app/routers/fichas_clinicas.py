"""Router de Fichas Clínicas — CEPA-121 CA-3 (bidireccional push/pull).

D12: el router de pull-salutem solo invoca métodos de lectura del cliente SALUTEM.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.ficha_clinica import FichaClinicaCreate, FichaClinicaRead, PullSalutemRequest
from app.services.ficha_clinica import crear_ficha, listar_fichas, pull_desde_salutem

router = APIRouter(prefix="/api/v1/fichas-clinicas", tags=["fichas-clinicas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "",
    response_model=FichaClinicaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def push_ficha_clinica(
    payload: FichaClinicaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> FichaClinicaRead:
    """Push: sistema externo envía datos clínicos al CEPA (CA-3)."""
    ficha = crear_ficha(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="ficha_clinica",
        entity_id=str(ficha.id),
    )
    db.commit()
    db.refresh(ficha)
    return ficha


@router.post(
    "/pull-salutem",
    response_model=FichaClinicaRead | None,
    dependencies=[Depends(_writer)],
)
def pull_desde_salutem_endpoint(
    payload: PullSalutemRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> FichaClinicaRead | None:
    """Pull desde SALUTEM (solo lectura D12): trae datos y los persiste en CEPA.

    Si SALUTEM no tiene datos para el folio, devuelve 200 con null.
    """
    ficha = pull_desde_salutem(db, payload.folio)
    if ficha is not None:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="ficha_clinica",
            entity_id=str(ficha.id),
        )
        db.commit()
        db.refresh(ficha)
    return ficha


@router.get(
    "/{folio}",
    response_model=list[FichaClinicaRead],
    dependencies=[Depends(_reader)],
)
def pull_fichas_clinicas(folio: str, db: Session = Depends(get_db)) -> list[FichaClinicaRead]:
    """Pull: entrega al sistema externo las fichas clínicas del CEPA para el folio (CA-3)."""
    return listar_fichas(db, folio)
