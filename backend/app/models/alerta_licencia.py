"""Alerta in-app de vencimiento de licencia médica — CEPA-072.

Append-only. La idempotencia se logra verificando que no exista una alerta
activa (activa=True) para la misma (licencia_id, fecha_generacion).
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlertaLicencia(Base):
    __tablename__ = "alerta_licencia"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    licencia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("licencia_medica.id"), nullable=False, index=True
    )
    ingreso_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    fecha_termino_lm: Mapped[date] = mapped_column(Date, nullable=False)
    dias_habiles_restantes: Mapped[int] = mapped_column(Integer, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
