from fastapi.testclient import TestClient


def test_crear_y_listar_audit_log(client: TestClient):
    payload = {
        "actor": "maria.garcia",
        "action": "CREATE",
        "entity": "ingreso",
        "entity_id": "F-2026-0001",
    }
    create = client.post("/api/v1/audit-log", json=payload)
    assert create.status_code == 201
    cuerpo = create.json()
    assert cuerpo["id"] >= 1
    assert cuerpo["actor"] == "maria.garcia"
    assert cuerpo["created_at"] is not None

    listado = client.get("/api/v1/audit-log")
    assert listado.status_code == 200
    actores = [item["actor"] for item in listado.json()]
    assert "maria.garcia" in actores


def test_entity_id_es_opcional(client: TestClient):
    payload = {"actor": "sistema", "action": "LOGIN", "entity": "sesion"}
    create = client.post("/api/v1/audit-log", json=payload)
    assert create.status_code == 201
    assert create.json()["entity_id"] is None
