"""Tabla de registro de payloads IMED entrantes (CEPA-122).

Persiste el payload recibido antes de procesarlo (patrón inbox).
Se activa cuando IMED_ENABLED=true (PA5). El tipo diferencia
licencias médicas electrónicas de recetas electrónicas.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, String

from app.db.types import PortableJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ImedPayload(Base):
    """Registro de payload IMED entrante (inbox ante fallo/reprocesado).

    Tabla: imed_payload (≤30 chars — cumple D15).
    """

    __tablename__ = "imed_payload"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    folio: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    datos: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
