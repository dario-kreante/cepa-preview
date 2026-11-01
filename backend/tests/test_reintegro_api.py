"""Tests de integración — CEPA-040: Datos del caso de reintegro."""


def _ingreso_fixture(as_admin):
    """Crea un ingreso real en la BD de tests para usar como FK."""
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
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
        },
    )
    assert r.status_code == 201, f"Fallo al crear ingreso fixture: {r.text}"
    return r.json()["id"]


def _payload_caso(ingreso_id: int, **over):
    base = {
        "ingreso_id": ingreso_id,
        "rut": "12.345.678-5",
        "nombre": "Juan Pérez",
        "tipo_derivacion": "DIAT",
        "fecha_caso": "2026-06-10",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
    }
    base.update(over)
    return base


# TC-040-01: crear caso con RUT existente — datos obligatorios completos
def test_crear_caso_reintegro_exitoso(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["rut"] == "123456785"  # normalizado
    assert cuerpo["estado_reintegro"] == "pendiente"
    assert cuerpo["ingreso_id"] == ingreso_id


# TC-040-01 (bis): caso vinculado al ingreso y visible en GET
def test_caso_creado_es_visible(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    create_r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    caso_id = create_r.json()["id"]
    get_r = as_admin.get(f"/api/v1/reintegros/{caso_id}")
    assert get_r.status_code == 200
    assert get_r.json()["id"] == caso_id


# TC-040-02: tipo de derivación válido de la lista D4
def test_tipo_derivacion_reingreso_fump(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, tipo_derivacion="Reingreso FUMP"),
    )
    assert r.status_code == 201
    assert r.json()["tipo_derivacion"] == "Reingreso FUMP"


# TC-040-03: RUT con DV inválido → 422
def test_rut_invalido_rechazado(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, rut="12.345.678-0"),
    )
    assert r.status_code == 422
    assert "rut" in r.text.lower()


# TC-040-04: campos obligatorios faltantes → 422
def test_campos_obligatorios_faltantes(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    datos = _payload_caso(ingreso_id)
    del datos["region"]
    r = as_admin.post("/api/v1/reintegros", json=datos)
    assert r.status_code == 422


# TC-040-04 (bis): tipo_derivacion inválido ("SOCORRO" no es válido en D4)
def test_tipo_derivacion_invalido_rechazado(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, tipo_derivacion="SOCORRO"),
    )
    assert r.status_code == 422


# TC-040-06: Auditor no puede crear → 403
def test_auditor_no_puede_crear(as_auditor):
    r = as_auditor.post(
        "/api/v1/reintegros",
        json={"ingreso_id": 1, "rut": "12.345.678-5", "nombre": "X",
              "tipo_derivacion": "DIAT", "fecha_caso": "2026-06-10",
              "sexo": "M", "edad": 40, "region": "Maule"},
    )
    assert r.status_code == 403


# Coordinacion puede crear
def test_coordinacion_puede_crear(as_coordinacion):
    ingreso_id = _ingreso_fixture(as_coordinacion)
    r = as_coordinacion.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    assert r.status_code == 201


# Auditor puede leer (solo lectura)
def test_auditor_puede_leer(as_admin, as_auditor):
    ingreso_id = _ingreso_fixture(as_admin)
    create_r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    caso_id = create_r.json()["id"]
    r = as_auditor.get(f"/api/v1/reintegros/{caso_id}")
    assert r.status_code == 200


# Listar por ingreso_id
def test_listar_casos_por_ingreso(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    r = as_admin.get("/api/v1/reintegros", params={"ingreso_id": ingreso_id})
    assert r.status_code == 200
    assert len(r.json()) >= 1


# RN-5: auditoría registrada (verificación indirecta — el endpoint no falla)
def test_operacion_create_no_falla_sin_auditoria_error(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    assert r.status_code == 201


# QA Pilar 22-10 QA-008: sin RUT en el formulario se usa el del paciente del ingreso
def test_sin_rut_toma_el_del_paciente(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    datos = _payload_caso(ingreso_id)
    del datos["rut"]
    r = as_admin.post("/api/v1/reintegros", json=datos)
    assert r.status_code == 201, r.text
    assert r.json()["rut"] == "123456785"


# QA Pilar 22-10 QA-008: paciente de SALUTEM sin RUT → el caso se crea igual
def test_paciente_sin_rut_permite_crear_caso(as_admin, db_session):
    from datetime import date

    from app.models.ingreso import Ingreso
    from app.models.paciente import Paciente

    paciente = Paciente(rut=None, nombre="Paciente Sin Rut", sexo="F", edad=30, region="Maule")
    db_session.add(paciente)
    db_session.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio="SR-0001",
        fecha_ingreso=date(2026, 10, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="x",
        estado="activo",
    )
    db_session.add(ingreso)
    db_session.commit()
    datos = _payload_caso(ingreso.id, rut="", nombre="Paciente Sin Rut", sexo="F")
    r = as_admin.post("/api/v1/reintegros", json=datos)
    assert r.status_code == 201, r.text
    assert r.json()["rut"] is None


# QA Pilar 22-10 QA-008: el alta ya no pide edad ni sexo; se copian del paciente
def test_sin_sexo_ni_edad_toma_los_del_paciente(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    datos = _payload_caso(ingreso_id, tipo_trabajador="dependiente")
    del datos["sexo"]
    del datos["edad"]
    r = as_admin.post("/api/v1/reintegros", json=datos)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["sexo"] == "M"
    assert cuerpo["edad"] == 40
    assert cuerpo["tipo_trabajador"] == "dependiente"


def _ingreso_directo(db_session, *, razon_social=None, sexo=None, edad=None):
    from datetime import date

    from app.models.ingreso import Ingreso
    from app.models.paciente import Paciente

    paciente = Paciente(rut=None, nombre="Paciente QA", sexo=sexo, edad=edad, region="Maule")
    db_session.add(paciente)
    db_session.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio=f"QA8-{paciente.id}",
        fecha_ingreso=date(2026, 10, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="x",
        estado="activo",
        razon_social=razon_social,
    )
    db_session.add(ingreso)
    db_session.commit()
    return ingreso.id


# QA-008: paciente sin sexo ni edad → el caso se crea igual, con esos datos vacíos
def test_paciente_sin_sexo_ni_edad_permite_crear_caso(as_admin, db_session):
    ingreso_id = _ingreso_directo(db_session)
    datos = _payload_caso(ingreso_id, rut="")
    del datos["sexo"]
    del datos["edad"]
    r = as_admin.post("/api/v1/reintegros", json=datos)
    assert r.status_code == 201, r.text
    assert r.json()["sexo"] is None
    assert r.json()["edad"] is None


# QA-008: sin razón social en el alta se toma la del ingreso
def test_sin_razon_social_toma_la_del_ingreso(as_admin, db_session):
    ingreso_id = _ingreso_directo(db_session, razon_social="Forestal Maule SpA")
    r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id, rut=""))
    assert r.status_code == 201, r.text
    assert r.json()["razon_social"] == "Forestal Maule SpA"


# QA-008: la razón social indicada en el alta gana sobre la del ingreso
def test_razon_social_explicita_gana(as_admin, db_session):
    ingreso_id = _ingreso_directo(db_session, razon_social="Forestal Maule SpA")
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, rut="", razon_social="Otra Empresa Ltda."),
    )
    assert r.status_code == 201, r.text
    assert r.json()["razon_social"] == "Otra Empresa Ltda."


# QA-008: tipo de trabajador fuera de la lista → 422
def test_tipo_trabajador_invalido_rechazado(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, tipo_trabajador="honorarios"),
    )
    assert r.status_code == 422


# QA-008: tipo de trabajador y razón social se editan por PATCH
def test_patch_tipo_trabajador_y_razon_social(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    caso_id = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id)).json()["id"]
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}",
        json={"tipo_trabajador": "independiente", "razon_social": "Mi Empresa"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["tipo_trabajador"] == "independiente"
    assert r.json()["razon_social"] == "Mi Empresa"
