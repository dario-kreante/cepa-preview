"""Modelo ConfigVentanaProceso — EPIC-09 CEPA-096.

Configuración de ventana de visualización por proceso.
Procesos válidos: licencias, farmacos, auditoria, reintegro, controles.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConfigVentanaProceso(Base):
    """Configuración de ventana de visualización por proceso (CEPA-096, §7.10).

    Procesos válidos: licencias, farmacos, auditoria, reintegro, controles.
    Tabla de configuración; no es tabla de dominio clínico.
    """

    __tablename__ = "config_ventana_proceso"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    proceso: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    columnas_visibles: Mapped[list] = mapped_column(JSON, nullable=False)
    orden_por_defecto: Mapped[str | None] = mapped_column(String(60), nullable=True)
    creado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
