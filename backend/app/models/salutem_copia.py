"""Copia local de SALUTEM (sync fase 1, solo lectura — D12).

Guarda lo que devuelve SALUTEM tal cual, con un hash para detectar cambios.
Nunca se borra una fila: lo que deja de aparecer en SALUTEM se marca con
`desaparecida_en`. El dominio CEPA no lee estas tablas directamente; la
vinculación (services/salutem_sync/vinculacion.py) las pasa a ficha_clinica.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import PortableJSON


class _RegistroCopia:
    """Columnas comunes: contenido crudo, hash y marcas de tiempo."""

    contenido: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    # `hash` a secas es palabra clave en Oracle.
    hash_contenido: Mapped[str] = mapped_column(String(64), nullable=False)
    visto_primera_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    visto_ultima_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cambiado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SalutemPersona(_RegistroCopia, Base):
    __tablename__ = "salutem_persona"

    salutem_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    # RUT en la forma canónica del CEPA (`<cuerpo><DV>`); None si SALUTEM no trae uno válido.
    rut: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)


class SalutemCita(_RegistroCopia, Base):
    __tablename__ = "salutem_cita"

    cita_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    # Sin FK: la cita puede llegar antes que su persona.
    persona_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    fecha_cita: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fecha_creacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estado_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    desaparecida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SalutemAtencion(_RegistroCopia, Base):
    __tablename__ = "salutem_atencion"

    cita_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    persona_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    fecha_cita: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # Hash que la vinculación ya aplicó a ficha_clinica. Distinto de hash_contenido = pendiente.
    hash_vinculado: Mapped[str | None] = mapped_column(String(64), nullable=True)
    desaparecida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
