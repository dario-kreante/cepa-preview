"""Modelo PlanTratamiento — EPIC-09 CEPA-095 (adherencia y avance).

Tabla `plan_tratamiento`: plan de sesiones para un ingreso. 1:1 con ingreso.
sesiones_plan: total de sesiones comprometidas en el plan.
aumentos_isl: número de sesiones adicionales aprobadas por ISL.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PlanTratamiento(Base):
    """Plan de tratamiento de un ingreso para cálculo de avance (CEPA-095)."""

    __tablename__ = "plan_tratamiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, unique=True
    )
    sesiones_plan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aumentos_isl: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship()  # noqa: F821
