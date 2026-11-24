"""CA-012 (QA 23-11-2026): permiso extra «Acceso a Auditoría» para un Administrativo.

- Sin el permiso, un Administrativo recibe 403 en el módulo Auditoría y en el log.
- Con el permiso, puede leer la vista de caso, los reportes, la descarga Excel y el log.
- El permiso se lee de la BD en cada request: un cambio aplica sin emitir un token nuevo.
- Solo Coordinación lo gestiona y solo se guarda para Administrativo.
"""
from collections.abc import Generator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.jwt import crear_access_token, decodificar_token
from app.auth.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.usuario import Usuario

PERIODO = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}


def _sembrar(db: Session, username: str, rol: str, acceso: bool = False) -> Usuario:
    usuario = Usuario(
        username=username,
        nombre=username.title(),
        hashed_password=hash_password("Clave123!"),
        rol=rol,
        activo=True,
        intentos_fallidos=0,
        acceso_auditoria=acceso,
    )
    db.add(usuario)
    db.flush()
    return usuario


@pytest.fixture
def cliente_de(db_session: Session) -> Generator:
    """Devuelve una fábrica de clientes autenticados con un token ya emitido para ``usuario``."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    def _fabrica(usuario: Usuario) -> TestClient:
        token = crear_access_token(usuario.id, usuario.username, usuario.rol)
        c = TestClient(app)
        c.headers.update({"Authorization": f"Bearer {token}"})
        return c

    yield _fabrica
    app.dependency_overrides.clear()


def _endpoints_auditoria(c: TestClient) -> list[int]:
    return [
        c.get("/api/v1/auditoria/casos", params={"q": "nadie"}).status_code,
        c.get("/api/v1/auditoria/casos/999999").status_code,
        c.post("/api/v1/auditoria/reportes", json=PERIODO).status_code,
        c.post("/api/v1/auditoria/reportes/descargar", json=PERIODO).status_code,
        c.get("/api/v1/audit-log").status_code,
    ]


def test_administrativo_sin_permiso_recibe_403(db_session: Session, cliente_de) -> None:
    c = cliente_de(_sembrar(db_session, "isidora_sin", "Administrativo"))
    assert _endpoints_auditoria(c) == [403, 403, 403, 403, 403]


def test_administrativo_con_permiso_lee_auditoria(db_session: Session, cliente_de) -> None:
    c = cliente_de(_sembrar(db_session, "isidora_con", "Administrativo", acceso=True))
    # La vista de un caso inexistente da 404 (pasó el control de acceso).
    assert _endpoints_auditoria(c) == [200, 404, 200, 200, 200]


def test_administrativo_con_permiso_mantiene_escritura_de_su_rol(
    db_session: Session, cliente_de
) -> None:
    """El permiso no le da gestión de usuarios (sigue siendo exclusiva de Coordinación)."""
    c = cliente_de(_sembrar(db_session, "isidora_rol", "Administrativo", acceso=True))
    assert c.get("/api/v1/usuarios").status_code == 403


def test_flag_en_otro_rol_no_da_acceso(db_session: Session, cliente_de) -> None:
    """Un rol que no es Administrativo ni de auditoría no gana acceso por el flag.

    Se fuerza el flag en BD (la API nunca lo guarda para otros roles) con un rol inventado
    para comprobar que la regla mira el rol, no solo el flag.
    """
    u = _sembrar(db_session, "otro_rol", "Administrativo", acceso=True)
    u.rol = "Invitado"
    db_session.flush()
    c = cliente_de(u)
    assert c.get("/api/v1/audit-log").status_code == 403


def test_cambio_de_flag_aplica_sin_token_nuevo(db_session: Session, cliente_de) -> None:
    usuario = _sembrar(db_session, "isidora_cambio", "Administrativo")
    c = cliente_de(usuario)
    assert c.post("/api/v1/auditoria/reportes", json=PERIODO).status_code == 403

    usuario.acceso_auditoria = True
    db_session.flush()
    assert c.post("/api/v1/auditoria/reportes", json=PERIODO).status_code == 200

    usuario.acceso_auditoria = False
    db_session.flush()
    assert c.post("/api/v1/auditoria/reportes", json=PERIODO).status_code == 403


def test_coordinacion_y_auditor_siguen_entrando(db_session: Session, cliente_de) -> None:
    for username, rol in (("coord_aud", "Coordinacion"), ("aud_aud", "Auditor"),
                          ("super_aud", "Superadmin")):
        c = cliente_de(_sembrar(db_session, username, rol))
        assert c.get("/api/v1/audit-log").status_code == 200, rol


# ── Gestión del permiso (usuarios) ─────────────────────────────────────────

def test_crear_administrativo_con_acceso_auditoria(as_coordinacion: TestClient) -> None:
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "isidora", "nombre": "Isidora", "password": "Clave123!",
              "rol": "Administrativo", "acceso_auditoria": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["acceso_auditoria"] is True
    listado = as_coordinacion.get("/api/v1/usuarios").json()
    assert next(u for u in listado if u["username"] == "isidora")["acceso_auditoria"] is True


def test_crear_sin_campo_queda_sin_acceso(as_coordinacion: TestClient) -> None:
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "sin_campo", "nombre": "X", "password": "Clave123!",
              "rol": "Administrativo"},
    )
    assert r.json()["acceso_auditoria"] is False


def test_acceso_auditoria_se_ignora_para_otros_roles(as_coordinacion: TestClient) -> None:
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "aud_flag", "nombre": "X", "password": "Clave123!",
              "rol": "Auditor", "acceso_auditoria": True},
    )
    assert r.status_code == 201
    assert r.json()["acceso_auditoria"] is False


def test_editar_flag_y_cambio_de_rol_lo_limpia(as_coordinacion: TestClient) -> None:
    uid = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "isi2", "nombre": "Isi", "password": "Clave123!",
              "rol": "Administrativo"},
    ).json()["id"]

    r = as_coordinacion.put(f"/api/v1/usuarios/{uid}", json={"acceso_auditoria": True})
    assert r.json()["acceso_auditoria"] is True

    # Editar otro campo sin mandar el flag lo conserva.
    r = as_coordinacion.put(f"/api/v1/usuarios/{uid}", json={"nombre": "Isidora"})
    assert r.json()["acceso_auditoria"] is True

    # Pasar a otro rol lo guarda en false.
    r = as_coordinacion.put(f"/api/v1/usuarios/{uid}", json={"rol": "Coordinacion"})
    assert r.json()["acceso_auditoria"] is False


def test_administrativo_no_puede_darse_el_permiso(as_admin: TestClient) -> None:
    r = as_admin.put("/api/v1/usuarios/1", json={"acceso_auditoria": True})
    assert r.status_code == 403


# ── Token ──────────────────────────────────────────────────────────────────

def test_login_incluye_acceso_auditoria_en_el_token(
    client: TestClient, db_session: Session
) -> None:
    _sembrar(db_session, "isidora_login", "Administrativo", acceso=True)
    r = client.post("/api/v1/auth/login",
                    json={"username": "isidora_login", "password": "Clave123!"})
    assert r.status_code == 200
    claims = decodificar_token(r.json()["access_token"], tipo_esperado="access")
    assert claims["acceso_auditoria"] is True
    refresh = jwt.decode(r.json()["refresh_token"], options={"verify_signature": False})
    assert refresh["acceso_auditoria"] is True
