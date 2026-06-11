from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.ingreso import IngresoCreate, IngresoRead
from app.services.ingreso import crear_ingreso

router = APIRouter(prefix="/api/v1/ingresos", tags=["ingresos"])

_writer = require_role("Administrativo", "Coordinacion")


@router.post(
    "",
    response_model=IngresoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: IngresoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = crear_ingreso(db, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso
