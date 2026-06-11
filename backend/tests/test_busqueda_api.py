def _payload(**over):
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
        "fecha_ingreso": "2026-06-10",
    }
    base.update(over)
    return base


# TC-012-01: buscar por RUT
def test_buscar_por_rut(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload())
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "11.111.111-1"})
    assert r.status_code == 200
    assert any(p["rut"] == "111111111" for p in r.json())


# TC-012-02: buscar por folio
def test_buscar_por_folio(as_admin):
    creado = as_admin.post("/api/v1/ingresos", json=_payload(folio="F-555")).json()
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "F-555"})
    assert r.status_code == 200
    assert any(p["id"] == creado["paciente_id"] for p in r.json())


# TC-012-04: sin coincidencias -> lista vacía, sin error
def test_buscar_sin_resultados(as_admin):
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "99.999.999-9"})
    assert r.status_code == 200
    assert r.json() == []


# TC-012-05: nombre parcial con coincidencias múltiples
def test_buscar_por_nombre_parcial(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(rut="11.111.111-1", nombre="Ana González"))
    as_admin.post("/api/v1/ingresos", json=_payload(rut="5.126.663-3", nombre="Pedro González"))
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "González"})
    assert r.status_code == 200
    nombres = {p["nombre"] for p in r.json()}
    assert {"Ana González", "Pedro González"} <= nombres


# CA-1: vista 360 consolida dimensiones
def test_vista_360_consolida(as_admin):
    creado = as_admin.post("/api/v1/ingresos", json=_payload()).json()
    r = as_admin.get(f"/api/v1/pacientes/{creado['paciente_id']}/vista-360")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["paciente"]["rut"] == "111111111"
    assert len(cuerpo["ingresos"]) == 1
    # ranuras de otras épicas presentes (aún vacías)
    for dim in ("farmacos", "licencias", "controles", "reintegro"):
        assert cuerpo[dim] == []


# CA-3: vista 360 de paciente inexistente -> 404
def test_vista_360_inexistente(as_admin):
    r = as_admin.get("/api/v1/pacientes/999999/vista-360")
    assert r.status_code == 404


# TC-012-06: Auditor accede a búsqueda y vista (solo lectura)
def test_auditor_puede_leer(as_admin, as_auditor):
    resp = as_admin.post("/api/v1/ingresos", json=_payload())
    assert resp.status_code == 201, resp.text
    creado = resp.json()
    assert "paciente_id" in creado, f"Response keys: {creado.keys()}"
    assert as_auditor.get("/api/v1/pacientes/buscar", params={"q": "111111111"}).status_code == 200
    assert as_auditor.get(f"/api/v1/pacientes/{creado['paciente_id']}/vista-360").status_code == 200
