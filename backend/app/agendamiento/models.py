"""Modelos SQLAlchemy del módulo de agendamiento.

Tres tablas portables (D15): disponibilidad_prof, propuesta_agenda, cita_propuesta.
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DisponibilidadProf(Base):
    """Disponibilidad semanal recurrente de un profesional (RN-3, RN-4).

    dia_semana: ISO weekday 1–5 (lunes–viernes).
    cupo_diario: máximo de citas propuestas ese día de semana.
    """

    __tablename__ = "disponibilidad_prof"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    profesional_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)          # 1–5
    cupo_diario: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class PropuestaAgenda(Base):
    """Propuesta de agenda generada para un profesional en un horizonte (diaria/semanal/mensual).

    tipo:       TipoPropuesta.value  — almacenado como String(10).
    estado:     EstadoPropuesta.value — almacenado como String(15).
    generado_por: username del actor que la generó (auditoría inline + RN-9).
    """

    __tablename__ = "propuesta_agenda"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    profesional_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="borrador")
    generado_por: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class CitaPropuesta(Base):
    """Cita individual dentro de una PropuestaAgenda.

    prioridad:   PrioridadCita.value — String(25).
    razon:       texto libre de hasta 120 chars (p. ej. "control vencido desde 2026-05-01").
    estado:      EstadoCita.value — String(15).
    excluida_por: motivo de exclusión si aplica (p. ej. "reposo vigente hasta 2026-06-20").
                  NULL si la cita no fue excluida.
    """

    __tablename__ = "cita_propuesta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    propuesta_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    paciente_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fecha_candidata: Mapped[date] = mapped_column(Date, nullable=False)
    prioridad: Mapped[str] = mapped_column(String(25), nullable=False)
    razon: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="propuesta")
    excluida_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
