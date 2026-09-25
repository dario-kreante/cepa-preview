"""Catálogo de tramos de GAF — v5 D18, COMP-2609-12.

Sembrado con los 10 tramos EEAG de 10 en 10 (``provisorio=True``) hasta que la contraparte
confirme la segmentación (PA-v5-03). Los registros guardan la ``etiqueta`` del tramo
("41-50"), igual que SALUTEM, para no depender del id si el catálogo se resiembra.
"""

from sqlalchemy import BigInteger, Boolean, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GafTramo(Base):
    __tablename__ = "gaf_tramo"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    desde: Mapped[int] = mapped_column(Integer, nullable=False)
    hasta: Mapped[int] = mapped_column(Integer, nullable=False)
    etiqueta: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    provisorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
