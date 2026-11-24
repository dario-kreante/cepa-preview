"""Catálogos de fármacos por convenio (QA-010 / QA-013, 23-11-2026).

- ``FarmacoCanasta``: canasta del Convenio 002 (código SAP, descripción, principio activo, marca…).
- ``FarmacoExternalizado``: lista «Externalizado» con la glosa truncada del ISL y la marca de
  Convenio 001 y/o 002.

Datos del sistema sembrados por la migración 1580 desde ``app/data/farmacos_convenio.json``.
"""

from sqlalchemy import BigInteger, Boolean, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FarmacoCanasta(Base):
    __tablename__ = "farmaco_canasta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    codigo_sap: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    descripcion: Mapped[str] = mapped_column(String(120), nullable=False)
    principio_activo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bioequivalencia: Mapped[str | None] = mapped_column(String(5), nullable=True)
    detalle_be: Mapped[str | None] = mapped_column(String(40), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(80), nullable=True)
    familia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    laboratorio: Mapped[str | None] = mapped_column(String(120), nullable=True)


class FarmacoExternalizado(Base):
    __tablename__ = "farmaco_externalizado"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    glosa: Mapped[str] = mapped_column(String(60), nullable=False)
    convenio_001: Mapped[bool] = mapped_column(Boolean, nullable=False)
    convenio_002: Mapped[bool] = mapped_column(Boolean, nullable=False)
