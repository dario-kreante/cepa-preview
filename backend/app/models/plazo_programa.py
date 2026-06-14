from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlazoPrograma(Base):
    """Plazo (en días) para el informe de evaluación por programa (v4 D10)."""

    __tablename__ = "plazo_programa"

    programa: Mapped[str] = mapped_column(String(80), primary_key=True)
    dias_plazo_informe: Mapped[int] = mapped_column(Integer, nullable=False)
