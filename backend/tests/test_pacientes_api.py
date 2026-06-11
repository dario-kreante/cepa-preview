"""TC-121-01, TC-121-04, TC-121-06 — Recurso Pacientes."""

import pytest


@pytest.fixture
def paciente_existente(as_admin):
    """Crea un paciente vía el endpoint de ingresos (flujo existente de EPIC-01)."""
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "12.345.678-5",
            "nombre": "Juan Integración",
            "sexo": "M",
            "edad": 35,
            "region": "Maule",
            "diagnostico": "Lumbalgia",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_buscar_paciente_por_rut(as_admin, paciente_existente):
    """TC-121-01: buscar paciente por RUT → 200 con datos."""
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "12.345.678-5"})
    assert r.status_code == 200
    resultados = r.json()
    assert len(resultados) >= 1
    assert any(p["rut"] == "123456785" for p in resultados)


def test_buscar_paciente_por_nombre(as_admin, paciente_existente):
    """CA-1: búsqueda por nombre."""
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "Juan Integración"})
    assert r.status_code == 200
    assert any("Juan" in p["nombre"] for p in r.json())


def test_buscar_paciente_por_folio(as_admin, paciente_existente):
    """CA-1: búsqueda por folio."""
    folio = paciente_existente["folio"]
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": folio})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_paciente_inexistente_devuelve_lista_vacia(as_admin):
    """TC-121-04: folio no registrado → lista vacía."""
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "F-9999-9999"})
    assert r.status_code == 200  # búsqueda devuelve lista vacía, no 404
    assert r.json() == []


def test_obtener_paciente_por_id_inexistente_devuelve_404(as_admin):
    """TC-121-04: GET /pacientes/{id} con id no existente → 404."""
    r = as_admin.get("/api/v1/pacientes/99999999")
    assert r.status_code == 404


def test_auditor_puede_buscar_pacientes(as_auditor, paciente_existente):
    """Auditor tiene permiso de lectura."""
    r = as_auditor.get("/api/v1/pacientes/buscar", params={"q": "123456785"})
    assert r.status_code == 200


def test_sin_token_pacientes_devuelve_401(client):
    """TC-121-06 / CA-2 de CEPA-120: sin JWT → 401."""
    r = client.get("/api/v1/pacientes/buscar", params={"q": "123456785"})
    assert r.status_code == 401


def test_auditor_no_puede_crear_paciente_directamente(as_auditor):
    """TC-121-06: Auditor no puede hacer escritura directa de paciente → 403."""
    r = as_auditor.patch(
        "/api/v1/pacientes/1",
        json={"nombre": "Intento de escritura"},
    )
    assert r.status_code == 403
