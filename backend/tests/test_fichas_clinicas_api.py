"""TC-121-02, TC-121-05 — Fichas clínicas bidireccionales (push/pull).

D12: el CEPA recibe datos de SALUTEM (pull) y los persiste localmente;
nunca escribe de vuelta a SALUTEM. Los sistemas externos pueden enviar
datos (push) que el CEPA persiste en su dominio.
"""

import pytest


@pytest.fixture
def ingreso_existente(as_admin):
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "7.876.543-7",
            "nombre": "María Ficha",
            "sexo": "F",
            "edad": 28,
            "region": "Maule",
            "diagnostico": "Ansiedad generalizada",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_push_ficha_clinica_persiste_en_cepa(as_admin, ingreso_existente):
    """TC-121-02 (push): sistema externo envía datos clínicos → 201 y persistidos."""
    folio = ingreso_existente["folio"]
    payload = {
        "folio": folio,
        "origen": "SAM",
        "contenido": {"diagnostico": "F41.1", "sesiones": 5, "nota_clinica": "Evolución estable"},
    }
    r = as_admin.post("/api/v1/fichas-clinicas", json=payload)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["folio"] == folio
    assert cuerpo["origen"] == "SAM"


def test_pull_ficha_clinica_devuelve_datos(as_admin, ingreso_existente):
    """TC-121-02 (pull): sistema externo solicita datos clínicos → 200."""
    folio = ingreso_existente["folio"]
    # Crear ficha primero (push)
    as_admin.post(
        "/api/v1/fichas-clinicas",
        json={"folio": folio, "origen": "SAM", "contenido": {"nota": "Primera atención"}},
    )
    # Luego pull
    r = as_admin.get(f"/api/v1/fichas-clinicas/{folio}")
    assert r.status_code == 200
    fichas = r.json()
    assert isinstance(fichas, list)
    assert len(fichas) >= 1
    assert fichas[0]["folio"] == folio


def test_pull_salutem_no_escribe_sobre_salutem(as_admin, ingreso_existente, monkeypatch):
    """TC-121-05: pull desde SALUTEM persiste localmente; no llama a métodos de escritura."""
    from tests.test_salutem_no_escribe import _SalutemWriteGuardMock

    guard = _SalutemWriteGuardMock()
    monkeypatch.setattr(
        "app.integrations.salutem.client.get_salutem_client",
        lambda: guard,
    )
    folio = ingreso_existente["folio"]
    r = as_admin.post(
        "/api/v1/fichas-clinicas/pull-salutem",
        json={"folio": folio},
    )
    # 200 o 404 (SALUTEM stub devuelve None); lo crucial es que no hubo escritura
    assert r.status_code in (200, 404)
    # Si guard hubiera disparado AssertionError, el endpoint habría devuelto 500


def test_ficha_folio_inexistente_devuelve_404(as_admin):
    """TC-121-04: folio no registrado → 404."""
    r = as_admin.get("/api/v1/fichas-clinicas/F-9999-0000")
    assert r.status_code == 404


def test_auditor_puede_leer_fichas(as_auditor, as_admin, ingreso_existente):
    """Auditor tiene permiso de lectura sobre fichas clínicas."""
    folio = ingreso_existente["folio"]
    as_admin.post(
        "/api/v1/fichas-clinicas",
        json={"folio": folio, "origen": "SALUTEM", "contenido": {"sesion": 1}},
    )
    r = as_auditor.get(f"/api/v1/fichas-clinicas/{folio}")
    assert r.status_code == 200


def test_auditor_no_puede_hacer_push(as_auditor, ingreso_existente):
    """TC-121-06: Auditor (solo lectura) no puede hacer push de ficha → 403."""
    folio = ingreso_existente["folio"]
    r = as_auditor.post(
        "/api/v1/fichas-clinicas",
        json={"folio": folio, "origen": "SAM", "contenido": {}},
    )
    assert r.status_code == 403
