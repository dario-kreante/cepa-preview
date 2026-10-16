"""Catálogo de profesionales del CEPA (agendamiento).

Antes el agendamiento trabajaba con un ``profesional_id`` suelto que no apuntaba a nada. Este
catálogo le da nombre a ese número: ``disponibilidad_prof.profesional_id`` y
``propuesta_agenda.profesional_id`` guardan el ``id`` de esta tabla.

Se siembra con los médicos tratantes de los controles que llegan desde SALUTEM
(``origen='SALUTEM'``) y se completa a mano desde Configuración (``origen='SIGE'``).
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import PortableJSON

# Nombre que pone el sync cuando la atención de SALUTEM no informa profesional.
SIN_PROFESIONAL_SALUTEM = "Sin profesional informado"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profesional(Base):
    __tablename__ = "profesional"
    __table_args__ = (UniqueConstraint("salutem_profesional_id", name="uq_profesional_salutem_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    # Mismo largo que control_medico.medico_tratante, que es de donde se siembra.
    nombre: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    especialidad: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origen: Mapped[str] = mapped_column(String(10), nullable=False, default="SIGE")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Datos que arma el sync desde la copia de SALUTEM (migración 1350) ────────────
    # SALUTEM no tiene endpoint de profesionales: el id sale de ``profesionalId`` de las
    # citas y atenciones. Nulo en los cargados a mano en SIGE.
    salutem_profesional_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Listas de nombres (unión de lo visto en SALUTEM); nulas si nunca se sincronizó.
    especialidades: Mapped[list[str] | None] = mapped_column(PortableJSON, nullable=True)
    sucursales: Mapped[list[str] | None] = mapped_column(PortableJSON, nullable=True)
    # Fecha de la primera y la última cita en estado Atendido.
    primera_atencion: Mapped[date | None] = mapped_column(Date, nullable=True)
    ultima_atencion: Mapped[date | None] = mapped_column(Date, nullable=True)
    sincronizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
