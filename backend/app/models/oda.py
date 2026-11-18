from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Oda(Base):
    """Orden de Primera Atención (v4 D3). Documento administrativo con vencimiento.

    Vinculada al ingreso (folio del paciente). Varias ODAS por ingreso: registrar una
    actualizada no borra las anteriores; `vigente` marca la activa.
    """

    __tablename__ = "oda"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    identificador: Mapped[str] = mapped_column(String(60), nullable=False)
    fecha_registro: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # «Tipo de Orden» tal como lo informa el reporte ISL (Ambulatoria = ODA; OPA/OPAEP = OPA).
    # NULL en las órdenes cargadas antes de QA-007 o registradas a mano: se completa al recargar
    # el reporte ISL.
    tipo_orden: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Gestión de la ODA vencida (QA-007): pendiente | solicitada | recibida.
    estado_gestion: Mapped[str] = mapped_column(
        String(20), default="pendiente", server_default="pendiente", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="odas")  # noqa: F821
