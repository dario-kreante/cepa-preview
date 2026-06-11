"""Tests — Task 4 EPIC-09: Reporte cumplimiento por convenio CEPA-092."""
import pytest
from datetime import date


@pytest.fixture
def datos_convenio(db_session):
    from app.models.paciente import Paciente
    from app.models.ingreso import Ingreso
    from app.models.cita import Cita

    pac = Paciente(rut="33333333-3", nombre="Test Conv", sexo="F", edad=30, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id, folio="F-CONV-001", folio_manual=True,
        programa="DIEP", tipo_convenio="DIEP",
        fecha_ingreso=date(2026, 4, 1),
        tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    db_session.add(ing)
    db_session.flush()
    citas = [
        Cita(ingreso_id=ing.id, estado="realizada",    fecha=date(2026, 4, 5)),
        Cita(ingreso_id=ing.id, estado="inasistencia", fecha=date(2026, 4, 10)),
    ]
    db_session.add_all(citas)
    db_session.commit()
    return ing


# ── TC-092-01: reporte de cumplimiento generado con indicadores del período ───

def test_reporte_convenio_genera_con_indicadores(as_coordinacion, datos_convenio):
    resp = as_coordinacion.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "DIEP",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["convenio"] == "DIEP"
    assert len(body["items"]) >= 1
    assert body["items"][0]["total_atenciones"] >= 1


# ── TC-092-04: convenio sin actividad → totales en cero ──────────────────────

def test_reporte_convenio_sin_actividad_totales_cero(as_coordinacion, datos_convenio):
    resp = as_coordinacion.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "PARTICULAR",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 200
    body = resp.json()
    total = sum(i["total_atenciones"] for i in body.get("items", []))
    assert total == 0


# ── TC-092-05: Auditor puede leer ─────────────────────────────────────────────

def test_reporte_convenio_auditor_puede_leer(as_auditor, datos_convenio):
    resp = as_auditor.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "DIEP",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 200


def test_reporte_convenio_sin_auth_rechaza(client):
    resp = client.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "DIEP",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 401
