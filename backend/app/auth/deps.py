from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import TokenInvalido, decodificar_token
from app.db.session import get_db
from app.models.usuario import ROL_ADMINISTRATIVO, ROL_SUPERADMIN, Usuario

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """Identidad mínima del usuario autenticado, derivada del JWT + BD."""

    id: int
    username: str
    role: str
    # CA-012 (QA 23-11-2026): permiso extra de lectura del módulo Auditoría para un
    # Administrativo. Se lee de la BD en cada request, así un cambio aplica sin re-login.
    acceso_auditoria: bool = False


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Resuelve al usuario autenticado a partir del access token. 401 si falta/expira/inactivo."""
    if credenciales is None or not credenciales.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decodificar_token(credenciales.credentials, tipo_esperado="access")
    except TokenInvalido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o desactivado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        id=usuario.id,
        username=usuario.username,
        role=usuario.rol,
        acceso_auditoria=bool(usuario.acceso_auditoria),
    )


def require_role(*roles: str):
    """Dependencia que exige que el usuario autenticado tenga uno de los roles dados (403 si no).

    Superadmin pasa siempre: tiene todos los permisos de los demás roles.
    """

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role != ROL_SUPERADMIN and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta operación",
            )
        return user

    return _checker


# Roles que entran al módulo Auditoría por su rol (RN-2, D1). Superadmin pasa siempre.
_ROLES_AUDITORIA = ("Coordinacion", "Auditor")


def tiene_acceso_auditoria(user: CurrentUser) -> bool:
    """True si el usuario puede leer el módulo Auditoría.

    Coordinación, Auditor y Superadmin por rol; un Administrativo solo con el permiso extra
    ``acceso_auditoria`` (CA-012, QA 23-11-2026). El flag no da nada a otros roles.
    """
    if user.role == ROL_SUPERADMIN or user.role in _ROLES_AUDITORIA:
        return True
    return user.role == ROL_ADMINISTRATIVO and user.acceso_auditoria


def require_auditoria(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependencia de lectura del módulo Auditoría (vista de caso, reportes y log). 403 si no."""
    if not tiene_acceso_auditoria(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para esta operación",
        )
    return user
