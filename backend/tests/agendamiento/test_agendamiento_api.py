"""Tests de API para el módulo de agendamiento.

Cubre CA-8 (permisos por rol), CA-1 (propuesta diaria), CA-7 (confirmación).
"""

from fastapi.testclient import TestClient


HOY_HABIL = "2026-07-07"  # martes


def test_generar_propuesta_requiere_autenticacion(client: TestClient):
    """CA-8: sin token → 401."""
    resp = client.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 401


def test_generar_propuesta_auditor_denegado(as_auditor: TestClient):
    """CA-8: Auditor no puede generar propuesta → 403."""
    resp = as_auditor.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 403


def test_generar_propuesta_admin_permitido(as_admin: TestClient):
    """CA-8 / CA-1: Administrativo puede generar propuesta → 201."""
    resp = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipo"] == "diaria"
    assert body["estado"] == "borrador"
    assert "id" in body


def test_generar_propuesta_coordinacion_permitido(as_coordinacion: TestClient):
    """CA-8: Coordinacion puede generar propuesta → 201."""
    resp = as_coordinacion.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 2, "tipo": "semanal", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 201


def test_listar_propuestas_auditor_puede_leer(as_auditor: TestClient):
    """CA-8: Auditor puede listar propuestas (solo lectura) → 200."""
    resp = as_auditor.get("/api/v1/propuestas-agenda")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_obtener_propuesta_por_id_admin(as_admin: TestClient):
    """Crear y luego recuperar por ID."""
    create = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 3, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert create.status_code == 201
    pid = create.json()["id"]

    get_resp = as_admin.get(f"/api/v1/propuestas-agenda/{pid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == pid


def test_obtener_propuesta_inexistente_404(as_admin: TestClient):
    resp = as_admin.get("/api/v1/propuestas-agenda/999999")
    assert resp.status_code == 404


def test_confirmar_citas_auditor_denegado(as_admin: TestClient, as_auditor: TestClient):
    """CA-8: Auditor no puede confirmar citas → 403."""
    create = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 4, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    pid = create.json()["id"]
    resp = as_auditor.post(f"/api/v1/propuestas-agenda/{pid}/confirmar", json={"cita_ids": [1]})
    assert resp.status_code == 403


def test_confirmar_citas_propuesta_inexistente_404(as_admin: TestClient):
    resp = as_admin.post("/api/v1/propuestas-agenda/999999/confirmar", json={"cita_ids": [1]})
    assert resp.status_code == 404


def test_crear_disponibilidad_admin(as_admin: TestClient):
    """El Administrativo puede crear disponibilidad de profesional."""
    resp = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 10, "dia_semana": 1, "cupo_diario": 6
    })
    assert resp.status_code == 201
    assert resp.json()["cupo_diario"] == 6


def test_crear_disponibilidad_fin_de_semana_422(as_admin: TestClient):
    """dia_semana=6 (sábado) → error de validación 422."""
    resp = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 10, "dia_semana": 6, "cupo_diario": 5
    })
    assert resp.status_code == 422
