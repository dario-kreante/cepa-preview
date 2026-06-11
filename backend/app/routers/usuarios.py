from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import CurrentUser, require_role
from app.auth.security import hash_password
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])

# Toda la gestión de usuarios es exclusiva de Coordinación (CEPA-002 RN-4).
_solo_coordinacion = require_role("Coordinacion")


def _get_usuario_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = Usuario(
        username=payload.username,
        nombre=payload.nombre,
        hashed_password=hash_password(payload.password),
        rol=payload.rol,
        activo=True,
        intentos_fallidos=0,
        email=payload.email,
    )
    db.add(usuario)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El username ya existe"
        )
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="CREATE",
        entity="usuario",
        entity_id=str(usuario.id),
        valor_nuevo=f'{{"username": "{usuario.username}", "rol": "{usuario.rol}"}}',
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("", response_model=list[UsuarioRead])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_solo_coordinacion),
) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id)))


@router.get("/{usuario_id}", response_model=UsuarioRead)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    return _get_usuario_o_404(db, usuario_id)


@router.put("/{usuario_id}", response_model=UsuarioRead)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    if payload.nombre is not None:
        usuario.nombre = payload.nombre
    if payload.rol is not None:
        usuario.rol = payload.rol
    if payload.password is not None:
        usuario.hashed_password = hash_password(payload.password)
    if payload.email is not None:
        usuario.email = payload.email
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="UPDATE",
        entity="usuario",
        entity_id=str(usuario.id),
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/desactivar", response_model=UsuarioRead)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    usuario.activo = False
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="UPDATE",
        entity="usuario",
        entity_id=str(usuario.id),
        valor_anterior='{"activo": true}',
        valor_nuevo='{"activo": false}',
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/activar", response_model=UsuarioRead)
def activar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    usuario.activo = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="UPDATE",
        entity="usuario",
        entity_id=str(usuario.id),
        valor_anterior='{"activo": false}',
        valor_nuevo='{"activo": true}',
    )
    db.commit()
    db.refresh(usuario)
    return usuario
