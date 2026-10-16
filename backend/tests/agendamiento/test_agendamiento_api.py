"""Tests de API para el módulo de agendamiento.

Cubre CA-8 (permisos por rol), el historial de propuestas y la disponibilidad. La generación y
confirmación de propuestas se retiró: las horas se agendan en SALUTEM.
"""

from datetime import date

from fastapi.testclient import TestClient

from app.agendamiento.models import PropuestaAgenda


HOY_HABIL = "2026-07-07"  # martes


def test_generar_y_confirmar_propuesta_retirados(as_admin: TestClient):
    """SALUTEM es la agenda real: ya no se generan ni se confirman propuestas desde el SIGE."""
    generar = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert generar.status_code in (404, 405)
    confirmar = as_admin.post("/api/v1/propuestas-agenda/1/confirmar", json={"cita_ids": [1]})
    assert confirmar.status_code in (404, 405)


def test_listar_propuestas_auditor_puede_leer(as_auditor: TestClient):
    """CA-8: Auditor puede listar propuestas (solo lectura) → 200."""
    resp = as_auditor.get("/api/v1/propuestas-agenda")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_obtener_propuesta_por_id_admin(as_admin: TestClient, db_session):
    """El historial de propuestas sigue disponible para lectura."""
    propuesta = PropuestaAgenda(
        profesional_id=3, tipo="diaria", fecha_inicio=date(2026, 7, 7),
        fecha_fin=date(2026, 7, 7), estado="borrador", generado_por="test",
    )
    db_session.add(propuesta)
    db_session.commit()

    get_resp = as_admin.get(f"/api/v1/propuestas-agenda/{propuesta.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == propuesta.id


def test_obtener_propuesta_inexistente_404(as_admin: TestClient):
    resp = as_admin.get("/api/v1/propuestas-agenda/999999")
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


def test_disponibilidad_mismo_dia_reemplaza(as_admin: TestClient):
    """Dos altas para el mismo profesional y día dejan una sola fila con el último cupo."""
    primera = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 11, "dia_semana": 1, "cupo_diario": 3
    })
    assert primera.status_code == 201
    segunda = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 11, "dia_semana": 1, "cupo_diario": 5
    })
    assert segunda.status_code == 201
    assert segunda.json()["id"] == primera.json()["id"]

    listado = as_admin.get("/api/v1/disponibilidad-profesional/11")
    assert listado.status_code == 200
    filas = listado.json()
    assert len(filas) == 1
    assert filas[0]["cupo_diario"] == 5


def test_disponibilidad_delete_la_saca_del_listado(as_admin: TestClient):
    """DELETE da de baja el día (204) y deja de aparecer en el listado."""
    alta = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 12, "dia_semana": 2, "cupo_diario": 4
    })
    assert alta.status_code == 201
    dp_id = alta.json()["id"]

    resp = as_admin.delete(f"/api/v1/disponibilidad-profesional/{dp_id}")
    assert resp.status_code == 204
    assert resp.content == b""

    listado = as_admin.get("/api/v1/disponibilidad-profesional/12")
    assert listado.status_code == 200
    assert listado.json() == []


def test_disponibilidad_delete_inexistente_404(as_admin: TestClient):
    resp = as_admin.delete("/api/v1/disponibilidad-profesional/999999")
    assert resp.status_code == 404


def test_disponibilidad_delete_auditor_403(as_admin: TestClient, as_auditor: TestClient):
    """CA-8: Auditor no puede dar de baja disponibilidad → 403."""
    alta = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 13, "dia_semana": 3, "cupo_diario": 2
    })
    dp_id = alta.json()["id"]
    resp = as_auditor.delete(f"/api/v1/disponibilidad-profesional/{dp_id}")
    assert resp.status_code == 403
