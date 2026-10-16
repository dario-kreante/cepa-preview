"""Tests DD-1 (EPIC-09 rework): citas reales en la tabla de hechos + PATCH estado.

Cubre:
  TC-DD1-02: PATCH /citas/{id}/estado transiciona agendada → realizada correctamente.
  TC-DD1-03: PATCH transición inválida devuelve 409.
  TC-DD1-04: integración Cita agendada → PATCH realizada → reporte operativo.
  (TC-DD1-01, confirmar una propuesta crea la Cita, se retiró con la confirmación de propuestas.)
"""
import pytest
from datetime import date

from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def paciente_con_ingreso(db_session):
    pac = Paciente(
        rut="88888888-8", nombre="Test DD1", sexo="M", edad=35, region="Maule"
    )
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id,
        folio="F-DD1-001",
        folio_manual=True,
        programa="DIEP",
        tipo_convenio="DIEP",
        fecha_ingreso=date(2026, 1, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Test DD1",
    )
    db_session.add(ing)
    db_session.flush()
    return {"paciente": pac, "ingreso": ing}


@pytest.fixture
def cita_agendada(db_session, paciente_con_ingreso):
    """Cita en estado 'agendada' directamente en tabla de hechos."""
    ing = paciente_con_ingreso["ingreso"]
    c = Cita(origen="SALUTEM", ingreso_id=ing.id, estado="agendada", fecha=date(2026, 3, 10))
    db_session.add(c)
    db_session.commit()
    return c


# ── TC-DD1-02: PATCH estado agendada → realizada ─────────────────────────────

def test_patch_estado_cita_agendada_a_realizada(as_coordinacion, cita_agendada):
    resp = as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "realizada"
    assert body["id"] == cita_agendada.id


# ── TC-DD1-03: PATCH transición inválida devuelve 409 ─────────────────────────

def test_patch_estado_transicion_invalida_409(as_coordinacion, cita_agendada):
    """realizada → agendada no es una transición permitida."""
    # Primero pasamos a realizada
    as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    # Luego intentamos volver a agendada
    resp = as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "agendada"},
    )
    assert resp.status_code == 409


# ── TC-DD1-04: integración Cita agendada→PATCH→reporte ───────────────────────

def test_integracion_cita_realizada_reporte(as_coordinacion, cita_agendada):
    """Transiciona una Cita agendada a 'realizada' vía PATCH y verifica que el reporte operativo
    la contabiliza."""
    resp = as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 200

    # Reporte operativo: debe contar esa cita (fecha 2026-03-10)
    resp_rep = as_coordinacion.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp_rep.status_code == 200
    body = resp_rep.json()
    assert body["totales"]["realizadas"] >= 1


# ── TC-DD1-05: PATCH sin auth devuelve 401 ───────────────────────────────────

def test_patch_cita_sin_auth(client, cita_agendada):
    resp = client.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 401


# ── TC-DD1-06: Auditor no puede PATCH (403) ───────────────────────────────────

def test_patch_cita_auditor_rechazado(as_auditor, cita_agendada):
    resp = as_auditor.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 403
