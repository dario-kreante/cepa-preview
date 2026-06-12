"""Modelos de formularios dinámicos versionados (CEPA-110).

FormDefinition  — registro maestro de un formulario (p. ej. "ingresos").
FormVersion     — versión concreta (borrador o publicada); inmutable una vez publicada.
FieldDef        — campo individual de una versión. domain_values usa JSON genérico (portable).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import PortableJSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FormDefinition(Base):
    """Registro maestro de un formulario del sistema (uno por módulo/formulario)."""

    __tablename__ = "form_definition"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    form_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    versions: Mapped[list[FormVersion]] = relationship(
        back_populates="form_definition", cascade="all, delete-orphan"
    )


class FormVersion(Base):
    """Versión de un formulario. status: 'draft' o 'published'.

    Una vez publicada es inmutable: los nuevos cambios generan una nueva versión draft.
    """

    __tablename__ = "form_version"
    __table_args__ = (
        UniqueConstraint("form_def_id", "version_num", name="uq_formver_def_num"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    form_def_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("form_definition.id"), nullable=False, index=True
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    # status: 'draft' | 'published'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    form_definition: Mapped[FormDefinition] = relationship(back_populates="versions")
    fields: Mapped[list[FieldDef]] = relationship(
        back_populates="form_version", cascade="all, delete-orphan"
    )


class FieldDef(Base):
    """Definición de un campo dentro de una FormVersion.

    field_type ∈ {'text', 'number', 'date', 'select', 'boolean'}.
    domain_values: lista de valores permitidos (solo para field_type='select'); JSON genérico.
    system_locked: True para campos obligatorios del sistema (no removibles, CEPA-111 RN-2).
    active: False para campos desactivados (se conservan datos históricos, CA-2).
    """

    __tablename__ = "field_def"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    form_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("form_version.id"), nullable=False, index=True
    )
    field_key: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    # field_type: 'text' | 'number' | 'date' | 'select' | 'boolean'
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    system_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # JSON genérico (portable PG/Oracle — no usar JSONB)
    domain_values: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    form_version: Mapped[FormVersion] = relationship(back_populates="fields")
