from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.consentimiento import ConsentimientoAlerta
from app.services.consentimiento import consentimientos_pendientes

router = APIRouter(prefix="/api/v1/consentimientos", tags=["consentimientos"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get("/alertas", response_model=list[ConsentimientoAlerta], dependencies=[Depends(_reader)])
def alertas(db: Session = Depends(get_db)) -> list[ConsentimientoAlerta]:
    return consentimientos_pendientes(db)
