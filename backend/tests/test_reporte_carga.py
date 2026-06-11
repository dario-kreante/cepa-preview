"""Tests — Task 5 EPIC-09: Reporte carga laboral CEPA-093."""
import pytest
from datetime import date


@pytest.fixture
def datos_carga(db_session):
    from app.models.paciente import Paciente
    from app.models.ingreso import Ingreso

    pac = Paciente(rut="44444444-4", nombre="Test Carga", sexo="F", edad=30, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ingresos = [
        Ingreso(
            paciente_id=pac.id, folio="F-CRG-001", folio_manual=True,
            programa="DIEP", profesional_id=10, especialidad="psicologia",
            fecha_ingreso=date(2026, 5, 1), sexo="F", tramo_etario="18-29",
            tipo_derivacion="DIAT", tipo_ingreso="convenio",
            modelo_tratamiento="ambulatorio", diagnostico="Test",
        ),
        Ingreso(
            paciente_id=pac.id, folio="F-CRG-002", folio_manual=True,
            programa="DIAT", profesional_id=10, especialidad="psicologia",
            fecha_ingreso=date(2026, 5, 3), sexo="M", tramo_etario="30-44",
            tipo_derivacion="DIAT", tipo_ingreso="convenio",
            modelo_tratamiento="ambulatorio", diagnostico="Test",
        ),
        Ingreso(
            paciente_id=pac.id, folio="F-CRG-003", folio_manual=True,
            programa="DIEP", profesional_id=20, especialidad="medicina",
            fecha_ingreso=date(2026, 5, 5), sexo="F", tramo_etario="45-59",
            tipo_derivacion="DIAT", tipo_ingreso="convenio",
            modelo_tratamiento="ambulatorio", diagnostico="Test",
        ),
    ]
    db_session.add_all(ingresos)
    db_session.commit()
    return ingresos


# ── TC-093-01: carga correcta por profesional ─────────────────────────────────

def test_carga_laboral_correcta_por_profesional(as_coordinacion, datos_carga):
    resp = as_coordinacion.get("/api/v1/reportes/carga-laboral", params={
        "fecha_desde": "2026-05-01",
        "fecha_hasta": "2026-05-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    ids = [i["profesional_id"] for i in body["items"]]
    assert 10 in ids
    assert 20 in ids
    prof10 = next(i for i in body["items"] if i["profesional_id"] == 10)
    assert prof10["total_casos"] == 2


# ── TC-093-03: período sin datos → lista vacía ───────────────────────────────

def test_carga_laboral_periodo_sin_datos(as_coordinacion, datos_carga):
    resp = as_coordinacion.get("/api/v1/reportes/carga-laboral", params={
        "fecha_desde": "2020-01-01",
        "fecha_hasta": "2020-01-31",
    })
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── TC-093-04: sin período → 422 ─────────────────────────────────────────────

def test_carga_laboral_sin_periodo_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/reportes/carga-laboral")
    assert resp.status_code == 422


# ── TC-093-05: Auditor accede en solo lectura ─────────────────────────────────

def test_carga_laboral_auditor(as_auditor, datos_carga):
    resp = as_auditor.get("/api/v1/reportes/carga-laboral", params={
        "fecha_desde": "2026-05-01",
        "fecha_hasta": "2026-05-31",
    })
    assert resp.status_code == 200
