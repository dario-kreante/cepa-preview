from datetime import datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Paciente(Base):
    """Paciente del CEPA. El RUT se guarda normalizado (forma canónica) y es único.

    Un paciente puede tener varios ingresos (reingresos / denuncias distintas).
    """

    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    sexo: Mapped[str] = mapped_column(String(10), nullable=False)
    edad: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    comuna: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingresos: Mapped[list["Ingreso"]] = relationship(  # noqa: F821
        back_populates="paciente", cascade="all, delete-orphan"
    )
