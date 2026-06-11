"""Router de tareas pendientes por rol (EPIC-10, CEPA-103)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.enums_alertas import EstadoTarea
from app.models.tareas import TareaItem
from app.schemas.tareas import TareaItemCreate, TareaItemRead, TareaItemUpdate

router = APIRouter(prefix="/api/v1/tareas", tags=["tareas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get("", response_model=list[TareaItemRead], dependencies=[Depends(_reader)])
def listar_tareas(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TareaItem]:
    """Lista de tareas pendientes por rol (CA-1, CA-3, CA-4 CEPA-103).

    - Administrativo: solo sus tareas (usuario_id == current_user.id).
    - Coordinacion: todas las tareas del equipo (vista de supervisión, CA-4).
    - Auditor: lectura de todas (sin filtro de usuario).
    """
    stmt = select(TareaItem).where(TareaItem.estado != EstadoTarea.COMPLETADA.value)
    if current_user.role == "Administrativo":
        stmt = stmt.where(TareaItem.usuario_id == current_user.id)
    stmt = stmt.order_by(TareaItem.creada_en.desc())
    return list(db.scalars(stmt))


@router.post(
    "",
    response_model=TareaItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_tarea(
    payload: TareaItemCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TareaItem:
    """Crea una tarea operativa asignada a un usuario (RN-1 CEPA-103).

    DD-B: auditoría ANTES del commit.
    """
    tarea = TareaItem(**payload.model_dump(), estado=EstadoTarea.PENDIENTE.value)
    db.add(tarea)
    db.flush()  # obtiene el id sin commit para poder registrarlo en auditoría

    # DD-B: registrar auditoría ANTES del commit
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="tarea_item",
        entity_id=str(tarea.id),
    )
    db.commit()
    db.refresh(tarea)
    return tarea


@router.patch("/{tarea_id}", response_model=TareaItemRead, dependencies=[Depends(_writer)])
def actualizar_tarea(
    tarea_id: int,
    payload: TareaItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TareaItem:
    """Marca una tarea como completada o en progreso (CA-2, RN-3 CEPA-103).

    DD-B: auditoría ANTES del commit.
    """
    tarea = db.get(TareaItem, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    tarea.estado = payload.estado.value
    if payload.estado == EstadoTarea.COMPLETADA:
        tarea.completada_en = datetime.now(timezone.utc)
        tarea.completada_por = current_user.username

    # DD-B: registrar auditoría ANTES del commit
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="tarea_item",
        entity_id=str(tarea_id),
    )
    db.commit()
    db.refresh(tarea)
    return tarea
