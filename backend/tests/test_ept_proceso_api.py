import pytest
from tests.conftest_ept import ingreso_fixture  # noqa: F401


def _crear_caso(as_admin, ingreso_id, corresponde=True):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json={
            "ingreso_id": ingreso_id,
            "mes": "2026-06",
            "fecha_ingreso_ept": "2026-01-10",
            "nombre_trabajador": "Pedro Soto",
            "rut_trabajador": "12.345.678-5",
            "region_trabajador": "Maule",
            "eista": "Ana González",
            "factor_riesgo": "carga",
            "corresponde_ept": corresponde,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _proceso_base(caso_id, **over):
    base = {
        "caso_ept_id": caso_id,
        "plazo_evid_denunciante": "2026-02-10",
        "plazo_insumos_empresa": "2026-03-10",
        "hay_testigos": True,
        "testigos_cantidad": 3,
        "num_entrevistas": 2,
        "insumos_eista": "Informe preliminar",
        "observaciones": "Sin novedades",
    }
    base.update(over)
    return base


# TC-031-01: proceso completo guardado y con traza auditoría
def test_crear_proceso_completo(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(f"/api/v1/casos-ept/{caso_id}/proceso", json=_proceso_base(caso_id))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["hay_testigos"] is True
    assert body["testigos_cantidad"] == 3
    assert body["num_entrevistas"] == 2

    # legible en GET
    r2 = as_admin.get(f"/api/v1/casos-ept/{caso_id}/proceso")
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]


# TC-031-02: testigos=Sí con cantidad 0 rechazado → 422
def test_testigos_si_cantidad_cero_rechazado(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json=_proceso_base(caso_id, hay_testigos=True, testigos_cantidad=0),
    )
    assert r.status_code == 422
    assert "testigos" in r.text.lower() or "cantidad" in r.text.lower()


# TC-031-03: num_entrevistas negativo rechazado → 422
def test_num_entrevistas_negativo_rechazado(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json=_proceso_base(caso_id, num_entrevistas=-1),
    )
    assert r.status_code == 422
    assert "entrevistas" in r.text.lower()


# TC-031-04: plazo anterior a fecha_ingreso_ept rechazado → 422
def test_plazo_anterior_a_fecha_ingreso_rechazado(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json=_proceso_base(caso_id, plazo_insumos_empresa="2026-01-05"),
        # fecha_ingreso_ept es 2026-01-10; plazo 2026-01-05 < ingreso
    )
    assert r.status_code == 422
    assert "ingreso" in r.text.lower() or "plazo" in r.text.lower()


# TC-031-05: cambiar testigos de Sí a No → cantidad pasa a 0
def test_cambio_testigos_a_no_zeroes_cantidad(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json=_proceso_base(caso_id, hay_testigos=True, testigos_cantidad=3),
    )
    r = as_admin.patch(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json={"hay_testigos": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["hay_testigos"] is False
    assert r.json()["testigos_cantidad"] == 0


# TC-031-06: Coordinacion no puede editar → 403
def test_coordinacion_no_puede_editar_proceso(as_admin, as_coordinacion, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json=_proceso_base(caso_id),
    )
    r = as_coordinacion.patch(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json={"num_entrevistas": 5},
    )
    assert r.status_code == 403


# CA-5: corresponde_ept=False no permite crear proceso → 400
def test_proceso_rechazado_si_no_corresponde(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id, corresponde=False)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json=_proceso_base(caso_id),
    )
    assert r.status_code == 400
    assert "corresponde_ept" in r.text.lower()
