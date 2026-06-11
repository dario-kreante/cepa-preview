"""Modelos del módulo EPT — Estudio de Puesto de Trabajo (EPIC-03).

CasoEpt   — caso EPT vinculado a un ingreso. Un ingreso puede tener un caso EPT.
ContactoEpt — correos de coordinación EPT del empleador (máx. 2 por caso;
              validado en la capa de servicio).
ProcesoEpt  — datos operativos del proceso (CEPA-031); solo aplica cuando
              corresponde_ept=True.
PlazoEpt    — plazos regulatorios ISL (CEPA-032); solo aplica cuando
              corresponde_ept=True.
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums_ept import EstadoEpt


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CasoEpt(Base):
    """Caso EPT asociado a un ingreso del CEPA.

    El campo corresponde_ept (Sí/True | No/False) determina si el caso tiene
    proceso y plazos EPT activos. Un caso con corresponde_ept=False queda
    registrado pero no exige datos de CEPA-031/032 (RN-5).
    Solo el rol Administrativo crea/edita (D1, RN-6).
    """

    __tablename__ = "caso_ept"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    mes: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_ingreso_ept: Mapped[date] = mapped_column(Date, nullable=False)
    nombre_trabajador: Mapped[str] = mapped_column(String(160), nullable=False)
    rut_trabajador: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    region_trabajador: Mapped[str] = mapped_column(String(80), nullable=False)
    eista: Mapped[str] = mapped_column(String(160), nullable=False)
    factor_riesgo: Mapped[str] = mapped_column(String(40), nullable=False)
    corresponde_ept: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EstadoEpt.ABIERTO.value
    )
    # datos del empleador
    razon_social: Mapped[str | None] = mapped_column(String(160), nullable=True)
    unidad_cargo_horario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    contactos: Mapped[list["ContactoEpt"]] = relationship(
        back_populates="caso_ept", cascade="all, delete-orphan"
    )
    proceso: Mapped["ProcesoEpt | None"] = relationship(
        back_populates="caso_ept", uselist=False, cascade="all, delete-orphan"
    )
    plazo: Mapped["PlazoEpt | None"] = relationship(
        back_populates="caso_ept", uselist=False, cascade="all, delete-orphan"
    )


class ContactoEpt(Base):
    """Correo de coordinación EPT del empleador.

    Un caso EPT acepta máximo 2 contactos (CEPA-030 RN-4).
    La restricción de máx. 2 se valida en la capa de servicio, no como constraint
    de BD, para mantener la portabilidad (no todos los motores soportan CHECK con
    subquery portable).
    """

    __tablename__ = "contacto_ept"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    caso_ept_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("caso_ept.id"), nullable=False, index=True
    )
    correo: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    caso_ept: Mapped[CasoEpt] = relationship(back_populates="contactos")


class ProcesoEpt(Base):
    """Datos operativos del proceso EPT (CEPA-031).

    Solo aplica cuando caso_ept.corresponde_ept = True.
    Los plazos (plazo_evidencia_denunciante, plazo_insumos_empresa) son fechas
    y no pueden ser anteriores a fecha_ingreso_ept del caso (RN-4 CEPA-031).
    testigos_cantidad = 0 cuando hay_testigos = False (RN-2).
    """

    __tablename__ = "proceso_ept"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    caso_ept_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("caso_ept.id"), nullable=False, unique=True, index=True
    )
    plazo_evid_denunciante: Mapped[date | None] = mapped_column(Date, nullable=True)
    plazo_insumos_empresa: Mapped[date | None] = mapped_column(Date, nullable=True)
    hay_testigos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    testigos_cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_entrevistas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    insumos_eista: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_incumplimiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    caso_ept: Mapped[CasoEpt] = relationship(back_populates="proceso")


class PlazoEpt(Base):
    """Plazos regulatorios de informe EPT / portal ISL (CEPA-032).

    Solo aplica cuando caso_ept.corresponde_ept = True.
    estado_informe y estado_entrega_isl se calculan en la capa de servicio
    a partir de la fecha objetivo y de si se registró envío (RN-1).
    """

    __tablename__ = "plazo_ept"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    caso_ept_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("caso_ept.id"), nullable=False, unique=True, index=True
    )
    plazo_informe_ept: Mapped[date | None] = mapped_column(Date, nullable=True)
    plazo_portal_isl: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_entrega_isl: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_envio: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado_informe: Mapped[str] = mapped_column(
        String(20), nullable=False, default="en_plazo"
    )
    estado_entrega_isl: Mapped[str] = mapped_column(
        String(20), nullable=False, default="en_plazo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    caso_ept: Mapped[CasoEpt] = relationship(back_populates="plazo")
