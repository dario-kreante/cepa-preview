from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import get_settings
from app.models.usuario import Usuario


def _crear(db: Session, username="maria", rol="Coordinacion", activo=True) -> Usuario:
    u = Usuario(
        username=username,
        nombre="Maria",
        hashed_password=hash_password("Clave123!"),
        rol=rol,
        activo=activo,
        intentos_fallidos=0,
    )
    db.add(u)
    db.flush()
    return u


def test_login_exitoso_devuelve_par_de_tokens(client: TestClient, db_session: Session):
    _crear(db_session)
    r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "Clave123!"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["access_token"] and cuerpo["refresh_token"]
    assert cuerpo["token_type"] == "bearer"


def test_login_con_clave_incorrecta_devuelve_401_generico(client: TestClient, db_session: Session):
    _crear(db_session)
    r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "mala"})
    assert r.status_code == 401
    # mensaje genérico, no revela el campo fallido (TC-001-03)
    assert "inválid" in r.json()["detail"].lower()


def test_login_usuario_inexistente_devuelve_401(client: TestClient):
    r = client.post("/api/v1/auth/login", json={"username": "fantasma", "password": "x"})
    assert r.status_code == 401


def test_login_bloqueo_tras_n_intentos_devuelve_429(client: TestClient, db_session: Session):
    settings = get_settings()
    _crear(db_session)
    # N-1 fallos: 401
    for _ in range(settings.login_max_intentos - 1):
        r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "mala"})
        assert r.status_code == 401
    # intento N: bloqueo -> 429
    r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "mala"})
    assert r.status_code == 429


def test_refresh_renueva_access_token(client: TestClient, db_session: Session):
    _crear(db_session)
    login = client.post("/api/v1/auth/login", json={"username": "maria", "password": "Clave123!"})
    refresh = login.json()["refresh_token"]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"


def test_refresh_con_token_invalido_devuelve_401(client: TestClient):
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "no-es-jwt"})
    assert r.status_code == 401


def test_endpoint_protegido_sin_token_devuelve_401(client: TestClient):
    # /whoami-test (montado en conftest) requiere get_current_user
    assert client.get("/whoami-test").status_code == 401
