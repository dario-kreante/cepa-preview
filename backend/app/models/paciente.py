from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, Integer, String
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
    # Nulos solo en borradores de SALUTEM pendientes de folio (varios NULL no chocan por unique).
    rut: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    sexo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    comuna: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Persona de SALUTEM con la que se cruza este paciente cuando SALUTEM no tiene su
    # RUT (p.ej. sus pacientes de prueba, "SIN IDENTIFICACION"). Si es nulo, se cruza por RUT.
    salutem_persona_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    estado_registro: Mapped[str] = mapped_column(
        String(20), default="completo", server_default="completo", nullable=False, index=True
    )
    origen: Mapped[str] = mapped_column(
        String(10), default="SIGE", server_default="SIGE", nullable=False
    )
    motivo_descarte: Mapped[str | None] = mapped_column(String(300), nullable=True)
    descartado_por: Mapped[str | None] = mapped_column(String(80), nullable=True)
    descartado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingresos: Mapped[list["Ingreso"]] = relationship(  # noqa: F821
        back_populates="paciente", cascade="all, delete-orphan"
    )
