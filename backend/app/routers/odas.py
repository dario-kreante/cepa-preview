from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.oda import OdaAlerta, OdaCreate, OdaRead
from app.services.oda import listar_odas, odas_por_vencer, registrar_oda

router = APIRouter(prefix="/api/v1", tags=["odas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "/ingresos/{ingreso_id}/odas",
    response_model=OdaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_oda(
    ingreso_id: int,
    payload: OdaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OdaRead:
    oda = registrar_oda(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="oda", entity_id=str(oda.id)
    )
    db.commit()
    db.refresh(oda)
    return oda


@router.get(
    "/ingresos/{ingreso_id}/odas",
    response_model=list[OdaRead],
    dependencies=[Depends(_reader)],
)
def listar(ingreso_id: int, db: Session = Depends(get_db)) -> list[OdaRead]:
    return listar_odas(db, ingreso_id)


@router.get("/odas/alertas", response_model=list[OdaAlerta], dependencies=[Depends(_reader)])
def alertas(db: Session = Depends(get_db)) -> list[OdaAlerta]:
    return odas_por_vencer(db)
