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


def _paciente_de_prueba_salutem(as_admin, db_session):
    """Paciente del CEPA asociado a una persona de SALUTEM sin RUT (sin_id)."""
    from app.integrations.salutem.models import PersonaSalutem
    from app.models.paciente import Paciente
    from app.services.salutem_sync import copia
    from tests.salutem_sync.conftest import AHORA

    creado = as_admin.post("/api/v1/ingresos", json=_payload(rut="39.000.001-4", nombre="Paciente Prueba")).json()
    copia.guardar_persona(
        db_session,
        PersonaSalutem.desde_api(
            {"SALUTEM_ID": 1332404, "identificacion": "sin_id_1216018", "tipoIdentificacion": "SIN IDENTIFICACION"}
        ),
        AHORA,
    )
    db_session.get(Paciente, creado["paciente_id"]).salutem_persona_id = 1332404
    db_session.flush()
    return creado["paciente_id"]


def test_buscar_por_sin_id_de_salutem(as_admin, db_session):
    paciente_id = _paciente_de_prueba_salutem(as_admin, db_session)
    for termino in ("sin_id_1216018", "SIN_ID_1216018", " sin_id_1216018 "):
        r = as_admin.get("/api/v1/pacientes/buscar", params={"q": termino})
        assert r.status_code == 200
        assert [p["id"] for p in r.json()] == [paciente_id]


def test_buscar_por_id_de_persona_salutem(as_admin, db_session):
    paciente_id = _paciente_de_prueba_salutem(as_admin, db_session)
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "1332404"})
    assert r.status_code == 200
    assert paciente_id in [p["id"] for p in r.json()]


def test_sin_id_inexistente_devuelve_lista_vacia(as_admin, db_session):
    _paciente_de_prueba_salutem(as_admin, db_session)
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "sin_id_999"})
    assert r.status_code == 200
    assert r.json() == []
