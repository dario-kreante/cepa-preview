from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import (
    TokenInvalido,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
)
from app.auth.service import CredencialesInvalidas, CuentaBloqueada, autenticar
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        usuario = autenticar(db, payload.username, payload.password)
    except CuentaBloqueada as exc:
        db.commit()  # persiste el bloqueo y su traza de auditoría
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except CredencialesInvalidas as exc:
        db.commit()  # persiste el incremento de intentos y la traza LOGIN_FALLIDO
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    db.commit()
    return TokenPair(
        access_token=crear_access_token(usuario.id, usuario.username, usuario.rol),
        refresh_token=crear_refresh_token(usuario.id, usuario.username, usuario.rol),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    try:
        claims = decodificar_token(payload.refresh_token, tipo_esperado="refresh")
    except TokenInvalido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado"
        )

    usuario = db.get(Usuario, int(claims["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inexistente o desactivado"
        )
    return AccessTokenResponse(
        access_token=crear_access_token(usuario.id, usuario.username, usuario.rol)
    )
