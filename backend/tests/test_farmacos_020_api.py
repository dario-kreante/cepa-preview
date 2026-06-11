"""Tests de CEPA-020: registro farmacológico vinculado al folio.

Fixtures as_admin / as_coordinacion / as_auditor provienen de EPIC-00 conftest.
Se necesita un ingreso previo: helper _crear_ingreso() lo hace vía API de EPIC-01.
"""
import pytest


def _crear_ingreso(client) -> int:
    """Crea un ingreso via API y devuelve su id."""
    payload = {
        "rut": "12.345.678-5",
        "nombre": "Paciente Test",
        "sexo": "F",
        "edad": 35,
        "region": "Maule",
        "diagnostico": "Trastorno adaptativo",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-10",
    }
    r = client.post("/api/v1/ingresos", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _payload_reg(ingreso_id: int, **over) -> dict:
    base = {
        "ingreso_id": ingreso_id,
        "medico_tratante": "Dr. González",
        "estado_farmacologico": "activo",
    }
    base.update(over)
    return base


# TC-020-01
def test_crear_registro_farmacologico_vinculado_al_folio(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["ingreso_id"] == ingreso_id
    assert cuerpo["medico_tratante"] == "Dr. González"
    assert cuerpo["estado_farmacologico"] == "activo"
    assert cuerpo["activo"] is True


# TC-020-02: lectura devuelve el registro
def test_obtener_registro_por_ingreso_id(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}")
    assert r.status_code == 200
    assert r.json()["ingreso_id"] == ingreso_id


# TC-020-03: campos obligatorios ausentes -> 422 (sin folio es error de Pydantic)
def test_crear_sin_medico_tratante_rechazado(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json={"ingreso_id": ingreso_id, "estado_farmacologico": "activo"},
    )
    assert r.status_code == 422
    assert "medico_tratante" in r.text


def test_crear_sin_estado_rechazado(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json={"ingreso_id": ingreso_id, "medico_tratante": "Dr. X"},
    )
    assert r.status_code == 422
    assert "estado_farmacologico" in r.text


# TC-020-03b: estado inválido -> 422
def test_estado_invalido_rechazado(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json=_payload_reg(ingreso_id, estado_farmacologico="inventado"),
    )
    assert r.status_code == 422


# TC-020-04: folio ya tiene registro activo → se reactiva (no duplica)
def test_reingreso_mismo_folio_reactiva_registro(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r1 = as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r1.status_code == 201
    id1 = r1.json()["id"]
    # segundo intento para el mismo ingreso → debe devolver el mismo registro reactivado
    r2 = as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r2.status_code == 200  # reactivación, no 201
    assert r2.json()["id"] == id1
    assert r2.json()["activo"] is True


# TC-020-05: Auditor no puede crear → 403
def test_auditor_no_puede_crear_registro(as_auditor, as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_auditor.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r.status_code == 403


# TC-020-05b: Auditor sí puede leer → 200
def test_auditor_puede_leer_registro(as_auditor, as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}")
    assert r.status_code == 200


# Ingreso inexistente → 404
def test_ingreso_inexistente_devuelve_404(as_admin):
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json=_payload_reg(999999),
    )
    assert r.status_code == 404
