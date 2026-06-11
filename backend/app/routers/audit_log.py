from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit-log"])

# Lectura del log restringida a Auditor y Coordinación (CEPA-003 RN-5).
_solo_auditoria = require_role("Auditor", "Coordinacion")


@router.get("", response_model=list[AuditLogRead], dependencies=[Depends(_solo_auditoria)])
def listar_audit_log(
    db: Session = Depends(get_db),
    actor: str | None = Query(default=None),
    entity: str | None = Query(default=None, description="Módulo/entidad afectada"),
    action: str | None = Query(default=None),
    desde: datetime | None = Query(default=None, description="created_at >= desde (UTC)"),
    hasta: datetime | None = Query(default=None, description="created_at <= hasta (UTC)"),
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if actor is not None:
        stmt = stmt.where(AuditLog.actor == actor)
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if desde is not None:
        stmt = stmt.where(AuditLog.created_at >= desde)
    if hasta is not None:
        stmt = stmt.where(AuditLog.created_at <= hasta)
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return list(db.scalars(stmt))
