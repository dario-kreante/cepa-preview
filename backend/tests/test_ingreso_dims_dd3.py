"""Tests DD-3 (EPIC-09 rework): dimensiones desde Paciente + población en crear_ingreso.

TC-DD3-01: POST /ingresos con programa/tipo_convenio → aparece en dashboard filtros.
TC-DD3-02: filtro por sexo vía Paciente join retorna solo ingresos correctos.
TC-DD3-03: filtro por region vía Paciente join funciona.
TC-DD3-04: filtro por tramo_etario derivado de paciente.edad funciona.
"""

# RUTs válidos computados algorítmicamente para este módulo de tests
_RUT_A = "10000000-8"
_RUT_B = "11000001-4"
_RUT_C = "12000002-0"
_RUT_D = "13000003-7"


# ── TC-DD3-01: crear ingreso con programa, luego filtrarlo en dashboard ───────

def test_ingreso_con_programa_aparece_en_dashboard(as_coordinacion):
    """DD-3: programa poblado en crear_ingreso via POST y filtrable en dashboard."""
    payload = {
        "rut": _RUT_A,
        "nombre": "Test Dims",
        "sexo": "M",
        "edad": 38,
        "region": "Maule",
        "diagnostico": "Test DD3",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-04-01",
        "programa": "DIEP",
        "tipo_convenio": "DIEP",
        "profesional_id": 5,
    }
    resp = as_coordinacion.post("/api/v1/ingresos", json=payload)
    assert resp.status_code == 201

    # Dashboard filtrado por programa
    resp_dash = as_coordinacion.get("/api/v1/dashboard", params={"programa": "DIEP"})
    assert resp_dash.status_code == 200
    body = resp_dash.json()
    assert body["total_ingresos"] >= 1
    assert body["filtros_aplicados"]["programa"] == "DIEP"


# ── TC-DD3-02: filtro sexo via Paciente join ──────────────────────────────────

def test_dashboard_filtro_sexo_via_paciente(as_coordinacion):
    """DD-3: dashboard filtra por sexo accediendo a Paciente (no ingreso.sexo)."""
    # Crear ingreso con paciente femenino
    payload_f = {
        "rut": _RUT_B,
        "nombre": "Femenino DD3",
        "sexo": "F",
        "edad": 25,
        "region": "Maule",
        "diagnostico": "Test",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-04-01",
    }
    as_coordinacion.post("/api/v1/ingresos", json=payload_f)

    resp = as_coordinacion.get("/api/v1/dashboard", params={"sexo": "F"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] >= 1

    # Filtro por sexo inexistente → 0
    resp_inex = as_coordinacion.get("/api/v1/dashboard", params={"sexo": "X"})
    assert resp_inex.status_code == 200
    assert resp_inex.json()["total_ingresos"] == 0


# ── TC-DD3-03: filtro region via Paciente join ───────────────────────────────

def test_dashboard_filtro_region_via_paciente(as_coordinacion):
    """DD-3: región del paciente es accesible para filtros de dashboard."""
    payload = {
        "rut": _RUT_C,
        "nombre": "Region Test",
        "sexo": "M",
        "edad": 45,
        "region": "BioBioDD3",
        "diagnostico": "Test",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-04-01",
    }
    as_coordinacion.post("/api/v1/ingresos", json=payload)

    resp = as_coordinacion.get("/api/v1/dashboard", params={"region": "BioBioDD3"})
    assert resp.status_code == 200
    assert resp.json()["total_ingresos"] >= 1

    resp_nada = as_coordinacion.get("/api/v1/dashboard", params={"region": "INEXISTENTE_XYZ"})
    assert resp_nada.json()["total_ingresos"] == 0


# ── TC-DD3-04: filtro tramo_etario derivado de edad ──────────────────────────

def test_dashboard_filtro_tramo_etario_derivado(as_coordinacion):
    """DD-3: tramo_etario derivado de paciente.edad en tiempo de consulta."""
    # Crear paciente con edad 25 → tramo 18-29
    payload = {
        "rut": _RUT_D,
        "nombre": "Tramo Test",
        "sexo": "F",
        "edad": 25,
        "region": "Maule",
        "diagnostico": "Test",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-04-01",
    }
    as_coordinacion.post("/api/v1/ingresos", json=payload)

    resp = as_coordinacion.get("/api/v1/dashboard", params={"tramo_etario": "18-29"})
    assert resp.status_code == 200
    assert resp.json()["total_ingresos"] >= 1

    # Tramo inexistente → 0
    resp_nada = as_coordinacion.get("/api/v1/dashboard", params={"tramo_etario": "0-5"})
    assert resp_nada.status_code == 200
    assert resp_nada.json()["total_ingresos"] == 0
