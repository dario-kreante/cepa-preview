from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FolioSeq(Base):
    """Contador de folios por año (portable). Una fila por año; se bloquea para incrementar.

    No se usa SERIAL ni secuencias nativas para mantener la portabilidad (D15); el
    correlativo se gestiona en la capa de aplicación con SELECT ... FOR UPDATE.
    """

    __tablename__ = "folio_seq"

    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    ultimo: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
