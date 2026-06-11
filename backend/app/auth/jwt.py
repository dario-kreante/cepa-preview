from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.config import get_settings


class TokenInvalido(Exception):
    """El token JWT es inválido, expiró o no es del tipo esperado."""


def _crear_token(
    user_id: int, username: str, role: str, tipo: Literal["access", "refresh"], expira_min: int
) -> str:
    settings = get_settings()
    ahora = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": tipo,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=expira_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def crear_access_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    return _crear_token(user_id, username, role, "access", settings.access_token_expira_min)


def crear_refresh_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    return _crear_token(user_id, username, role, "refresh", settings.refresh_token_expira_min)


def decodificar_token(token: str, tipo_esperado: Literal["access", "refresh"]) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:  # firma inválida, expirado, malformado
        raise TokenInvalido(str(exc)) from exc
    if payload.get("type") != tipo_esperado:
        raise TokenInvalido(f"se esperaba un token '{tipo_esperado}'")
    return payload
