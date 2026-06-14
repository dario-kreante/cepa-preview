"""Ficha clínica persistida en el dominio CEPA (D12).

El CEPA no escribe sobre SALUTEM; estos registros son la copia/recepción
local de datos clínicos. El origen indica desde dónde llegaron (SAM, SALUTEM,
push externo). El contenido clínico se almacena como JSON.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String

from app.db.types import PortableJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ingreso import Ingreso  # noqa: F401


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FichaClinica(Base):
    """Registro de datos clínicos recibidos/persistidos en el dominio CEPA.

    Tabla: ficha_clinica (≤30 chars). Cada registro es una entrada de datos
    clínicos asociada a un folio (ingreso). El origen identifica el sistema
    externo que proveyó los datos.
    """

    __tablename__ = "ficha_clinica"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    folio: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    origen: Mapped[str] = mapped_column(String(40), nullable=False)
    contenido: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="fichas_clinicas")
