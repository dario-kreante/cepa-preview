"""Tests — Task 3 EPIC-09: Reportes operativos CEPA-091."""
import pytest
from datetime import date

from app.models.paciente import Paciente


@pytest.fixture
def datos_operativos(db_session):
    from app.models.ingreso import Ingreso
    from app.models.cita import Cita

    pac = Paciente(rut="22222222-2", nombre="Test Op", sexo="F", edad=25, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id, folio="F-OP-001", folio_manual=True,
        programa="DIEP", fecha_ingreso=date(2026, 3, 1),
        tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    db_session.add(ing)
    db_session.flush()

    citas = [
        Cita(ingreso_id=ing.id, estado="realizada",    fecha=date(2026, 3, 5)),
        Cita(ingreso_id=ing.id, estado="inasistencia", fecha=date(2026, 3, 12)),
        Cita(ingreso_id=ing.id, estado="anulada",      fecha=date(2026, 3, 19)),
        Cita(ingreso_id=ing.id, estado="agendada",     fecha=date(2026, 3, 26)),
    ]
    db_session.add_all(citas)
    db_session.commit()


# ── TC-091-01: cifras correctas de citas/atenciones/inasistencias/anulaciones ─

def test_reporte_operativo_cifras_correctas(as_coordinacion, datos_operativos):
    resp = as_coordinacion.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["totales"]["realizadas"] >= 1
    assert body["totales"]["inasistencias"] >= 1
    assert body["totales"]["anuladas"] >= 1


# ── TC-091-03: período vacío → 422 ────────────────────────────────────────────

def test_reporte_operativo_sin_periodo_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/reportes/operativo")
    assert resp.status_code == 422


# ── TC-091-04: período sin actividad → reporte con totales en cero ───────────

def test_reporte_operativo_periodo_sin_datos(as_coordinacion, datos_operativos):
    resp = as_coordinacion.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2020-01-01",
        "fecha_hasta": "2020-01-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["totales"]["realizadas"] == 0
    assert body["totales"]["inasistencias"] == 0
    assert body["totales"]["anuladas"] == 0


# ── TC-091-05: Auditor accede ─────────────────────────────────────────────────

def test_reporte_operativo_auditor_accede(as_auditor, datos_operativos):
    resp = as_auditor.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp.status_code == 200


def test_reporte_operativo_sin_auth_rechaza(client):
    resp = client.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp.status_code == 401
