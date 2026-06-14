from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Traza append-only e inmutable de operaciones (CEPA-003).

    Registra quién (actor/rol), qué (action/entity/entity_id), valores y cuándo (created_at).
    La inmutabilidad se garantiza en la aplicación (sin endpoints de update/delete) y en la BD
    (trigger que rechaza UPDATE/DELETE; ver migración 0003).
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    rol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    entity: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    valor_anterior: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
