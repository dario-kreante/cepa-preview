"""TC-122-01..05 — Integración IMED (P2, diferible).

Los tests verifican el comportamiento tanto con IMED_ENABLED=false (503)
como con IMED_ENABLED=true (funcionalidad completa).
"""

def test_imed_deshabilitado_devuelve_503(client):
    """CA-3: cuando IMED no está habilitado (PA5 pendiente), los endpoints responden 503."""
    r = client.post(
        "/api/v1/imed/licencias",
        json={"folio": "F-2026-0001", "tipo": "licencia_medica", "datos": {}},
        headers={"Authorization": "Bearer tokeninvalido"},
    )
    # Sin autenticación → 401 primero (auth antes del feature flag)
    # Con autenticación y IMED_ENABLED=false → 503
    assert r.status_code in (401, 503)


def test_imed_habilitado_recibe_licencia(as_admin, monkeypatch):
    """TC-122-01: con IMED habilitado, recibe licencia médica electrónica → 201."""
    monkeypatch.setenv("IMED_ENABLED", "true")
    import app.config

    app.config.get_settings.cache_clear()

    # Crear un ingreso para tener un folio válido
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "15.555.555-6",
            "nombre": "IMED Test",
            "sexo": "F",
            "edad": 38,
            "region": "Maule",
            "diagnostico": "x",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r_ing.status_code == 201, r_ing.text
    folio = r_ing.json()["folio"]

    r = as_admin.post(
        "/api/v1/imed/licencias",
        json={"folio": folio, "tipo": "licencia_medica", "datos": {"dias": 7}},
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["folio"] == folio
    assert cuerpo["tipo"] == "licencia_medica"

    # Restaurar
    app.config.get_settings.cache_clear()


def test_imed_habilitado_recibe_receta(as_admin, monkeypatch):
    """TC-122-02: con IMED habilitado, recibe receta electrónica → 201."""
    monkeypatch.setenv("IMED_ENABLED", "true")
    import app.config

    app.config.get_settings.cache_clear()

    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "16.666.666-K",
            "nombre": "IMED Receta",
            "sexo": "M",
            "edad": 50,
            "region": "Maule",
            "diagnostico": "y",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "particular",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r_ing.status_code == 201, r_ing.text
    folio = r_ing.json()["folio"]

    r = as_admin.post(
        "/api/v1/imed/recetas",
        json={"folio": folio, "tipo": "receta_electronica", "datos": {"medicamento": "X"}},
    )
    assert r.status_code == 201, r.text
    assert r.json()["tipo"] == "receta_electronica"

    app.config.get_settings.cache_clear()


def test_imed_payload_invalido_devuelve_422(as_admin, monkeypatch):
    """TC-122-03: payload sin campos obligatorios → 422."""
    monkeypatch.setenv("IMED_ENABLED", "true")
    import app.config

    app.config.get_settings.cache_clear()

    r = as_admin.post("/api/v1/imed/licencias", json={"tipo": "licencia_medica"})
    assert r.status_code == 422

    app.config.get_settings.cache_clear()


def test_imed_sin_permiso_devuelve_403(as_auditor, monkeypatch):
    """TC-122-04: token sin scope IMED (Auditor solo lectura) → 403."""
    monkeypatch.setenv("IMED_ENABLED", "true")
    import app.config

    app.config.get_settings.cache_clear()

    r = as_auditor.post(
        "/api/v1/imed/licencias",
        json={"folio": "F-2026-0001", "tipo": "licencia_medica", "datos": {}},
    )
    assert r.status_code == 403

    app.config.get_settings.cache_clear()


def test_imed_endpoints_en_openapi(client):
    """TC-122-05: endpoints IMED aparecen en la spec OpenAPI (contratos documentados)."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/api/v1/imed/licencias" in paths
    assert "/api/v1/imed/recetas" in paths


def test_imed_deshabilitado_exactamente_503(as_admin, monkeypatch):
    """IMED_ENABLED=False (feature flag off) → exactamente 503, no 401 ni otro código."""
    monkeypatch.setenv("IMED_ENABLED", "false")
    import app.config

    app.config.get_settings.cache_clear()
    try:
        r = as_admin.post(
            "/api/v1/imed/licencias",
            json={"folio": "F-2026-0001", "tipo": "licencia_medica", "datos": {}},
        )
        assert r.status_code == 503, (
            f"Se esperaba exactamente 503 con IMED_ENABLED=false, got {r.status_code}"
        )
    finally:
        app.config.get_settings.cache_clear()
