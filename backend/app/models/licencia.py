"""Modelo LicenciaMedica — EPIC-07 CEPA-070..073.

Columnas D8 (v4): cantidad_dias, inicio_reposo, fin_reposo, fecha_emision,
tipo_lm, indicacion_reposo, diagnostico, tipo_reposo (total/parcial).
Trazabilidad ISL (CEPA-073): envio_isl, fecha_envio_isl, eeag_gaf, observaciones.
Licencias extra-sistema (v4 D7): campo origen.
Anulación 77 BIS: campo anulada.
"""

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
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LicenciaMedica(Base):
    """Licencia médica vinculada a un ingreso/folio.

    Una LM anulada (campo anulada=True) queda en historial pero se excluye
    del acumulado vigente (RN-4 CEPA-071, RN-5 CEPA-073).
    """

    __tablename__ = "licencia_medica"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    folio_lm: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    tipo_lm: Mapped[str] = mapped_column(String(5), nullable=False)
    tipo_reposo: Mapped[str] = mapped_column(String(15), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_termino: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    inicio_reposo: Mapped[date] = mapped_column(Date, nullable=False)
    fin_reposo: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    indicacion_reposo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    diagnostico: Mapped[str] = mapped_column(String(200), nullable=False)
    origen: Mapped[str] = mapped_column(String(20), nullable=False, default="sistema")
    # Trazabilidad ISL (CEPA-073)
    envio_isl: Mapped[str] = mapped_column(String(15), nullable=False, default="pendiente")
    fecha_envio_isl: Mapped[date | None] = mapped_column(Date, nullable=True)
    eeag_gaf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Control
    anulada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="licencias")  # noqa: F821
