"""Modelo Cita — EPIC-09 (reportes operativos, adherencia).

Tabla `cita`: registro de citas agendadas para un paciente/ingreso.
Estados válidos: realizada, inasistencia, anulada, agendada.

Nota: no es CitaPropuesta del módulo de agendamiento (EPIC-08). Esa tabla
gestiona propuestas de agenda; esta tabla registra citas confirmadas para
efectos de reporting (CEPA-090..095).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Cita(Base):
    """Cita de un paciente asociada a un ingreso.

    estados: realizada | inasistencia | anulada | agendada
    """

    __tablename__ = "cita"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship()  # noqa: F821
