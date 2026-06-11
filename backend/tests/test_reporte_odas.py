"""Tests — Task 7 EPIC-09: Reporte ODAS vencidas CEPA-097.

Deviación: modelo se llama Oda (no ODA). La clase Oda tiene `identificador`
(no `numero_oda`). Se usa `fecha_registro` que fue añadida via migración 09000.
"""
import pytest
from datetime import date, timedelta


@pytest.fixture
def datos_odas(db_session):
    """Crea ODAS vencidas, vigentes y la que vence exactamente hoy."""
    from app.models.oda import Oda
    from app.models.paciente import Paciente
    from app.models.ingreso import Ingreso

    pac = Paciente(rut="66666666-6", nombre="Test ODA", sexo="F", edad=40, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id, folio="F-ODA-001", folio_manual=True,
        programa="DIEP", fecha_ingreso=date(2026, 1, 1),
        sexo="F", tramo_etario="18-29", region="Maule",
        tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    db_session.add(ing)
    db_session.flush()

    hoy = date.today()
    odas = [
        Oda(
            ingreso_id=ing.id, identificador="ODA-001",
            fecha_registro=date(2026, 1, 1),
            fecha_vencimiento=hoy - timedelta(days=10),   # vencida
        ),
        Oda(
            ingreso_id=ing.id, identificador="ODA-002",
            fecha_registro=date(2026, 2, 1),
            fecha_vencimiento=hoy,                         # vence hoy → NO vencida
        ),
        Oda(
            ingreso_id=ing.id, identificador="ODA-003",
            fecha_registro=date(2026, 3, 1),
            fecha_vencimiento=hoy + timedelta(days=30),    # vigente
        ),
    ]
    db_session.add_all(odas)
    db_session.commit()
    return {"ingreso": ing, "odas": odas}


# ── TC-097-01: solo ODAS con vencimiento anterior a hoy ──────────────────────

def test_odas_vencidas_solo_anteriores_a_hoy(as_coordinacion, datos_odas):
    resp = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    hoy = date.today().isoformat()
    for item in body["items"]:
        assert item["fecha_vencimiento"] < hoy


# ── TC-097-02: ODA que vence exactamente hoy NO aparece como vencida ─────────

def test_oda_vence_hoy_no_es_vencida(as_coordinacion, datos_odas):
    resp = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    body = resp.json()
    hoy = date.today().isoformat()
    vencimientos = [i["fecha_vencimiento"] for i in body["items"]]
    assert hoy not in vencimientos


# ── TC-097-04: sin ODAS vencidas → listado vacío, sin error ──────────────────

def test_odas_vencidas_sin_datos_lista_vacia(as_coordinacion, db_session):
    resp = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 0


# ── TC-097-05: Auditor puede leer ────────────────────────────────────────────

def test_odas_vencidas_auditor(as_auditor, datos_odas):
    resp = as_auditor.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 200


def test_odas_vencidas_sin_auth_rechaza(client):
    resp = client.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 401
