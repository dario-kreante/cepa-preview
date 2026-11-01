"""Rol Superadmin (reunión 29-10-2026): pasa todos los controles de rol, incluidos los
exclusivos de Administrativo (EPT, corregir folio) y de Coordinación (usuarios), y solo otro
Superadmin puede otorgar, editar o desactivar ese rol."""

from app.models.usuario import Usuario

from tests.test_ept_caso_api import _payload as _payload_ept
from tests.test_ingreso_corregir_folio_api import _crear_ingreso


def test_superadmin_crea_caso_ept(as_superadmin, ingreso_fixture):
    r = as_superadmin.post("/api/v1/casos-ept", json=_payload_ept(ingreso_fixture.id))
    assert r.status_code == 201, r.text


def test_superadmin_corrige_el_folio(as_superadmin):
    ingreso = _crear_ingreso(as_superadmin)
    r = as_superadmin.put(f"/api/v1/ingresos/{ingreso['id']}/folio", json={"folio": "F-2026-0998"})
    assert r.status_code == 200, r.text
    assert r.json()["folio"] == "F-2026-0998"


def test_superadmin_gestiona_usuarios(as_superadmin):
    r = as_superadmin.get("/api/v1/usuarios")
    assert r.status_code == 200
    r = as_superadmin.post(
        "/api/v1/usuarios",
        json={"username": "otra_super", "nombre": "Otra", "password": "Clave123!", "rol": "Superadmin"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["rol"] == "Superadmin"


def test_superadmin_lee_auditoria_y_reportes(as_superadmin):
    assert as_superadmin.get("/api/v1/audit-log").status_code != 403
    assert as_superadmin.get("/api/v1/alertas").status_code == 200


def test_coordinacion_no_puede_crear_superadmin(as_coordinacion):
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "intento", "nombre": "X", "password": "Clave123!", "rol": "Superadmin"},
    )
    assert r.status_code == 403


def test_coordinacion_no_puede_promover_ni_tocar_a_un_superadmin(as_coordinacion, db_session):
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "promovible", "nombre": "P", "password": "Clave123!", "rol": "Administrativo"},
    )
    uid = r.json()["id"]
    assert as_coordinacion.put(f"/api/v1/usuarios/{uid}", json={"rol": "Superadmin"}).status_code == 403

    db_session.get(Usuario, uid).rol = "Superadmin"
    db_session.commit()
    assert as_coordinacion.put(f"/api/v1/usuarios/{uid}", json={"nombre": "Q"}).status_code == 403
    assert as_coordinacion.patch(f"/api/v1/usuarios/{uid}/desactivar").status_code == 403
    assert as_coordinacion.put(f"/api/v1/usuarios/{uid}", json={"rol": "Auditor"}).status_code == 403
