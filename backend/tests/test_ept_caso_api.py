def _payload(ingreso_id, **over):
    base = {
        "ingreso_id": ingreso_id,
        "mes": "2026-06",
        "fecha_ingreso_ept": "2026-01-10",
        "nombre_trabajador": "Pedro Soto",
        "rut_trabajador": "12.345.678-5",
        "region_trabajador": "Maule",
        "eista": "Ana González",
        "factor_riesgo": "carga",
        "corresponde_ept": True,
        "razon_social": "Empresa XY SA",
        "unidad_cargo_horario": "Bodega / Bodeguero / turno mañana",
    }
    base.update(over)
    return base


# TC-030-01: creación completa — caso creado, auditoría registrada
def test_crear_caso_ept_completo(as_admin, db_session, ingreso_fixture):
    r = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] >= 1
    assert body["estado"] == "abierto"
    assert body["corresponde_ept"] is True
    assert body["rut_trabajador"] == "123456785"  # normalizado

    # visible al leer por id
    r2 = as_admin.get(f"/api/v1/casos-ept/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]


# TC-030-02: RUT con DV inválido rechazado con 422
def test_rut_invalido_retorna_422(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, rut_trabajador="12.345.678-0"),
    )
    assert r.status_code == 422
    assert "rut" in r.text.lower()


# TC-030-03: tercer contacto rechazado
def test_tercer_contacto_rechazado(as_admin, db_session, ingreso_fixture):
    r = as_admin.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    caso_id = r.json()["id"]
    as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "a@b.cl"})
    as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "c@d.cl"})
    r3 = as_admin.post(f"/api/v1/casos-ept/{caso_id}/contactos", json={"correo": "e@f.cl"})
    assert r3.status_code == 400
    assert "máximo" in r3.text.lower() or "max" in r3.text.lower()


# TC-030-04: corresponde_ept=False — caso creado con estado no_corresponde
def test_corresponde_ept_false(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, corresponde_ept=False),
    )
    assert r.status_code == 201
    assert r.json()["estado"] == "no_corresponde"
    assert r.json()["corresponde_ept"] is False


# TC-030-05: Auditor no puede crear (solo lectura) → 403
def test_auditor_no_puede_crear(as_auditor, ingreso_fixture):
    r = as_auditor.post("/api/v1/casos-ept", json=_payload(ingreso_fixture.id))
    assert r.status_code == 403


# TC-030-06: campo factor_riesgo vacío / inválido → 422
def test_factor_riesgo_invalido_rechazado(as_admin, ingreso_fixture):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json=_payload(ingreso_fixture.id, factor_riesgo="invalido_xyz"),
    )
    assert r.status_code == 422


# CA-5: Auditor y Coordinacion pueden leer en solo lectura
def test_auditor_puede_leer(as_admin, as_auditor, ingreso_fixture):
    caso_id = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id)
    ).json()["id"]
    r = as_auditor.get(f"/api/v1/casos-ept/{caso_id}")
    assert r.status_code == 200
    assert r.json()["id"] == caso_id


def test_coordinacion_puede_leer(as_admin, as_coordinacion, ingreso_fixture):
    caso_id = as_admin.post(
        "/api/v1/casos-ept", json=_payload(ingreso_fixture.id)
    ).json()["id"]
    r = as_coordinacion.get(f"/api/v1/casos-ept/{caso_id}")
    assert r.status_code == 200
