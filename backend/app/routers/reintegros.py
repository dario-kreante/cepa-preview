"""Router del módulo de Seguimiento de Reintegro — /api/v1/reintegros (EPIC-04)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.reintegro import CasoReintegro, Reca
from app.schemas.reintegro import (
    CasoReintegroCreate,
    CasoReintegroRead,
    CasoReintegroUpdate,
    CierreReintegroUpdate,
    RecaCreate,
    RecaRead,
    RecaUpdate,
)
from app.services.reintegro import (
    _obtener_caso_o_404,
    actualizar_caso_reintegro,
    actualizar_reca,
    cerrar_caso_reintegro,
    crear_caso_reintegro,
    crear_reca,
)

router = APIRouter(prefix="/api/v1/reintegros", tags=["reintegros"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── CEPA-040: Caso de reintegro ────────────────────────────────────────────

@router.post(
    "",
    response_model=CasoReintegroRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_caso(
    payload: CasoReintegroCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = crear_caso_reintegro(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


@router.get(
    "",
    response_model=list[CasoReintegroRead],
    dependencies=[Depends(_reader)],
)
def listar_casos(
    ingreso_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CasoReintegroRead]:
    stmt = select(CasoReintegro)
    if ingreso_id is not None:
        stmt = stmt.where(CasoReintegro.ingreso_id == ingreso_id)
    return list(db.scalars(stmt.order_by(CasoReintegro.id)))


@router.get(
    "/{caso_id}",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_reader)],
)
def obtener_caso(
    caso_id: int,
    db: Session = Depends(get_db),
) -> CasoReintegroRead:
    return _obtener_caso_o_404(db, caso_id)


@router.patch(
    "/{caso_id}",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def actualizar_caso(
    caso_id: int,
    payload: CasoReintegroUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = _obtener_caso_o_404(db, caso_id)
    caso = actualizar_caso_reintegro(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


# ── CEPA-041: RECA y medidas correctivas ──────────────────────────────────

@router.post(
    "/{caso_id}/reca",
    response_model=RecaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_reca_endpoint(
    caso_id: int,
    payload: RecaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecaRead:
    reca = crear_reca(db, caso_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reca",
        entity_id=str(reca.id),
    )
    db.commit()
    db.refresh(reca)
    return reca


@router.get(
    "/{caso_id}/reca",
    response_model=RecaRead,
    dependencies=[Depends(_reader)],
)
def obtener_reca(
    caso_id: int,
    db: Session = Depends(get_db),
) -> RecaRead:
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.reca is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El caso {caso_id} no tiene RECA registrada.",
        )
    return caso.reca


@router.patch(
    "/{caso_id}/reca",
    response_model=RecaRead,
    dependencies=[Depends(_writer)],
)
def actualizar_reca_endpoint(
    caso_id: int,
    payload: RecaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecaRead:
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.reca is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El caso {caso_id} no tiene RECA registrada.",
        )
    reca = actualizar_reca(db, caso.reca, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="reca",
        entity_id=str(reca.id),
    )
    db.commit()
    db.refresh(reca)
    return reca


# ── CEPA-042: Cierre / reintegro ──────────────────────────────────────────

@router.patch(
    "/{caso_id}/cierre",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def registrar_cierre(
    caso_id: int,
    payload: CierreReintegroUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = _obtener_caso_o_404(db, caso_id)
    caso = cerrar_caso_reintegro(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso
