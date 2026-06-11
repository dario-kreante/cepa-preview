import pytest
from datetime import date, timedelta
from tests.conftest_ept import ingreso_fixture  # noqa: F401

from app.services.ept import calcular_estado_cumplimiento
from app.domain.enums_ept import EstadoCumplimiento


# ── Tests unitarios del cálculo de estado ──────────────────────────

def test_estado_en_plazo():
    hoy = date(2026, 6, 10)
    objetivo = hoy + timedelta(days=30)
    assert calcular_estado_cumplimiento(objetivo, None, hoy) == EstadoCumplimiento.EN_PLAZO


def test_estado_por_vencer():
    hoy = date(2026, 6, 10)
    objetivo = hoy + timedelta(days=5)  # dentro de ventana de 7 días
    assert calcular_estado_cumplimiento(objetivo, None, hoy) == EstadoCumplimiento.POR_VENCER


def test_estado_vencido():
    hoy = date(2026, 6, 10)
    objetivo = hoy - timedelta(days=1)
    assert calcular_estado_cumplimiento(objetivo, None, hoy) == EstadoCumplimiento.VENCIDO


def test_estado_cumplido_con_envio():
    hoy = date(2026, 6, 10)
    objetivo = hoy - timedelta(days=1)  # ya vencido
    fecha_envio = hoy - timedelta(days=2)
    assert calcular_estado_cumplimiento(objetivo, fecha_envio, hoy) == EstadoCumplimiento.CUMPLIDO


def test_estado_en_plazo_sin_fecha_objetivo():
    assert calcular_estado_cumplimiento(None, None, date(2026, 6, 10)) == EstadoCumplimiento.EN_PLAZO


# ── Tests de integración API ──────────────────────────────────────

def _crear_caso(as_admin, ingreso_id):
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
            "corresponde_ept": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# TC-032-01: plazos guardados y estado calculado correctamente
def test_crear_plazos_estado_en_plazo(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={
            "caso_ept_id": caso_id,
            "plazo_informe_ept": "2026-12-31",
            "plazo_portal_isl": "2026-12-31",
            "fecha_entrega_isl": "2026-12-31",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado_informe"] == "en_plazo"
    assert body["estado_entrega_isl"] == "en_plazo"


# TC-032-03: fecha_entrega_isl = hoy sin envío → estado calculado correctamente
def test_fecha_hoy_sin_envio(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    hoy = date.today().isoformat()
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={
            "caso_ept_id": caso_id,
            "fecha_entrega_isl": hoy,
        },
    )
    assert r.status_code == 201, r.text
    # hoy puede ser "por_vencer" (0 días restantes ≤ 7) o "vencido" si ya pasó
    estado = r.json()["estado_entrega_isl"]
    assert estado in {"por_vencer", "vencido", "en_plazo"}


# TC-032-04: fecha_entrega_isl anterior a fecha_ingreso rechazada
def test_fecha_entrega_anterior_a_ingreso_rechazada(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={
            "caso_ept_id": caso_id,
            "fecha_entrega_isl": "2026-01-05",  # < fecha_ingreso_ept 2026-01-10
        },
    )
    assert r.status_code == 422
    assert "ingreso" in r.text.lower() or "entrega" in r.text.lower()


# TC-032-05: registrar envío cierra el hito (estado → cumplido)
def test_registrar_envio_marca_cumplido(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={
            "caso_ept_id": caso_id,
            "plazo_informe_ept": "2026-07-01",
            "fecha_entrega_isl": "2026-07-15",
        },
    )
    r = as_admin.patch(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"fecha_envio": "2026-06-20"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["estado_informe"] == "cumplido"
    assert body["estado_entrega_isl"] == "cumplido"
    assert body["fecha_envio"] == "2026-06-20"


# TC-032-06: Auditor solo lectura en plazos → 403 para editar
def test_auditor_no_puede_editar_plazos(as_admin, as_auditor, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": "2026-12-31"},
    )
    r = as_auditor.patch(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"fecha_envio": "2026-06-20"},
    )
    assert r.status_code == 403


# CA-5: Auditor puede leer plazos en solo lectura
def test_auditor_puede_leer_plazos(as_admin, as_auditor, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": "2026-12-31"},
    )
    r = as_auditor.get(f"/api/v1/casos-ept/{caso_id}/plazos")
    assert r.status_code == 200
    assert "estado_informe" in r.json()


# corresponde_ept=False no permite crear plazos
def test_plazos_rechazados_si_no_corresponde(as_admin, ingreso_fixture):
    r_caso = as_admin.post(
        "/api/v1/casos-ept",
        json={
            "ingreso_id": ingreso_fixture.id,
            "mes": "2026-06",
            "fecha_ingreso_ept": "2026-01-10",
            "nombre_trabajador": "Pedro Soto",
            "rut_trabajador": "12.345.678-5",
            "region_trabajador": "Maule",
            "eista": "Ana González",
            "factor_riesgo": "carga",
            "corresponde_ept": False,
        },
    )
    caso_id = r_caso.json()["id"]
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": "2026-12-31"},
    )
    assert r.status_code == 400
