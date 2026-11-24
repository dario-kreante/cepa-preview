"""Historial de cierres y reaperturas del caso (QA-007, 23-11-2026).

Cada cierre del ingreso deja una fila con su motivo, fecha y quién cerró. Al reabrir se
completan ``reabierto_por`` / ``reabierto_en`` (y el motivo de reapertura, opcional) en la
última fila abierta. Los campos de cierre del ``Ingreso`` reflejan solo el cierre vigente;
esta tabla los conserva todos.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HistorialCierre(Base):
    __tablename__ = "ingreso_cierre"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    motivo_cierre: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_cierre: Mapped[date] = mapped_column(Date, nullable=False)
    cerrado_por: Mapped[str] = mapped_column(String(100), nullable=False)
    cerrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reabierto_por: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reabierto_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_reapertura: Mapped[str | None] = mapped_column(String(300), nullable=True)
