"""Modelos del módulo de Seguimiento de Reintegro (EPIC-04).

Tablas: caso_reintegro, reca.
- caso_reintegro: vinculado al ingreso (FK); contiene los datos del caso (CEPA-040)
  y las columnas de cierre/reintegro (CEPA-042).
- reca: subrecurso de caso_reintegro; contiene datos de la RECA y medidas (CEPA-041).
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.reintegro_enums import EstadoReintegro


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CasoReintegro(Base):
    """Caso de reintegro laboral vinculado a un ingreso/folio (CEPA-040, 042).

    Los campos de reintegro y cierre (estado_reintegro, fecha_reintegro,
    altas, tipo_alta) se completan en la fase de cierre (CEPA-042).
    """

    __tablename__ = "caso_reintegro"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    # Datos del caso (CEPA-040) ────────────────────────────────────────────
    rut: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo_derivacion: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_caso: Mapped[date] = mapped_column(Date, nullable=False)
    sexo: Mapped[str] = mapped_column(String(10), nullable=False)
    edad: Mapped[int] = mapped_column(BigInteger, nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    comuna: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rubro_empleador: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Cierre / reintegro (CEPA-042) ────────────────────────────────────────
    estado_reintegro: Mapped[str] = mapped_column(
        String(20), default=EstadoReintegro.PENDIENTE.value, nullable=False
    )
    fecha_reintegro: Mapped[date | None] = mapped_column(Date, nullable=True)
    remitido_isl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alta_medica: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_alta_medica: Mapped[date | None] = mapped_column(Date, nullable=True)
    alta_psicologica: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_alta_psico: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_alta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Auditoría ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    reca: Mapped["Reca | None"] = relationship(
        back_populates="caso", uselist=False, cascade="all, delete-orphan"
    )


class Reca(Base):
    """RECA (Resolución de Calificación) y ciclo de medidas correctivas (CEPA-041).

    Una RECA por caso de reintegro. El número de RECA es único dentro del caso
    (restricción UniqueConstraint sobre numero_reca + caso_reintegro_id).
    """

    __tablename__ = "reca"
    __table_args__ = (
        UniqueConstraint(
            "numero_reca", "caso_reintegro_id", name="uq_reca_numero_caso"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    caso_reintegro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("caso_reintegro.id"), nullable=False, index=True
    )
    # Datos RECA ───────────────────────────────────────────────────────────
    fecha_reca: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_reca: Mapped[str] = mapped_column(String(10), nullable=False)
    numero_reca: Mapped[str] = mapped_column(String(40), nullable=False)
    riesgos_calificados: Mapped[str | None] = mapped_column(Text, nullable=True)
    razon_social: Mapped[str] = mapped_column(String(160), nullable=False)
    # Medidas correctivas ──────────────────────────────────────────────────
    solicita_medidas: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detalle_medidas: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_medidas: Mapped[date | None] = mapped_column(Date, nullable=True)
    verifica_medidas: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detalle_verificacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_verificacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Auditoría ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    caso: Mapped["CasoReintegro"] = relationship(back_populates="reca")
