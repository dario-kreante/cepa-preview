from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Seguimiento(Base):
    """Hitos del proceso clínico de un ingreso (§7.1.2). 1:1 con `ingreso`."""

    __tablename__ = "seguimiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), unique=True, nullable=False
    )
    fecha_acogida: Mapped[date | None] = mapped_column(Date, nullable=True)
    programa: Mapped[str | None] = mapped_column(String(80), nullable=True)
    eval_medica_estado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    eval_medica_medico: Mapped[str | None] = mapped_column(String(120), nullable=True)
    eval_medica_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    eval_psico_estado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    eval_psico_psicologo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    eval_psico_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    obstaculizacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    plazo_informe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_envio_informe: Mapped[date | None] = mapped_column(Date, nullable=True)
    reca_ep_ec: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="seguimiento")  # noqa: F821
