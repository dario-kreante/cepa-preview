from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogRead

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit-log"])


@router.post("", response_model=AuditLogRead, status_code=status.HTTP_201_CREATED)
def create_audit_log(payload: AuditLogCreate, db: Session = Depends(get_db)) -> AuditLog:
    entry = AuditLog(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[AuditLogRead])
def list_audit_log(db: Session = Depends(get_db)) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)))
