from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import EstadoCaso


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ingreso(Base):
    """Ingreso de un paciente al CEPA. Lleva el folio (único entre ingresos distintos).

    El campo `estado` evoluciona activo→cerrado/derivado (CEPA-014). `tipo_alta`,
    `fecha_alta`, `flag_revision` y `observaciones` se completan al cierre.
    """

    __tablename__ = "ingreso"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    paciente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("paciente.id"), nullable=False, index=True
    )
    folio: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    folio_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    numero_siniestro: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_diep_diat: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_derivacion: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo_ingreso: Mapped[str] = mapped_column(String(40), nullable=False)
    modelo_tratamiento: Mapped[str] = mapped_column(String(80), nullable=False)
    diagnostico: Mapped[str] = mapped_column(String(200), nullable=False)
    razon_social: Mapped[str | None] = mapped_column(String(160), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default=EstadoCaso.ACTIVO.value, nullable=False)
    tipo_alta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha_alta: Mapped[date | None] = mapped_column(Date, nullable=True)
    flag_revision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento_iniciado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    paciente: Mapped["Paciente"] = relationship(back_populates="ingresos")  # noqa: F821
