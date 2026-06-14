"""Modelo ControlMedico — tabla del módulo de Controles Médicos (EPIC-06).

Columnas base:          CEPA-060 (Task 3)
Próximo control:        CEPA-061 (Task 5, migración 0061)
Licencia / RECA:        CEPA-062 (Task 7, migración 0062)
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


class ControlMedico(Base):
    """Control médico periódico de un paciente del CEPA.

    Vinculado al ingreso (folio). La semana del control se calcula automáticamente
    en la capa de servicio y se persiste como campo de solo lectura (RN-3 CEPA-060).
    """

    __tablename__ = "control_medico"

    # ── Clave primaria ────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)

    # ── Vínculo al ingreso/folio (RN-1 CEPA-060) ─────────────────────────────
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )

    # ── Campos base del control (CEPA-060) ───────────────────────────────────
    fecha_control: Mapped[date] = mapped_column(Date, nullable=False)
    semana_control: Mapped[int] = mapped_column(Integer, nullable=False)
    medico_tratante: Mapped[str] = mapped_column(String(160), nullable=False)
    region_derivacion: Mapped[str] = mapped_column(String(80), nullable=False)

    # ── Próximo control (CEPA-061, migración 0061) ───────────────────────────
    proximo_control: Mapped[date | None] = mapped_column(Date, nullable=True)
    proximo_agendado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Licencia médica asociada (CEPA-062, migración 0062) ──────────────────
    tiene_licencia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # campos obligatorios solo si tiene_licencia=True
    resumen_termino_lm: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_dias_lm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_licencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tipo_reposo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gaf: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── RECA y observaciones (CEPA-062, siempre editables) ───────────────────
    estado_reca: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Metadatos ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # ── Relación ──────────────────────────────────────────────────────────────
    ingreso: Mapped["Ingreso"] = relationship(  # noqa: F821
        back_populates="controles_medicos"
    )
