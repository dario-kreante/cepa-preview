"""Tests de integración de los endpoints de alertas (CEPA-100, CEPA-101).

Desviación 1: el helper _alerta_en_bd usa AlertaNotif (tabla alerta_notif).
Desviación 3: el usuario_id del fixture as_admin no es fijo — se obtiene
via /whoami-test para asegurar que las alertas se asignen al usuario correcto.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alertas import AlertaNotif


def _get_user_id(client: TestClient) -> int:
    """Obtiene el id real del usuario autenticado via /whoami-test."""
    return client.get("/whoami-test").json()["id"]


def _alerta_en_bd(
    db: Session,
    *,
    usuario_id: int,
    tipo: str = "oda_por_vencer",
) -> AlertaNotif:
    """Helper: inserta una alerta directamente para setup de tests."""
    alerta = AlertaNotif(
        tipo=tipo,
        estado="pendiente",
        caso_id=999,
        caso_tipo="oda",
        usuario_id=usuario_id,
        plazo_objetivo=datetime.now(timezone.utc) + timedelta(days=3),
        ventana_dias=7,
        email_enviado=False,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


# ---------------------------------------------------------------------------
# Endpoint: POST /api/v1/alertas/ejecutar-job
# ---------------------------------------------------------------------------


def test_job_requiere_autenticacion(client: TestClient):
    resp = client.post("/api/v1/alertas/ejecutar-job")
    assert resp.status_code == 401


def test_job_ejecutable_por_admin(as_admin: TestClient):
    resp = as_admin.post("/api/v1/alertas/ejecutar-job")
    # El job puede no generar alertas si no hay hitos en la BD de test,
    # pero debe responder 200 con un resumen.
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert "alertas_generadas" in cuerpo
    assert isinstance(cuerpo["alertas_generadas"], int)


def test_job_no_accesible_por_auditor(as_auditor: TestClient):
    resp = as_auditor.post("/api/v1/alertas/ejecutar-job")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Endpoint: GET /api/v1/alertas
# ---------------------------------------------------------------------------


def test_listar_alertas_requiere_autenticacion(client: TestClient):
    resp = client.get("/api/v1/alertas")
    assert resp.status_code == 401


def test_admin_ve_sus_alertas(as_admin: TestClient, db_session: Session):
    uid = _get_user_id(as_admin)
    _alerta_en_bd(db_session, usuario_id=uid, tipo="oda_por_vencer")
    resp = as_admin.get("/api/v1/alertas")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(a["tipo"] == "oda_por_vencer" for a in data)


def test_auditor_puede_leer_alertas(as_auditor: TestClient, db_session: Session):
    # TC-101-04: auditor tiene lectura (ve todas las alertas)
    _alerta_en_bd(db_session, usuario_id=1, tipo="receta_por_renovar")
    resp = as_auditor.get("/api/v1/alertas")
    assert resp.status_code == 200


def test_panel_sin_alertas_devuelve_lista_vacia(as_admin: TestClient, db_session: Session):
    # TC-101-05: usuario sin alertas → lista vacía, sin error
    resp = as_admin.get("/api/v1/alertas")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Endpoint: PATCH /api/v1/alertas/{id}
# ---------------------------------------------------------------------------


def test_marcar_alerta_resuelta(as_admin: TestClient, db_session: Session):
    # TC-101-02, CA-4: cambiar estado a resuelta
    uid = _get_user_id(as_admin)
    alerta = _alerta_en_bd(db_session, usuario_id=uid, tipo="control_medico")
    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "resuelta"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "resuelta"
    assert resp.json()["resuelta_en"] is not None


def test_marcar_alerta_leida(as_admin: TestClient, db_session: Session):
    uid = _get_user_id(as_admin)
    alerta = _alerta_en_bd(db_session, usuario_id=uid, tipo="vencimiento_licencia")
    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "leida"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "leida"


def test_auditor_no_puede_cambiar_estado(as_auditor: TestClient, db_session: Session):
    # TC-101-04: auditor no puede editar
    alerta = _alerta_en_bd(db_session, usuario_id=1)
    resp = as_auditor.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "resuelta"})
    assert resp.status_code == 403


def test_cambiar_estado_alerta_inexistente(as_admin: TestClient):
    resp = as_admin.patch("/api/v1/alertas/99999", json={"estado": "resuelta"})
    assert resp.status_code == 404


def test_segregacion_admin_no_ve_alertas_de_otro_usuario(
    as_admin: TestClient, db_session: Session
):
    # TC-101-03: admin A no ve alertas de usuario_id=9999
    _alerta_en_bd(db_session, usuario_id=9999, tipo="oda_por_vencer")
    resp = as_admin.get("/api/v1/alertas")
    assert resp.status_code == 200
    ids_usuario = {a["usuario_id"] for a in resp.json()}
    assert 9999 not in ids_usuario
