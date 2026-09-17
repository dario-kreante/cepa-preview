"""Estado del sync SALUTEM (fase 1, solo lectura)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.salutem_sync import EstadoSyncRead
from app.services.salutem_sync.estado import estado_sync

router = APIRouter(prefix="/api/v1/salutem/sync", tags=["salutem-sync"])


@router.get(
    "/estado",
    response_model=EstadoSyncRead,
    dependencies=[Depends(require_role("Coordinacion"))],
)
def estado(db: Session = Depends(get_db)) -> EstadoSyncRead:
    return estado_sync(db, datetime.now(timezone.utc))
