"""Modelos del dominio de Gestión de Fármacos (EPIC-02).

Tablas: reg_farmacologico, esquema_indicacion, receta, seguim_tratamiento, alerta.
Todas siguen las reglas de portabilidad D15: tipos genéricos SQLAlchemy, Identity,
identificadores ≤30 chars en minúscula, fechas UTC.
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RegistroFarmacologico(Base):
    """Registro farmacológico de un paciente, vinculado 1:1 al ingreso (CEPA-020).

    El campo `activo` permite reutilizar/reactivar el registro en un reingreso
    (CEPA-020 RN-4) sin duplicar la fila — se conserva el historial completo.
    """

    __tablename__ = "reg_farmacologico"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), unique=True, nullable=False
    )
    medico_tratante: Mapped[str] = mapped_column(String(160), nullable=False)
    estado_farmacologico: Mapped[str] = mapped_column(String(40), nullable=False)
    antecedentes_previos: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento_previo: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    indicaciones: Mapped[list["EsquemaIndicacion"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )
    recetas: Mapped[list["Receta"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )
    seguimientos: Mapped[list["SeguimTratamiento"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )


class EsquemaIndicacion(Base):
    """Indicación farmacológica individual del esquema del paciente (CEPA-021).

    El esquema es versionable: una nueva indicación no reemplaza la anterior,
    se agrega como nueva fila (CEPA-021 RN-2). `vigente=True` marca la actual.
    `extra_sistema=True` identifica fármacos fuera del catálogo institucional (D7).
    """

    __tablename__ = "esquema_indicacion"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    registro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reg_farmacologico.id"), nullable=False, index=True
    )
    medicamento: Mapped[str] = mapped_column(String(200), nullable=False)
    dosis: Mapped[str] = mapped_column(String(80), nullable=False)
    frecuencia: Mapped[str] = mapped_column(String(40), nullable=False)
    extra_sistema: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    registro: Mapped["RegistroFarmacologico"] = relationship(back_populates="indicaciones")


class Receta(Base):
    """Receta vinculada a un registro farmacológico (CEPA-022).

    Contiene las tres fechas del ciclo: emisión, revisión y envío.
    El proceso de alertas revisa `fecha_revision` contra la fecha actual (RN-3).
    """

    __tablename__ = "receta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    registro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reg_farmacologico.id"), nullable=False, index=True
    )
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_revision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_envio: Mapped[date | None] = mapped_column(Date, nullable=True)
    marca_medicamento: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    registro: Mapped["RegistroFarmacologico"] = relationship(back_populates="recetas")


class SeguimTratamiento(Base):
    """Seguimiento de tratamiento farmacológico de un paciente (CEPA-023).

    Si `disminucion_farmacos=True` → `plan_disminucion` obligatorio (validado en servicio).
    Si `cambio_esquema=True` → `detalle_cambio` obligatorio (validado en servicio).
    """

    __tablename__ = "seguim_tratamiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    registro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reg_farmacologico.id"), nullable=False, index=True
    )
    disminucion_farmacos: Mapped[bool] = mapped_column(Boolean, nullable=False)
    plan_disminucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cambio_esquema: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detalle_cambio: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    registro: Mapped["RegistroFarmacologico"] = relationship(back_populates="seguimientos")


class Alerta(Base):
    """Alerta generada por el proceso de revisión de recetas (CEPA-022 RN-3).

    Se escribe cuando `fecha_revision` de una receta está dentro de los próximos
    5 días (límite inclusivo). La entrega in-app la gestiona EPIC-10.
    """

    __tablename__ = "alerta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    receta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receta.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(300), nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    receta: Mapped["Receta"] = relationship()
