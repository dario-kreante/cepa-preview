"""Configuración de alertas y calendario de festivos — COMP-2609-07.

``config_alerta``: una fila por tipo de alerta del motor (TipoAlerta) con la ventana
de aviso (días), si se cuenta en días hábiles y si el tipo está activo. La lee el job
en cada ejecución: un cambio de Coordinación aplica sin redespliegue (v5 D21, TC-072-07).

``festivo``: días no hábiles además de sábados y domingos, usados en el conteo de días
hábiles del motor y de las alertas de licencias.
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConfigAlerta(Base):
    __tablename__ = "config_alerta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    dias: Mapped[int] = mapped_column(Integer, nullable=False)
    habiles: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actualizado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class Festivo(Base):
    __tablename__ = "festivo"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
