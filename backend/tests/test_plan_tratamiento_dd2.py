"""Tests DD-2 (EPIC-09 rework): endpoint PUT /ingresos/{id}/plan-tratamiento.

TC-DD2-01: crear plan nuevo devuelve 200 con sesiones_plan.
TC-DD2-02: actualizar plan existente devuelve datos actualizados.
TC-DD2-03: upsert luego reporte adherencia refleja pct_avance.
TC-DD2-04: ingreso inexistente devuelve 404.
TC-DD2-05: Auditor no puede escribir (403).
"""
import pytest
from datetime import date

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


@pytest.fixture
def ingreso_dd2(db_session):
    pac = Paciente(rut="99999999-9", nombre="Test Plan", sexo="F", edad=40, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id,
        folio="F-DD2-001",
        folio_manual=True,
        programa="DIEP",
        fecha_ingreso=date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Test Plan",
    )
    db_session.add(ing)
    db_session.commit()
    return ing


# ── TC-DD2-01: crear plan nuevo ───────────────────────────────────────────────

def test_crear_plan_tratamiento(as_coordinacion, ingreso_dd2):
    resp = as_coordinacion.put(
        f"/api/v1/ingresos/{ingreso_dd2.id}/plan-tratamiento",
        json={"sesiones_plan": 15, "aumentos_isl": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sesiones_plan"] == 15
    assert body["aumentos_isl"] == 3
    assert body["ingreso_id"] == ingreso_dd2.id


# ── TC-DD2-02: actualizar plan existente (upsert) ─────────────────────────────

def test_upsert_plan_tratamiento_actualiza(as_coordinacion, ingreso_dd2):
    # Primer PUT
    as_coordinacion.put(
        f"/api/v1/ingresos/{ingreso_dd2.id}/plan-tratamiento",
        json={"sesiones_plan": 10, "aumentos_isl": 0},
    )
    # Segundo PUT (actualiza)
    resp = as_coordinacion.put(
        f"/api/v1/ingresos/{ingreso_dd2.id}/plan-tratamiento",
        json={"sesiones_plan": 20, "aumentos_isl": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sesiones_plan"] == 20
    assert body["aumentos_isl"] == 5


# ── TC-DD2-03: upsert y reporte adherencia refleja pct_avance ────────────────

def test_upsert_plan_refleja_adherencia(as_coordinacion, db_session, ingreso_dd2):
    from app.models.cita import Cita

    # Agregar 8 citas realizadas
    for d in range(1, 9):
        db_session.add(Cita(
            ingreso_id=ingreso_dd2.id,
            estado="realizada",
            fecha=date(2026, 2, d),
        ))
    db_session.commit()

    # Upsert plan con 15 sesiones
    resp_put = as_coordinacion.put(
        f"/api/v1/ingresos/{ingreso_dd2.id}/plan-tratamiento",
        json={"sesiones_plan": 15, "aumentos_isl": 0},
    )
    assert resp_put.status_code == 200

    # Reporte adherencia
    resp = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ingreso_dd2.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sesiones_plan"] == 15
    # 8/15 * 100 ≈ 53.33
    assert body["pct_avance"] is not None
    assert abs(body["pct_avance"] - 53.33) < 1.0


# ── TC-DD2-04: ingreso inexistente → 404 ─────────────────────────────────────

def test_plan_tratamiento_ingreso_inexistente(as_coordinacion):
    resp = as_coordinacion.put(
        "/api/v1/ingresos/9999999/plan-tratamiento",
        json={"sesiones_plan": 10, "aumentos_isl": 0},
    )
    assert resp.status_code == 404


# ── TC-DD2-05: Auditor no puede escribir ─────────────────────────────────────

def test_plan_tratamiento_auditor_rechazado(as_auditor, ingreso_dd2):
    resp = as_auditor.put(
        f"/api/v1/ingresos/{ingreso_dd2.id}/plan-tratamiento",
        json={"sesiones_plan": 10, "aumentos_isl": 0},
    )
    assert resp.status_code == 403
