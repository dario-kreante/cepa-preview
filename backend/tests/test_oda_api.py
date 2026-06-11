from datetime import date, timedelta


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


# TC-015-01: registrar ODA con vencimiento
def test_registrar_oda(as_admin):
    ing = _ingreso(as_admin)
    venc = (date.today() + timedelta(days=20)).isoformat()
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/odas",
        json={"identificador": "ODA-1", "fecha_vencimiento": venc},
    )
    assert r.status_code == 201
    assert r.json()["fecha_vencimiento"] == venc
    assert r.json()["vigente"] is True


# TC-015-04: ODA sin fecha de vencimiento -> 422
def test_oda_sin_vencimiento(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-1"}
    )
    assert r.status_code == 422


# TC-015-05: ODA actualizada conserva historial y marca vigente la nueva
def test_oda_actualizada_conserva_historial(as_admin):
    ing = _ingreso(as_admin)
    v1 = (date.today() + timedelta(days=10)).isoformat()
    v2 = (date.today() + timedelta(days=40)).isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-1", "fecha_vencimiento": v1})
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-2", "fecha_vencimiento": v2})
    listado = as_admin.get(f"/api/v1/ingresos/{ing['id']}/odas").json()
    assert len(listado) == 2  # historial conservado
    vigentes = [o for o in listado if o["vigente"]]
    assert len(vigentes) == 1 and vigentes[0]["identificador"] == "ODA-2"


# TC-015-02: alerta de ODAS por vencer (ventana 5 días)
def test_alerta_oda_por_vencer(as_admin):
    ing = _ingreso(as_admin)
    venc = (date.today() + timedelta(days=3)).isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-1", "fecha_vencimiento": venc})
    r = as_admin.get("/api/v1/odas/alertas")
    assert r.status_code == 200
    assert any(o["identificador"] == "ODA-1" for o in r.json())


# TC-015-03: ODA que vence hoy entra en la alerta (límite)
def test_alerta_oda_vence_hoy(as_admin):
    ing = _ingreso(as_admin, rut="10.000.05K")
    hoy = date.today().isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-HOY", "fecha_vencimiento": hoy})
    r = as_admin.get("/api/v1/odas/alertas")
    assert any(o["identificador"] == "ODA-HOY" for o in r.json())


# ODA lejana NO entra en la alerta
def test_oda_lejana_no_alerta(as_admin):
    ing = _ingreso(as_admin, rut="21.111.111-9")
    venc = (date.today() + timedelta(days=60)).isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-LEJOS", "fecha_vencimiento": venc})
    r = as_admin.get("/api/v1/odas/alertas")
    assert not any(o["identificador"] == "ODA-LEJOS" for o in r.json())


# TC-015-06: Auditor no puede registrar ODA -> 403
def test_auditor_no_registra_oda(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    venc = (date.today() + timedelta(days=10)).isoformat()
    r = as_auditor.post(
        f"/api/v1/ingresos/{ing['id']}/odas",
        json={"identificador": "ODA-1", "fecha_vencimiento": venc},
    )
    assert r.status_code == 403
