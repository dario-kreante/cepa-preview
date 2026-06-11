from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import TokenInvalido, decodificar_token
from app.db.session import get_db
from app.models.usuario import Usuario

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """Identidad mínima del usuario autenticado, derivada del JWT + BD."""

    id: int
    username: str
    role: str


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
    return CurrentUser(id=usuario.id, username=usuario.username, role=usuario.rol)


def require_role(*roles: str):
    """Dependencia que exige que el usuario autenticado tenga uno de los roles dados (403 si no)."""

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta operación",
            )
        return user

    return _checker
