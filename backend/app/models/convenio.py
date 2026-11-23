"""Catálogo de convenios del CEPA, espejo de los convenios de SALUTEM.

``ingreso.tipo_convenio`` guarda el *nombre* del convenio (texto), no una clave: este catálogo
es la lista de opciones que ofrece el formulario y lo que el sync de SALUTEM mantiene al día.

- ``salutem_id`` / ``activo_salutem`` / ``sincronizado_en`` los escribe solo el sync; son nulos
  en los convenios creados a mano en SIGE.
- ``visible`` lo cambia solo el CEPA (oculta un convenio del formulario sin borrarlo). El sync
  no lo toca, salvo al crear «Sin Convenio», que nace oculto.
- Un convenio nunca se borra: los ingresos antiguos siguen apuntando a su nombre.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Convenio(Base):
    __tablename__ = "convenio"
    __table_args__ = (
        UniqueConstraint("nombre_normalizado", name="uq_convenio_nombre_norm"),
        UniqueConstraint("salutem_id", name="uq_convenio_salutem_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    # Mismo largo que ``ingreso.tipo_convenio``, que guarda este nombre.
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # Sin tildes, en minúsculas y con espacios colapsados: evita duplicados por escritura.
    nombre_normalizado: Mapped[str] = mapped_column(String(120), nullable=False)
    salutem_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activo_salutem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sincronizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    @property
    def seleccionable(self) -> bool:
        """Se ofrece en el formulario: visible y, si viene de SALUTEM, activo allá."""
        # ``visible`` y ``activo_salutem`` pueden ser None antes del flush (los defaults corren al insertar).
        visible = True if self.visible is None else self.visible
        activo = True if self.activo_salutem is None else self.activo_salutem
        return visible and (self.salutem_id is None or activo)
