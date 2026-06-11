from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audit.service import record_audit


def _sembrar_trazas(db: Session) -> None:
    record_audit(db, actor="maria", rol="Coordinacion", action="CREATE", entity="ingreso", entity_id="F1")
    record_audit(db, actor="juan", rol="Administrativo", action="UPDATE", entity="farmaco", entity_id="X9")
    record_audit(db, actor="maria", rol="Coordinacion", action="DELETE", entity="ingreso", entity_id="F2")
    db.flush()


def test_auditor_puede_listar_el_log(as_auditor: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_auditor.get("/api/v1/audit-log")
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_coordinacion_puede_listar_el_log(as_coordinacion: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_coordinacion.get("/api/v1/audit-log")
    assert r.status_code == 200


def test_administrativo_no_puede_ver_el_log_403(as_admin: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_admin.get("/api/v1/audit-log")
    assert r.status_code == 403


def test_sin_token_el_log_devuelve_401(client: TestClient):
    assert client.get("/api/v1/audit-log").status_code == 401


def test_filtro_por_actor(as_auditor: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_auditor.get("/api/v1/audit-log", params={"actor": "maria"})
    assert r.status_code == 200
    assert all(t["actor"] == "maria" for t in r.json())
    assert len(r.json()) == 2


def test_filtro_por_entity_y_action(as_auditor: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_auditor.get("/api/v1/audit-log", params={"entity": "ingreso", "action": "DELETE"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["entity_id"] == "F2"


def test_no_existe_endpoint_para_crear_trazas_via_api(as_coordinacion: TestClient):
    # El POST público fue retirado; las trazas solo nacen vía record_audit (inmutabilidad/append-only).
    r = as_coordinacion.post(
        "/api/v1/audit-log",
        json={"actor": "x", "action": "CREATE", "entity": "y"},
    )
    assert r.status_code in (404, 405)


def test_no_existe_endpoint_para_borrar_trazas_via_api(as_coordinacion: TestClient):
    r = as_coordinacion.delete("/api/v1/audit-log/1")
    assert r.status_code in (404, 405)
