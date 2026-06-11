import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, get_current_user, require_role
from app.auth.jwt import crear_access_token
from app.auth.security import hash_password
from app.db.session import get_db
from app.models.usuario import Usuario


@pytest.fixture
def mini_app(db_session: Session):
    app = FastAPI()

    @app.get("/yo")
    def yo(user: CurrentUser = Depends(get_current_user)) -> dict:
        return {"id": user.id, "username": user.username, "role": user.role}

    @app.get("/solo-coordinacion", dependencies=[Depends(require_role("Coordinacion"))])
    def solo_coord() -> dict:
        return {"ok": True}

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def _crear_usuario(db: Session, username: str, rol: str, activo: bool = True) -> Usuario:
    u = Usuario(
        username=username,
        nombre=username.title(),
        hashed_password=hash_password("Clave123"),
        rol=rol,
        activo=activo,
        intentos_fallidos=0,
    )
    db.add(u)
    db.flush()
    return u


def test_sin_token_devuelve_401(mini_app):
    client = TestClient(mini_app)
    assert client.get("/yo").status_code == 401


def test_token_invalido_devuelve_401(mini_app):
    client = TestClient(mini_app)
    r = client.get("/yo", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert r.status_code == 401


def test_token_valido_resuelve_current_user(mini_app, db_session):
    u = _crear_usuario(db_session, "maria", "Coordinacion")
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"id": u.id, "username": "maria", "role": "Coordinacion"}


def test_usuario_desactivado_devuelve_401(mini_app, db_session):
    u = _crear_usuario(db_session, "expulsado", "Administrativo", activo=False)
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_require_role_permite_rol_correcto(mini_app, db_session):
    u = _crear_usuario(db_session, "coord", "Coordinacion")
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/solo-coordinacion", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_require_role_rechaza_rol_incorrecto_con_403(mini_app, db_session):
    u = _crear_usuario(db_session, "admin", "Administrativo")
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/solo-coordinacion", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
