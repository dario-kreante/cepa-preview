"""Tests de CEPA-021: historial clínico farmacológico y esquema."""


def _setup(client) -> tuple[int, int]:
    """Crea un ingreso y un registro farmacológico; devuelve (ingreso_id, registro_id)."""
    ingreso_r = client.post(
        "/api/v1/ingresos",
        json={
            "rut": "11.111.111-1",
            "nombre": "Paciente CEPA-021",
            "sexo": "F",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "F32",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert ingreso_r.status_code == 201, ingreso_r.text
    ingreso_id = ingreso_r.json()["id"]

    reg_r = client.post(
        "/api/v1/registro-farmacologico",
        json={
            "ingreso_id": ingreso_id,
            "medico_tratante": "Dr. Pérez",
            "estado_farmacologico": "activo",
            "antecedentes_previos": "Depresión 2018",
            "tratamiento_previo": "Fluoxetina 20 mg (2018-2020)",
        },
    )
    assert reg_r.status_code == 201, reg_r.text
    return ingreso_id, reg_r.json()["id"]


# TC-021-01: CA-1 — antecedentes y tratamiento previo se guardan
def test_antecedentes_guardados_vinculados_al_folio(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}")
    assert r.status_code == 200
    body = r.json()
    assert "Depresión 2018" in body["antecedentes_previos"]
    assert "Fluoxetina" in body["tratamiento_previo"]


# TC-021-01: CA-2 — indicación actual con medicamento/dosis/frecuencia
def test_agregar_indicacion_actual(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["medicamento"] == "Sertralina"
    assert body["dosis"] == "50 mg"
    assert body["frecuencia"] == "c/24h"
    assert body["extra_sistema"] is False
    assert body["vigente"] is True


# TC-021-02: sin dosis ni frecuencia → 422
def test_indicacion_sin_dosis_rechazada(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina"},
    )
    assert r.status_code == 422
    errores = r.text.lower()
    assert "dosis" in errores or "frecuencia" in errores


# TC-021-03: CA-3 — fármaco extra-sistema aceptado y etiquetado
def test_farmaco_extra_sistema_aceptado(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={
            "medicamento": "Vortioxetina (importado)",
            "dosis": "10 mg",
            "frecuencia": "c/24h",
            "extra_sistema": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["extra_sistema"] is True


# TC-021-04: historial conserva indicaciones previas (versioning)
def test_nueva_indicacion_no_borra_la_previa(as_admin):
    ingreso_id, _ = _setup(as_admin)
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Clonazepam", "dosis": "0.5 mg", "frecuencia": "c/24h"},
    )
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/esquema")
    assert r.status_code == 200
    medicamentos = [i["medicamento"] for i in r.json()]
    assert "Sertralina" in medicamentos
    assert "Clonazepam" in medicamentos


# TC-021-05: Auditor no puede agregar indicación → 403
def test_auditor_no_puede_agregar_indicacion(as_auditor, as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_auditor.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    assert r.status_code == 403


# TC-021-05: Auditor puede leer el esquema → 200
def test_auditor_puede_leer_esquema(as_auditor, as_admin):
    ingreso_id, _ = _setup(as_admin)
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}/esquema")
    assert r.status_code == 200
