from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import EstadoConsentimiento


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Consentimiento(Base):
    """Consentimiento informado del ingreso (CEPA-016, v4 D9). 1:1 con `ingreso`.

    `evidencia_ref` es una referencia opcional (URL de archivo o id en ficha clínica);
    el mecanismo de origen está por definir (nota abierta D9).
    """

    __tablename__ = "consentimiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), unique=True, nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(20), default=EstadoConsentimiento.PENDIENTE.value, nullable=False
    )
    evidencia_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_firma: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="consentimiento")  # noqa: F821
