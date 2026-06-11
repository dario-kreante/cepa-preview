"""Tests — Task 8 EPIC-09: Métricas adherencia y avance CEPA-095."""
import pytest
from datetime import date

# ── Tests unitarios de casos borde del cálculo ───────────────────────────────

from app.services.adherencia import calcular_pct_adherencia, calcular_pct_avance


def test_adherencia_normal():
    """TC-095-01: 8 realizadas de 10 agendadas → 80%."""
    assert calcular_pct_adherencia(realizadas=8, agendadas=10) == pytest.approx(80.0)


def test_adherencia_cero_agendadas_no_divide_por_cero():
    """TC-095-03: 0 citas agendadas → None (no aplica)."""
    assert calcular_pct_adherencia(realizadas=0, agendadas=0) is None


def test_adherencia_completa():
    assert calcular_pct_adherencia(realizadas=10, agendadas=10) == pytest.approx(100.0)


def test_adherencia_cero_realizadas():
    assert calcular_pct_adherencia(realizadas=0, agendadas=5) == pytest.approx(0.0)


def test_avance_normal():
    """TC-095-02: 10 sesiones realizadas de plan 15 → 66.67%."""
    resultado = calcular_pct_avance(sesiones_realizadas=10, sesiones_plan=15)
    assert resultado == pytest.approx(66.67, abs=0.1)


def test_avance_plan_cero_no_divide_por_cero():
    """Plan = 0 o None → None."""
    assert calcular_pct_avance(sesiones_realizadas=5, sesiones_plan=0) is None
    assert calcular_pct_avance(sesiones_realizadas=5, sesiones_plan=None) is None


def test_avance_con_aumento_isl():
    """Plan 15 + 3 aumentos ISL = 18; 10 realizadas → 55.56%."""
    resultado = calcular_pct_avance(sesiones_realizadas=10, sesiones_plan=15, aumentos_isl=3)
    assert resultado == pytest.approx(55.56, abs=0.1)


# ── Tests de integración del endpoint ────────────────────────────────────────

@pytest.fixture
def datos_adherencia(db_session):
    from app.models.paciente import Paciente
    from app.models.ingreso import Ingreso
    from app.models.cita import Cita
    from app.models.plan_tratamiento import PlanTratamiento

    pac = Paciente(rut="77777777-7", nombre="Test Adh", sexo="F", edad=28, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id, folio="F-ADH-001", folio_manual=True,
        programa="DIEP", fecha_ingreso=date(2026, 1, 1),
        sexo="F", tramo_etario="18-29",
        tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    db_session.add(ing)
    db_session.flush()

    # 8 realizadas + 2 inasistencias = 10 citas total (agendadas)
    citas = (
        [Cita(ingreso_id=ing.id, estado="realizada",    fecha=date(2026, 1, d)) for d in range(1, 9)]
        + [Cita(ingreso_id=ing.id, estado="inasistencia", fecha=date(2026, 2, d)) for d in range(1, 3)]
    )
    db_session.add_all(citas)

    plan = PlanTratamiento(ingreso_id=ing.id, sesiones_plan=15, aumentos_isl=3)
    db_session.add(plan)
    db_session.commit()
    return {"ingreso": ing}


def test_adherencia_endpoint_correcto(as_coordinacion, datos_adherencia):
    ing = datos_adherencia["ingreso"]
    resp = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ing.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["citas_realizadas"] == 8
    assert body["citas_agendadas"] == 10
    assert abs(body["pct_adherencia"] - 80.0) < 0.1


def test_adherencia_auditor_accede(as_auditor, datos_adherencia):
    ing = datos_adherencia["ingreso"]
    resp = as_auditor.get(f"/api/v1/reportes/adherencia/{ing.id}")
    assert resp.status_code == 200
