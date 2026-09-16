"""Control del sync SALUTEM: checkpoint por día, bitácora de ejecuciones y lease."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SalutemSyncDia(Base):
    """Día ya barrido por completo en la carga inicial (permite reanudarla)."""

    __tablename__ = "salutem_sync_dia"

    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    tipo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    citas: Mapped[int] = mapped_column(Integer, nullable=False)
    completado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SalutemSyncEjecucion(Base):
    """Bitácora: una fila por ejecución de un modo del sync."""

    __tablename__ = "salutem_sync_ejecucion"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    modo: Mapped[str] = mapped_column(String(20), nullable=False)
    # en_curso | ok | con_errores | error | omitida
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llamadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nuevos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cambiados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    desaparecidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class SalutemSyncLease(Base):
    """Un solo proceso de sync a la vez. La fila `salutem` la siembra la migración 1250."""

    __tablename__ = "salutem_sync_lease"

    nombre: Mapped[str] = mapped_column(String(30), primary_key=True)
    dueno: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
