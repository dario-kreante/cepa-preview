"""TC-120-01, TC-120-02, TC-120-03, TC-120-05, TC-120-06 — versionado, auth JWT y OpenAPI."""


def test_v1_endpoint_requiere_jwt_valido(as_admin):
    """TC-120-01: token JWT válido → 200."""
    r = as_admin.get("/api/v1/ingresos")
    assert r.status_code == 200


def test_sin_token_devuelve_401(client):
    """TC-120-02: sin header Authorization → 401."""
    r = client.get("/api/v1/ingresos")
    assert r.status_code == 401


def test_token_invalido_devuelve_401(client):
    """TC-120-03: token malformado → 401."""
    r = client.get("/api/v1/ingresos", headers={"Authorization": "Bearer tokeninvalido"})
    assert r.status_code == 401


def test_v2_existe_y_v1_sigue_operativa(client, as_admin):
    """TC-120-06: v1 y v2 coexisten sin romperse."""
    r_v2 = client.get("/api/v2/health")
    assert r_v2.status_code == 200
    assert r_v2.json()["version"] == "v2"

    r_v1 = as_admin.get("/api/v1/ingresos")
    assert r_v1.status_code == 200


def test_openapi_cubre_100_pct_endpoints(client):
    """TC-120-05: la spec OpenAPI lista todos los endpoints expuestos.

    Verifica que /api/v1/ingresos, /api/v1/pacientes, /api/v1/fichas,
    /api/v1/licencias, /api/v2/health estén en la spec.
    Criterio OI3: ningún endpoint sin documentar.
    """
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for ruta_esperada in [
        "/api/v1/ingresos",
        "/api/v1/pacientes/buscar",
        "/api/v1/fichas-clinicas",
        "/api/v1/licencias/{folio}",
        "/api/v2/health",
        "/health",
    ]:
        assert ruta_esperada in paths, f"Endpoint {ruta_esperada!r} no documentado en OpenAPI"
