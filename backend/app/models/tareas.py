"""Modelo TareaItem — tareas operativas por rol (CEPA-103 EPIC-10).

Portabilidad D15: PK Identity/BigInteger, tipos genéricos, identificadores
≤30 chars en minúscula, fechas en UTC.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TareaItem(Base):
    """Tarea operativa asignada a un usuario por rol.

    - usuario_id:    destinatario principal de la tarea
    - tipo_tarea:    categoría operativa ('gestionar_receta', 'enviar_informe', etc.)
    - caso_id:       id del objeto de dominio origen (nullable — tarea puede ser sin caso)
    - caso_tipo:     'ingreso' | 'oda' | 'ept' | etc. (nullable)
    - completada_por: username de quien completó (RN-3 — registrar quién y cuándo)
    """

    __tablename__ = "tarea_item"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    tipo_tarea: Mapped[str] = mapped_column(String(60), nullable=False)
    caso_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    caso_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completada_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
