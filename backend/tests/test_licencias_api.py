"""TC-121-03, TC-121-04 — Recurso Licencias: historial y días acumulados.

Adaptado al modelo real LicenciaMedica (EPIC-07):
  - campos: tipo_lm, tipo_reposo, fecha_inicio, fecha_termino, fecha_emision,
             inicio_reposo, fin_reposo, cantidad_dias, diagnostico, anulada
  - calcular_acumulado recibe ingreso_id (no folio).
"""

import pytest


@pytest.fixture
def folio_con_licencias(as_admin, db_session):
    """Crea un ingreso y licencias médicas asociadas directamente en la BD de test."""
    from datetime import date

    from app.models.ingreso import Ingreso
    from app.models.paciente import Paciente

    # Crear paciente e ingreso
    p = Paciente(rut="9998887779", nombre="Test Licencia", sexo="F", edad=40, region="Maule")
    db_session.add(p)
    db_session.flush()
    ing = Ingreso(
        paciente_id=p.id,
        folio="F-2026-LIC1",
        folio_manual=True,
        fecha_ingreso=date(2026, 6, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="x",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    try:
        from app.models.licencia import LicenciaMedica

        l1 = LicenciaMedica(
            ingreso_id=ing.id,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio=date(2026, 5, 1),
            fecha_termino=date(2026, 5, 15),
            fecha_emision=date(2026, 4, 30),
            inicio_reposo=date(2026, 5, 1),
            fin_reposo=date(2026, 5, 15),
            cantidad_dias=15,
            diagnostico="F41.1",
            anulada=False,
        )
        l2 = LicenciaMedica(
            ingreso_id=ing.id,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio=date(2026, 5, 20),
            fecha_termino=date(2026, 5, 29),
            fecha_emision=date(2026, 5, 19),
            inicio_reposo=date(2026, 5, 20),
            fin_reposo=date(2026, 5, 29),
            cantidad_dias=10,
            diagnostico="F41.1",
            anulada=False,
        )
        db_session.add_all([l1, l2])
        db_session.flush()
        return {"folio": "F-2026-LIC1", "dias_esperados": 25}
    except ImportError:
        pytest.skip("EPIC-07 (modelo LicenciaMedica) no está disponible")


def test_licencias_historial_y_acumulado(as_admin, folio_con_licencias):
    """TC-121-03: consultar licencias devuelve historial completo y total de días."""
    folio = folio_con_licencias["folio"]
    dias_esperados = folio_con_licencias["dias_esperados"]

    r = as_admin.get(f"/api/v1/licencias/folio/{folio}")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert "historial" in cuerpo
    assert "dias_acumulados" in cuerpo
    assert cuerpo["dias_acumulados"] == dias_esperados
    assert len(cuerpo["historial"]) == 2


def test_licencias_folio_inexistente_devuelve_404(as_admin):
    """TC-121-04: folio sin licencias → 404."""
    r = as_admin.get("/api/v1/licencias/folio/F-9999-0000")
    assert r.status_code == 404


def test_auditor_puede_consultar_licencias(as_auditor, as_admin, folio_con_licencias):
    """Auditor tiene permiso de lectura."""
    folio = folio_con_licencias["folio"]
    r = as_auditor.get(f"/api/v1/licencias/folio/{folio}")
    assert r.status_code == 200


def test_sin_token_licencias_devuelve_401(client):
    r = client.get("/api/v1/licencias/folio/F-2026-0001")
    assert r.status_code == 401
