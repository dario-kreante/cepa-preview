import jwt
import pytest

from app.auth.jwt import (
    TokenInvalido,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
)
from app.config import get_settings


def test_access_token_porta_identidad_y_rol_no_la_clave():
    token = crear_access_token(user_id=7, username="maria", role="Coordinacion")
    payload = decodificar_token(token, tipo_esperado="access")
    assert payload["sub"] == "7"
    assert payload["username"] == "maria"
    assert payload["role"] == "Coordinacion"
    assert payload["type"] == "access"
    assert "password" not in payload and "hashed_password" not in payload


def test_refresh_token_tiene_type_refresh():
    token = crear_refresh_token(user_id=7, username="maria", role="Coordinacion")
    payload = decodificar_token(token, tipo_esperado="refresh")
    assert payload["type"] == "refresh"


def test_no_se_acepta_refresh_donde_se_espera_access():
    refresh = crear_refresh_token(user_id=7, username="maria", role="Auditor")
    with pytest.raises(TokenInvalido):
        decodificar_token(refresh, tipo_esperado="access")


def test_token_con_firma_invalida_es_rechazado():
    token = crear_access_token(user_id=1, username="x", role="Administrativo")
    falso = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(TokenInvalido):
        decodificar_token(falso, tipo_esperado="access")


def test_token_expirado_es_rechazado():
    settings = get_settings()
    payload = {
        "sub": "1",
        "username": "x",
        "role": "Administrativo",
        "type": "access",
        "exp": 1,  # 1970, ya expirado
    }
    expirado = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(TokenInvalido):
        decodificar_token(expirado, tipo_esperado="access")
