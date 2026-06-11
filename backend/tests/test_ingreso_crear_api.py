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


# TC-010-01
def test_crear_ingreso_genera_folio_y_es_buscable(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload())
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["folio"].startswith("F-")
    assert cuerpo["estado"] == "activo"
    # visible de inmediato en búsqueda por RUT
    b = as_admin.get("/api/v1/pacientes/buscar", params={"q": "12.345.678-5"})
    assert b.status_code == 200
    assert any(p["rut"] == "123456785" for p in b.json())


# TC-010-02: RUT ya existente reutiliza paciente y crea nuevo ingreso
def test_rut_existente_reutiliza_paciente(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(numero_siniestro="S-1"))
    r2 = as_admin.post(
        "/api/v1/ingresos",
        json=_payload(numero_siniestro="S-2", nombre="Juan Pérez Actualizado"),
    )
    assert r2.status_code == 201
    # un solo paciente con ese RUT
    b = as_admin.get("/api/v1/pacientes/buscar", params={"q": "123456785"})
    assert len([p for p in b.json() if p["rut"] == "123456785"]) == 1


# TC-010-03: RUT inválido -> 422, sin crear nada
def test_rut_invalido_rechazado(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(rut="12.345.678-0"))
    assert r.status_code == 422
    assert "rut" in r.text.lower()


# TC-010-04: faltan obligatorios -> 422
def test_campos_obligatorios_faltantes(as_admin):
    incompleto = _payload()
    del incompleto["sexo"]
    del incompleto["diagnostico"]
    r = as_admin.post("/api/v1/ingresos", json=incompleto)
    assert r.status_code == 422


# TC-010-05: tipo de derivación fuera de lista cerrada -> 422
def test_tipo_derivacion_invalido(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(tipo_derivacion="SOCORRO"))
    assert r.status_code == 422


# TC-010-06 / TC-011-06: Auditor no puede crear (solo lectura) -> 403
def test_auditor_no_puede_crear(as_auditor):
    r = as_auditor.post("/api/v1/ingresos", json=_payload())
    assert r.status_code == 403


# TC-011-01: sin folio -> secuencial automático
def test_folio_automatico_cuando_no_se_indica(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload())
    assert r.json()["folio_manual"] is False


# TC-011-02: reingreso con folio manual del mismo paciente (nuevo siniestro)
def test_reingreso_folio_manual_mismo_paciente(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(folio="F-001", numero_siniestro="S-1"))
    r2 = as_admin.post(
        "/api/v1/ingresos",
        json=_payload(folio="F-001", numero_siniestro="S-1", es_reingreso=True),
    )
    assert r2.status_code == 201
    assert r2.json()["folio"] == "F-001"
    assert r2.json()["folio_manual"] is True


# TC-011-04: folio manual colisiona con otro paciente -> 409
def test_folio_manual_colision_otro_paciente(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(rut="12.345.678-5", folio="F-100"))
    r = as_admin.post(
        "/api/v1/ingresos",
        json=_payload(rut="7.876.543-7", nombre="Otra Persona", folio="F-100"),
    )
    assert r.status_code == 409
