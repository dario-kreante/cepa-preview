"""Router para el editor de formularios dinámicos (CEPA-110 / CEPA-111)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.form_config import FormVersionCreate, FormVersionRead, PublishResult
from app.services import form_config as svc

router = APIRouter(prefix="/api/v1/form-definitions", tags=["form-definitions"])

# Solo Coordinacion puede editar formularios (CEPA-110 RN-1)
_coord = require_role("Coordinacion")
# Lectura abierta a todos los roles (CA-4 test: auditor puede leer la versión publicada)
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "/{form_key}/draft",
    response_model=FormVersionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_coord)],
)
def crear_borrador(
    form_key: str,
    payload: FormVersionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> FormVersionRead:
    version = svc.create_draft(db, form_key, payload, current_user.username)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="form_version",
        entity_id=str(version.id),
    )
    db.commit()
    db.refresh(version)
    return version


@router.post(
    "/{form_key}/publish/{version_id}",
    response_model=PublishResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_coord)],
)
def publicar(
    form_key: str,
    version_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PublishResult:
    result = svc.publish_version(db, form_key, version_id, current_user.username)
    if result["success"]:
        record_audit(
            db,
            actor=current_user.username,
            action="UPDATE",
            entity="form_version",
            entity_id=str(version_id),
        )
        db.commit()
        return result
    else:
        # Publicación bloqueada: devolver 422 con body igual a PublishResult
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=result,
        )


@router.get(
    "/{form_key}/published",
    response_model=FormVersionRead,
    dependencies=[Depends(_reader)],
)
def obtener_version_publicada(
    form_key: str,
    db: Session = Depends(get_db),
) -> FormVersionRead:
    return svc.get_published_version(db, form_key)


@router.get(
    "/{form_key}/versions/{version_id}",
    response_model=FormVersionRead,
    dependencies=[Depends(_reader)],
)
def obtener_version_por_id(
    form_key: str,
    version_id: int,
    db: Session = Depends(get_db),
) -> FormVersionRead:
    return svc.get_version_by_id(db, form_key, version_id)
