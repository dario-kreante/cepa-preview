"""Modelo Cita — EPIC-09 (reportes operativos, adherencia).

Tabla `cita`: registro de citas agendadas para un paciente/ingreso.
Estados válidos: realizada, inasistencia, anulada, agendada.

Nota: no es CitaPropuesta del módulo de agendamiento (EPIC-08). Esa tabla
gestiona propuestas de agenda; esta tabla registra citas confirmadas para
efectos de reporting (CEPA-090..095).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Cita(Base):
    """Cita de un paciente asociada a un ingreso.

    estados: realizada | inasistencia | anulada | agendada
    """

    __tablename__ = "cita"
    __table_args__ = (Index("uq_cita_salutem_cita_id", "salutem_cita_id", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # Fase 2 (cita desde SALUTEM): espejo de la cita de SALUTEM cuando el origen es SALUTEM.
    # Único cuando no es nulo; las citas creadas en el SIGE quedan con NULL.
    salutem_cita_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    origen: Mapped[str] = mapped_column(
        String(10), nullable=False, default="SIGE", server_default="SIGE"
    )
    especialidad: Mapped[str | None] = mapped_column(String(80), nullable=True)
    profesional_nombre: Mapped[str | None] = mapped_column(String(160), nullable=True)
    profesional_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profesional.id"), nullable=True
    )

    ingreso: Mapped["Ingreso"] = relationship()  # noqa: F821
