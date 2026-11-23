"""Convenio del ingreso: se valida contra el catálogo al crear y al editar.

Al editar, un valor antiguo fuera del catálogo se conserva (no se rechaza ni se pierde).
"""

from app.models.convenio import Convenio
from app.services.salutem_sync.profesionales import normalizar_nombre


def _payload(**over):
    base = {
        "rut": "12.345.678-5",
        "nombre": "Juan Pérez",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
        "diagnostico": "Trastorno adaptativo",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-10",
    }
    base.update(over)
    return base


def _sembrar(db, nombre: str, **over) -> Convenio:
    c = Convenio(nombre=nombre, nombre_normalizado=normalizar_nombre(nombre), **over)
    db.add(c)
    db.flush()
    return c


def test_alta_con_convenio_del_catalogo(as_admin, db_session):
    _sembrar(db_session, "DIEP", visible=True, activo_salutem=True)
    r = as_admin.post("/api/v1/ingresos", json=_payload(tipo_convenio="DIEP"))
    assert r.status_code == 201, r.text
    assert r.json()["tipo_convenio"] == "DIEP"


def test_alta_con_convenio_desconocido_422(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(tipo_convenio="Inventado"))
    assert r.status_code == 422, r.text
    assert "Inventado" in r.text


def test_alta_con_convenio_oculto_422(as_admin, db_session):
    _sembrar(db_session, "Oculto", visible=False, activo_salutem=True)
    r = as_admin.post("/api/v1/ingresos", json=_payload(tipo_convenio="Oculto"))
    assert r.status_code == 422, r.text


def test_alta_sin_convenio_y_blanco_quedan_null(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload())
    assert r.status_code == 201, r.text
    assert r.json()["tipo_convenio"] is None
    r2 = as_admin.post(
        "/api/v1/ingresos", json=_payload(rut="10.000.000-8", tipo_convenio="  ")
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["tipo_convenio"] is None


def test_editar_cambia_convenio(as_admin, db_session, ingreso_fixture):
    _sembrar(db_session, "DIEP", visible=True, activo_salutem=True)
    r = as_admin.put(f"/api/v1/ingresos/{ingreso_fixture.id}", json={"tipo_convenio": "DIEP"})
    assert r.status_code == 200, r.text
    assert r.json()["tipo_convenio"] == "DIEP"


def test_editar_conserva_valor_antiguo(as_admin, db_session, ingreso_fixture):
    ingreso_fixture.tipo_convenio = "ISL"
    db_session.flush()
    r = as_admin.put(
        f"/api/v1/ingresos/{ingreso_fixture.id}",
        json={"tipo_convenio": "ISL", "diagnostico": "x"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["tipo_convenio"] == "ISL"


def test_editar_a_valor_desconocido_422(as_admin, ingreso_fixture):
    r = as_admin.put(f"/api/v1/ingresos/{ingreso_fixture.id}", json={"tipo_convenio": "Inventado"})
    assert r.status_code == 422, r.text


def test_editar_conserva_valor_antiguo_con_espacios(as_admin, db_session, ingreso_fixture):
    ingreso_fixture.tipo_convenio = "ISL "
    db_session.flush()
    r = as_admin.put(
        f"/api/v1/ingresos/{ingreso_fixture.id}",
        json={"tipo_convenio": "ISL", "diagnostico": "x"},
    )
    assert r.status_code == 200, r.text
