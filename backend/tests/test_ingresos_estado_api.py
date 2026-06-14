"""TC-121-02 (actualización de estado) y TC-121-06 (permisos)."""

import pytest


@pytest.fixture
def ingreso_activo(as_admin):
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "11.111.111-1",
            "nombre": "Estado Test",
            "sexo": "M",
            "edad": 45,
            "region": "Maule",
            "diagnostico": "Dolor lumbar",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_actualizar_estado_ingreso(as_admin, ingreso_activo):
    """TC-121-02 (CA-2): consultar y actualizar estado del ingreso con trazabilidad."""
    ingreso_id = ingreso_activo["id"]
    # Verificar estado inicial
    r_get = as_admin.get(f"/api/v1/ingresos/{ingreso_id}")
    assert r_get.status_code == 200
    assert r_get.json()["estado"] == "activo"

    # Actualizar estado
    r_patch = as_admin.patch(
        f"/api/v1/ingresos/{ingreso_id}/estado",
        json={"estado": "cerrado", "tipo_alta": "terapeutica", "observaciones": "Alta programada"},
    )
    assert r_patch.status_code == 200, r_patch.text
    assert r_patch.json()["estado"] == "cerrado"

    # Verificar persistencia
    r_get2 = as_admin.get(f"/api/v1/ingresos/{ingreso_id}")
    assert r_get2.json()["estado"] == "cerrado"


def test_auditor_no_puede_actualizar_estado(as_auditor, ingreso_activo):
    """TC-121-06: rol sin permiso de escritura → 403."""
    ingreso_id = ingreso_activo["id"]
    r = as_auditor.patch(
        f"/api/v1/ingresos/{ingreso_id}/estado",
        json={"estado": "cerrado"},
    )
    assert r.status_code == 403


def test_estado_invalido_devuelve_422(as_admin, ingreso_activo):
    """Estado fuera de lista cerrada → 422."""
    ingreso_id = ingreso_activo["id"]
    r = as_admin.patch(
        f"/api/v1/ingresos/{ingreso_id}/estado",
        json={"estado": "estado_inexistente"},
    )
    assert r.status_code == 422


def test_ingreso_inexistente_devuelve_404(as_admin):
    r = as_admin.patch(
        "/api/v1/ingresos/99999999/estado",
        json={"estado": "cerrado"},
    )
    assert r.status_code == 404
