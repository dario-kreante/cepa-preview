"""Lógica de negocio para el editor de formularios dinámicos (CEPA-110 / CEPA-111)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.form_definition import FieldDef, FormDefinition, FormVersion
from app.schemas.form_config import FieldDefIn, FormVersionCreate
from app.services.form_validator import ParametrizationError, validate_form_version


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_form_def(db: Session, form_key: str) -> FormDefinition:
    fd = db.execute(
        select(FormDefinition).where(FormDefinition.form_key == form_key)
    ).scalar_one_or_none()
    if fd is None:
        fd = FormDefinition(form_key=form_key)
        db.add(fd)
        db.flush()
    return fd


def _next_version_num(db: Session, form_def_id: int) -> int:
    from sqlalchemy import func
    result = db.execute(
        select(func.max(FormVersion.version_num)).where(
            FormVersion.form_def_id == form_def_id
        )
    ).scalar_one_or_none()
    return (result or 0) + 1


def create_draft(
    db: Session, form_key: str, payload: FormVersionCreate, username: str
) -> FormVersion:
    """Crea un borrador (status='draft') para el formulario indicado."""
    fd = _get_or_create_form_def(db, form_key)
    num = _next_version_num(db, fd.id)
    version = FormVersion(
        form_def_id=fd.id,
        version_num=num,
        status="draft",
        published_at=None,
        created_by=username,
    )
    db.add(version)
    db.flush()

    for f in payload.fields:
        field = FieldDef(
            form_version_id=version.id,
            field_key=f.field_key,
            label=f.label,
            field_type=f.field_type,
            required=f.required,
            system_locked=f.system_locked,
            domain_values=f.domain_values,
            display_order=f.display_order,
            active=f.active,
        )
        db.add(field)
    db.flush()
    return version


def publish_version(db: Session, form_key: str, version_id: int, username: str) -> dict:
    """Publica una versión borrador previo paso por el validador.

    Devuelve dict compatible con PublishResult.
    Si la validación falla, no publica y devuelve los errores.
    """
    version = db.execute(
        select(FormVersion)
        .options(selectinload(FormVersion.fields))
        .where(FormVersion.id == version_id)
        .join(FormVersion.form_definition)
        .where(FormDefinition.form_key == form_key)
    ).scalar_one_or_none()

    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versión no encontrada.")
    if version.status == "published":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La versión ya está publicada.")

    # Convertir FieldDef ORM a dicts para el validador
    fields_as_dicts = [
        {
            "field_key": f.field_key,
            "label": f.label,
            "field_type": f.field_type,
            "required": f.required,
            "system_locked": f.system_locked,
            "domain_values": f.domain_values,
            "active": f.active,
        }
        for f in version.fields
    ]
    errors = validate_form_version(fields_as_dicts)
    if errors:
        return {"success": False, "version_id": None, "errors": errors}

    version.status = "published"
    version.published_at = _utcnow()
    db.flush()
    return {"success": True, "version_id": version.id, "errors": []}


def get_published_version(db: Session, form_key: str) -> FormVersion:
    """Devuelve la versión publicada más reciente o 404."""
    version = db.execute(
        select(FormVersion)
        .options(selectinload(FormVersion.fields))
        .join(FormVersion.form_definition)
        .where(FormDefinition.form_key == form_key, FormVersion.status == "published")
        .order_by(FormVersion.version_num.desc())
        .limit(1)
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay versión publicada para el formulario '{form_key}'.",
        )
    return version


def get_version_by_id(db: Session, form_key: str, version_id: int) -> FormVersion:
    """Devuelve una versión específica por ID (para consulta histórica)."""
    version = db.execute(
        select(FormVersion)
        .options(selectinload(FormVersion.fields))
        .where(FormVersion.id == version_id)
        .join(FormVersion.form_definition)
        .where(FormDefinition.form_key == form_key)
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versión no encontrada.")
    return version
