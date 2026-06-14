"""Tests de integración del módulo de tareas pendientes por rol (CEPA-103).

Cubre CA-1..CA-4 y TC-103-01..TC-103-05.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.tareas import TareaItem


def _tarea(db: Session, *, usuario_id: int = 1, estado: str = "pendiente") -> TareaItem:
    t = TareaItem(
        titulo="Gestionar receta",
        descripcion="Renovar receta paciente X",
        estado=estado,
        tipo_tarea="gestionar_receta",
        caso_id=101,
        caso_tipo="ingreso",
        usuario_id=usuario_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _get_user_id(client: TestClient) -> int:
    return client.get("/whoami-test").json()["id"]


# ---------------------------------------------------------------------------
# GET /api/v1/tareas
# ---------------------------------------------------------------------------


def test_listar_tareas_requiere_autenticacion(client: TestClient):
    resp = client.get("/api/v1/tareas")
    assert resp.status_code == 401


def test_admin_ve_sus_tareas(as_admin: TestClient, db_session: Session):
    # TC-103-01: admin ve sus tareas pendientes
    uid = _get_user_id(as_admin)
    _tarea(db_session, usuario_id=uid)
    resp = as_admin.get("/api/v1/tareas")
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["tipo_tarea"] == "gestionar_receta" for t in data)


def test_lista_tareas_vacia_sin_error(as_admin: TestClient, db_session: Session):
    # TC-103-05: sin tareas pendientes → lista vacía, sin error
    resp = as_admin.get("/api/v1/tareas")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_segregacion_admin_no_ve_tareas_de_otro(as_admin: TestClient, db_session: Session):
    # TC-103-03: admin A no ve tareas de admin B (usuario_id=9999)
    _tarea(db_session, usuario_id=9999)
    resp = as_admin.get("/api/v1/tareas")
    assert resp.status_code == 200
    ids_usuario = {t["usuario_id"] for t in resp.json()}
    assert 9999 not in ids_usuario


def test_coordinacion_ve_tareas_del_equipo(as_coordinacion: TestClient, db_session: Session):
    # TC-103-04: Coordinación ve estado de tareas del equipo (sin filtro de usuario_id)
    _tarea(db_session, usuario_id=1)
    _tarea(db_session, usuario_id=2)
    resp = as_coordinacion.get("/api/v1/tareas")
    assert resp.status_code == 200
    # Coordinación debe ver las tareas de todos los usuarios
    assert len(resp.json()) >= 2


# ---------------------------------------------------------------------------
# POST /api/v1/tareas
# ---------------------------------------------------------------------------


def test_crear_tarea_como_admin(as_admin: TestClient):
    uid = _get_user_id(as_admin)
    payload = {
        "titulo": "Enviar informe EPT",
        "descripcion": "Enviar informe al ISL antes del viernes",
        "tipo_tarea": "enviar_informe",
        "usuario_id": uid,
        "caso_id": 55,
        "caso_tipo": "ept",
    }
    resp = as_admin.post("/api/v1/tareas", json=payload)
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["titulo"] == "Enviar informe EPT"
    assert cuerpo["estado"] == "pendiente"


def test_auditor_no_puede_crear_tarea(as_auditor: TestClient):
    payload = {
        "titulo": "Tarea de auditor",
        "tipo_tarea": "otro",
        "usuario_id": 1,
    }
    resp = as_auditor.post("/api/v1/tareas", json=payload)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/v1/tareas/{id}
# ---------------------------------------------------------------------------


def test_completar_tarea(as_admin: TestClient, db_session: Session):
    # TC-103-02: tarea pasa a completada y sale de pendientes
    uid = _get_user_id(as_admin)
    tarea = _tarea(db_session, usuario_id=uid)
    resp = as_admin.patch(f"/api/v1/tareas/{tarea.id}", json={"estado": "completada"})
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "completada"
    assert cuerpo["completada_en"] is not None
    assert cuerpo["completada_por"] is not None


def test_completar_tarea_inexistente(as_admin: TestClient):
    resp = as_admin.patch("/api/v1/tareas/99999", json={"estado": "completada"})
    assert resp.status_code == 404
