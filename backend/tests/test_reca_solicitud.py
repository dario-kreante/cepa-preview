"""Solicitud de RECA del caso de reintegro (QA-003, 18-11-2026; PRD v5 §7.4.2).

El estado se deriva: «pendiente» sin fecha de solicitud ni RECA, «solicitada» con fecha y sin
RECA, «recibida» cuando el caso tiene la RECA registrada.
"""

import datetime

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.services.reintegro import hoy_chile


def _caso(client, fecha_caso: str = "2026-04-01") -> int:
    ing = client.post(
        "/api/v1/ingresos",
        json={
            "rut": "14.963.452-5", "nombre": "Pedro Soto", "sexo": "M", "edad": 45, "region": "Biobío",
            "diagnostico": "DIAT rodilla", "tipo_derivacion": "DIAT", "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio", "fecha_ingreso": fecha_caso,
        },
    )
    assert ing.status_code == 201
    caso = client.post(
        "/api/v1/reintegros",
        json={
            "ingreso_id": ing.json()["id"], "rut": "14.963.452-5", "nombre": "Pedro Soto",
            "tipo_derivacion": "DIAT", "fecha_caso": fecha_caso, "sexo": "M", "edad": 45, "region": "Biobío",
        },
    )
    assert caso.status_code == 201
    return caso.json()["id"]


def _solicitar(client, caso_id: int, fecha: datetime.date | str):
    return client.patch(
        f"/api/v1/reintegros/{caso_id}/solicitud-reca", json={"fecha_solicitud_reca": str(fecha)}
    )


def _reca(client, caso_id: int):
    return client.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json={
            "fecha_reca": "2026-04-05", "tipo_reca": "AT", "numero_reca": "2026-AT-001",
            "razon_social": "Empresa SA", "solicita_medidas": False,
        },
    )


def test_caso_nuevo_esta_pendiente_sin_fecha(as_admin):
    caso_id = _caso(as_admin)

    body = as_admin.get(f"/api/v1/reintegros/{caso_id}").json()

    assert body["estado_solicitud_reca"] == "pendiente"
    assert body["fecha_solicitud_reca"] is None


def test_registrar_la_fecha_deja_el_caso_solicitada(as_admin):
    caso_id = _caso(as_admin)

    r = _solicitar(as_admin, caso_id, "2026-04-03")

    assert r.status_code == 200
    assert r.json()["estado_solicitud_reca"] == "solicitada"
    assert r.json()["fecha_solicitud_reca"] == "2026-04-03"


def test_con_reca_registrada_el_estado_es_recibida(as_admin):
    caso_id = _caso(as_admin)
    _solicitar(as_admin, caso_id, "2026-04-03")

    assert _reca(as_admin, caso_id).status_code == 201

    body = as_admin.get(f"/api/v1/reintegros/{caso_id}").json()
    assert body["estado_solicitud_reca"] == "recibida"
    assert body["fecha_solicitud_reca"] == "2026-04-03"  # el dato de la solicitud se conserva


def test_con_reca_y_sin_fecha_de_solicitud_tambien_es_recibida(as_admin):
    caso_id = _caso(as_admin)
    _reca(as_admin, caso_id)

    assert as_admin.get(f"/api/v1/reintegros/{caso_id}").json()["estado_solicitud_reca"] == "recibida"


def test_se_puede_corregir_la_fecha(as_coordinacion):
    caso_id = _caso(as_coordinacion)
    _solicitar(as_coordinacion, caso_id, "2026-04-03")

    r = _solicitar(as_coordinacion, caso_id, "2026-04-02")

    assert r.status_code == 200
    assert r.json()["fecha_solicitud_reca"] == "2026-04-02"


def test_la_fecha_de_hoy_es_valida(as_admin):
    caso_id = _caso(as_admin, fecha_caso=str(hoy_chile() - datetime.timedelta(days=3)))

    assert _solicitar(as_admin, caso_id, hoy_chile()).status_code == 200


def test_la_fecha_futura_se_rechaza(as_admin):
    caso_id = _caso(as_admin)

    r = _solicitar(as_admin, caso_id, hoy_chile() + datetime.timedelta(days=2))

    assert r.status_code == 422
    assert "futura" in r.json()["detail"]


def test_la_fecha_anterior_a_la_del_caso_se_rechaza(as_admin):
    caso_id = _caso(as_admin, fecha_caso="2026-04-10")

    r = _solicitar(as_admin, caso_id, "2026-04-09")

    assert r.status_code == 422
    assert "10-04-2026" in r.json()["detail"]


def test_la_fecha_del_mismo_dia_del_caso_es_valida(as_admin):
    caso_id = _caso(as_admin, fecha_caso="2026-04-10")

    assert _solicitar(as_admin, caso_id, "2026-04-10").status_code == 200


def test_sin_fecha_en_el_cuerpo_es_422(as_admin):
    caso_id = _caso(as_admin)

    assert as_admin.patch(f"/api/v1/reintegros/{caso_id}/solicitud-reca", json={}).status_code == 422


def test_caso_inexistente_es_404(as_admin):
    assert _solicitar(as_admin, 999999, "2026-04-03").status_code == 404


def test_el_auditor_no_puede_registrar(as_admin, as_auditor):
    caso_id = _caso(as_admin)

    assert _solicitar(as_auditor, caso_id, "2026-04-03").status_code == 403
    assert as_auditor.get(f"/api/v1/reintegros/{caso_id}").status_code == 200


def test_sin_sesion_es_401(client):
    assert _solicitar(client, 1, "2026-04-03").status_code in (401, 403)


def test_el_cambio_queda_en_la_auditoria(as_admin, db_session):
    caso_id = _caso(as_admin)
    _solicitar(as_admin, caso_id, "2026-04-03")
    _solicitar(as_admin, caso_id, "2026-04-02")

    trazas = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity == "caso_reintegro", AuditLog.entity_id == str(caso_id), AuditLog.action == "UPDATE")
        .order_by(AuditLog.id)
    ).all()
    assert [(t.actor, t.valor_anterior, t.valor_nuevo) for t in trazas] == [
        ("admin_test", None, "fecha_solicitud_reca=2026-04-03"),
        ("admin_test", "fecha_solicitud_reca=2026-04-03", "fecha_solicitud_reca=2026-04-02"),
    ]


def test_una_fecha_rechazada_no_deja_traza_ni_cambia_el_caso(as_admin, db_session):
    caso_id = _caso(as_admin)
    antes = db_session.scalar(select(AuditLog.id).order_by(AuditLog.id.desc()).limit(1))

    _solicitar(as_admin, caso_id, hoy_chile() + datetime.timedelta(days=5))

    despues = db_session.scalar(select(AuditLog.id).order_by(AuditLog.id.desc()).limit(1))
    assert antes == despues
    assert as_admin.get(f"/api/v1/reintegros/{caso_id}").json()["fecha_solicitud_reca"] is None


def test_el_listado_trae_el_estado(as_admin):
    caso_id = _caso(as_admin)
    _solicitar(as_admin, caso_id, "2026-04-03")

    [fila] = [c for c in as_admin.get("/api/v1/reintegros").json() if c["id"] == caso_id]

    assert fila["estado_solicitud_reca"] == "solicitada"

