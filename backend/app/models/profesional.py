"""Catálogo de profesionales del CEPA (agendamiento).

Antes el agendamiento trabajaba con un ``profesional_id`` suelto que no apuntaba a nada. Este
catálogo le da nombre a ese número: ``disponibilidad_prof.profesional_id`` y
``propuesta_agenda.profesional_id`` guardan el ``id`` de esta tabla.

Se siembra con los médicos tratantes de los controles que llegan desde SALUTEM
(``origen='SALUTEM'``) y se completa a mano desde Configuración (``origen='SIGE'``).
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Nombre que pone el sync cuando la atención de SALUTEM no informa profesional.
SIN_PROFESIONAL_SALUTEM = "Sin profesional informado"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profesional(Base):
    __tablename__ = "profesional"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    # Mismo largo que control_medico.medico_tratante, que es de donde se siembra.
    nombre: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    especialidad: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origen: Mapped[str] = mapped_column(String(10), nullable=False, default="SIGE")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
