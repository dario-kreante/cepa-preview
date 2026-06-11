"""Tests — Task 6 EPIC-09: Reporte licencias acumuladas CEPA-094.

Deviación D5: LicenciaMedica usa `cantidad_dias` (no `dias_reposo`) y
`origen: str` ("sistema"/"extra_sistema") en lugar de `origen_externo: bool`.
Los fixtures se adaptan a los campos reales del modelo.
"""
import pytest
from datetime import date


@pytest.fixture
def datos_licencias(db_session):
    """Crea un ingreso con 3 licencias: 2 internas + 1 extra-sistema."""
    from app.models.paciente import Paciente
    from app.models.ingreso import Ingreso
    from app.models.licencia import LicenciaMedica

    pac = Paciente(rut="55555555-5", nombre="Test Lic", sexo="F", edad=35, region="Maule")
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id, folio="F-LIC-001", folio_manual=True,
        programa="DIEP", fecha_ingreso=date(2026, 1, 10),
        sexo="F", tramo_etario="18-29", region="Maule", tipo_convenio="DIEP",
        tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    db_session.add(ing)
    db_session.flush()

    # 2 internas (origen="sistema") + 1 externa (origen="extra_sistema")
    lics = [
        LicenciaMedica(
            ingreso_id=ing.id, folio_lm="LM-001", tipo_lm="1",
            tipo_reposo="total", cantidad_dias=10, origen="sistema",
            fecha_inicio=date(2026, 2, 1), fecha_termino=date(2026, 2, 10),
            fecha_emision=date(2026, 2, 1), inicio_reposo=date(2026, 2, 1),
            fin_reposo=date(2026, 2, 10), diagnostico="Test",
        ),
        LicenciaMedica(
            ingreso_id=ing.id, folio_lm="LM-002", tipo_lm="1",
            tipo_reposo="total", cantidad_dias=15, origen="sistema",
            fecha_inicio=date(2026, 3, 1), fecha_termino=date(2026, 3, 15),
            fecha_emision=date(2026, 3, 1), inicio_reposo=date(2026, 3, 1),
            fin_reposo=date(2026, 3, 15), diagnostico="Test",
        ),
        LicenciaMedica(
            ingreso_id=ing.id, folio_lm="LM-003", tipo_lm="1",
            tipo_reposo="total", cantidad_dias=7, origen="extra_sistema",
            fecha_inicio=date(2026, 4, 1), fecha_termino=date(2026, 4, 7),
            fecha_emision=date(2026, 4, 1), inicio_reposo=date(2026, 4, 1),
            fin_reposo=date(2026, 4, 7), diagnostico="Test",
        ),
    ]
    db_session.add_all(lics)
    db_session.commit()
    return {"ingreso": ing}


# ── TC-094-01: total de días acumulados correcto por paciente ─────────────────

def test_licencias_total_acumulado_correcto(as_coordinacion, datos_licencias):
    ing = datos_licencias["ingreso"]
    resp = as_coordinacion.get("/api/v1/reportes/licencias", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    folio = next((i for i in body["items"] if i["folio_id"] == ing.id), None)
    assert folio is not None
    # 10 + 15 + 7 = 32 total
    assert folio["total_dias_acumulados"] == 32


# ── TC-094-02: licencias extra-sistema marcadas como tales ───────────────────

def test_licencias_externas_marcadas(as_coordinacion, datos_licencias):
    ing = datos_licencias["ingreso"]
    resp = as_coordinacion.get("/api/v1/reportes/licencias", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
    })
    body = resp.json()
    folio = next(i for i in body["items"] if i["folio_id"] == ing.id)
    assert folio["licencias_externas"] == 1
    assert folio["licencias_internas"] == 2


# ── TC-094-04: sin período → 422 ─────────────────────────────────────────────

def test_licencias_sin_periodo_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/reportes/licencias")
    assert resp.status_code == 422


# ── TC-094-05: Auditor puede leer ────────────────────────────────────────────

def test_licencias_auditor_accede(as_auditor, datos_licencias):
    resp = as_auditor.get("/api/v1/reportes/licencias", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
    })
    assert resp.status_code == 200
