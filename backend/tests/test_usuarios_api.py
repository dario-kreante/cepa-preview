from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.usuario import Usuario


def test_coordinacion_crea_usuario_administrativo(as_coordinacion: TestClient):
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "nuevo", "nombre": "Nuevo", "password": "Clave123!", "rol": "Administrativo"},
    )
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["username"] == "nuevo"
    assert cuerpo["rol"] == "Administrativo"
    assert cuerpo["activo"] is True
    assert "hashed_password" not in cuerpo  # nunca se expone el hash


def test_crear_usuario_rol_clinico_es_rechazado_422(as_coordinacion: TestClient):
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "x", "nombre": "X", "password": "Clave123!", "rol": "Clinico"},
    )
    assert r.status_code == 422  # el rol "Clinico" no existe (CEPA-002 CA-2)


def test_administrativo_no_puede_crear_usuarios_403(as_admin: TestClient):
    r = as_admin.post(
        "/api/v1/usuarios",
        json={"username": "x", "nombre": "X", "password": "Clave123!", "rol": "Administrativo"},
    )
    assert r.status_code == 403


def test_auditor_no_puede_crear_usuarios_403(as_auditor: TestClient):
    r = as_auditor.post(
        "/api/v1/usuarios",
        json={"username": "x", "nombre": "X", "password": "Clave123!", "rol": "Administrativo"},
    )
    assert r.status_code == 403


def test_coordinacion_lista_usuarios(as_coordinacion: TestClient):
    as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "u1", "nombre": "U1", "password": "Clave123!", "rol": "Administrativo"},
    )
    r = as_coordinacion.get("/api/v1/usuarios")
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "u1" in usernames


def test_coordinacion_desactiva_usuario_revoca_acceso(
    as_coordinacion: TestClient, db_session: Session
):
    create = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "rotativo", "nombre": "Rot", "password": "Clave123!", "rol": "Administrativo"},
    )
    uid = create.json()["id"]
    r = as_coordinacion.patch(f"/api/v1/usuarios/{uid}/desactivar")
    assert r.status_code == 200
    assert r.json()["activo"] is False
    usuario = db_session.get(Usuario, uid)
    db_session.refresh(usuario)
    assert usuario.activo is False


def test_alta_de_usuario_genera_traza_de_auditoria(
    as_coordinacion: TestClient, db_session: Session
):
    as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "auditado", "nombre": "A", "password": "Clave123!", "rol": "Auditor"},
    )
    trazas = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "usuario", AuditLog.action == "CREATE")
    ).all()
    assert any(t.actor == "coord_test" for t in trazas)


def test_alta_rotacion_crea_varios_usuarios_sin_limite(as_coordinacion: TestClient):
    for i in range(5):
        r = as_coordinacion.post(
            "/api/v1/usuarios",
            json={"username": f"adm{i}", "nombre": f"A{i}", "password": "Clave123!", "rol": "Administrativo"},
        )
        assert r.status_code == 201


def test_username_duplicado_devuelve_409(as_coordinacion: TestClient):
    payload = {"username": "dup", "nombre": "D", "password": "Clave123!", "rol": "Administrativo"}
    assert as_coordinacion.post("/api/v1/usuarios", json=payload).status_code == 201
    r = as_coordinacion.post("/api/v1/usuarios", json=payload)
    assert r.status_code == 409
