def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


# TC-014-01: cerrar con alta terapéutica
def test_cerrar_con_alta_terapeutica(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "tipo_alta": "terapeutica", "fecha_alta": "2026-06-20"},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "cerrado"
    assert cuerpo["tipo_alta"] == "terapeutica"
    assert cuerpo["fecha_alta"] == "2026-06-20"


# TC-014-02: derivar con observaciones
def test_derivar_con_observaciones(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "derivado", "observaciones": "Derivado a red pública"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "derivado"
    assert r.json()["observaciones"] == "Derivado a red pública"


# TC-014-04: tipo de alta fuera de catálogo -> 422
def test_tipo_alta_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "tipo_alta": "otro"},
    )
    assert r.status_code == 422


# TC-014-05: cerrar conservando flag de revisión
def test_cerrar_con_flag_revision(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "tipo_alta": "medica", "flag_revision": True},
    )
    assert r.status_code == 200
    assert r.json()["flag_revision"] is True


# CA-1: estado fuera de catálogo -> 422
def test_estado_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "pausado"}
    )
    assert r.status_code == 422


# TC-014-06: Auditor no puede cerrar -> 403
def test_auditor_no_cierra(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = as_auditor.post(
        f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "cerrado"}
    )
    assert r.status_code == 403


def test_cierre_ingreso_inexistente(as_admin):
    r = as_admin.post("/api/v1/ingresos/999999/cierre", json={"estado": "cerrado"})
    assert r.status_code == 404
