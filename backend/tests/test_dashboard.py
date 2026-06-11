"""Tests — Task 2 EPIC-09: Dashboard multiprograma CEPA-090."""
import pytest
from datetime import date

from app.models.ingreso import Ingreso
from app.models.cita import Cita


# Campos obligatorios para Ingreso (excepto paciente_id y folio, que varían por test)
_ING_DEFAULTS = dict(
    folio_manual=True,
    tipo_derivacion="DIAT",
    tipo_ingreso="convenio",
    modelo_tratamiento="ambulatorio",
    diagnostico="Test diagnóstico",
)


# ── Fixtures de datos ─────────────────────────────────────────────────────────

@pytest.fixture
def datos_dashboard(db_session):
    """Crea ingresos y citas de prueba en dos programas distintos."""
    # Paciente dummy para FK (la sesión de test no tiene FKs reales enforced)
    from app.models.paciente import Paciente
    pac = Paciente(rut="11111111-1", nombre="Test Pac", sexo="F", edad=30, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing_a = Ingreso(
        **_ING_DEFAULTS,
        paciente_id=pac.id,
        folio="F-DASH-001",
        programa="DIEP",
        fecha_ingreso=date(2026, 1, 15), tipo_convenio="DIEP",
    )
    ing_b = Ingreso(
        **_ING_DEFAULTS,
        paciente_id=pac.id,
        folio="F-DASH-002",
        programa="DIAT",
        fecha_ingreso=date(2026, 2, 20), tipo_convenio="DIAT",
    )
    db_session.add_all([ing_a, ing_b])
    db_session.flush()

    cita1 = Cita(ingreso_id=ing_a.id, estado="realizada", fecha=date(2026, 1, 20))
    cita2 = Cita(ingreso_id=ing_a.id, estado="inasistencia", fecha=date(2026, 1, 27))
    cita3 = Cita(ingreso_id=ing_b.id, estado="anulada", fecha=date(2026, 2, 25))
    db_session.add_all([cita1, cita2, cita3])
    db_session.commit()
    return {"ingresos": [ing_a, ing_b], "citas": [cita1, cita2, cita3]}


# ── TC-090-01: dashboard sin filtros muestra todos los programas ──────────────

def test_dashboard_sin_filtros_agrega_todos_programas(as_coordinacion, datos_dashboard):
    resp = as_coordinacion.get("/api/v1/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] == 2
    assert body["total_atenciones"] >= 1
    assert body["total_inasistencias"] >= 1
    assert body["total_anulaciones"] >= 1


# ── TC-090-02: filtros combinados recalculan todos los indicadores ─────────────

def test_dashboard_filtros_combinados(as_coordinacion, datos_dashboard):
    resp = as_coordinacion.get("/api/v1/dashboard", params={
        "programa": "DIEP",
        "sexo": "F",
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-01-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] == 1
    assert body["filtros_aplicados"]["programa"] == "DIEP"


# ── TC-090-03: estado vacío cuando filtro sin coincidencias ──────────────────

def test_dashboard_filtros_sin_coincidencias(as_coordinacion, datos_dashboard):
    resp = as_coordinacion.get("/api/v1/dashboard", params={"comuna": "INEXISTENTE_XYZ"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] == 0
    assert body["total_atenciones"] == 0


# ── TC-090-04: Auditor accede en solo lectura ─────────────────────────────────

def test_dashboard_auditor_accede_solo_lectura(as_auditor, datos_dashboard):
    resp = as_auditor.get("/api/v1/dashboard")
    assert resp.status_code == 200


# ── Sin token → 401 ──────────────────────────────────────────────────────────

def test_dashboard_sin_auth_rechaza(client):
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 401
