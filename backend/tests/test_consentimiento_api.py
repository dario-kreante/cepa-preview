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


# TC-016-01: sin consentimiento firmado -> iniciar tratamiento bloqueado (409)
def test_iniciar_tratamiento_bloqueado_sin_consentimiento(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/iniciar-tratamiento")
    assert r.status_code == 409
    assert "consentimiento" in r.text.lower()


# TC-016-02: con consentimiento firmado -> tratamiento habilitado
def test_iniciar_tratamiento_con_consentimiento_firmado(as_admin):
    ing = _ingreso(as_admin)
    as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento",
        json={"estado": "firmado", "fecha_firma": "2026-06-02"},
    )
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/iniciar-tratamiento")
    assert r.status_code == 200
    assert r.json()["tratamiento_iniciado"] is True


# TC-016-03: consentimiento pendiente aparece en alertas
def test_alerta_consentimiento_pendiente(as_admin):
    ing = _ingreso(as_admin)
    as_admin.put(f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "pendiente"})
    r = as_admin.get("/api/v1/consentimientos/alertas")
    assert r.status_code == 200
    assert any(c["ingreso_id"] == ing["id"] for c in r.json())


# firmado NO aparece en alertas
def test_consentimiento_firmado_no_en_alertas(as_admin):
    ing = _ingreso(as_admin, rut="10.000.05K")
    as_admin.put(f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "firmado"})
    r = as_admin.get("/api/v1/consentimientos/alertas")
    assert not any(c["ingreso_id"] == ing["id"] for c in r.json())


# TC-016-04: firmado sin evidencia se acepta (mecanismo D9 por definir)
def test_firmado_sin_evidencia_aceptado(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "firmado"}
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "firmado"


# estado inválido -> 422
def test_estado_consentimiento_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "quizas"}
    )
    assert r.status_code == 422


# TC-016-05: Auditor no puede cambiar estado del consentimiento -> 403
def test_auditor_no_cambia_consentimiento(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = as_auditor.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "firmado"}
    )
    assert r.status_code == 403
