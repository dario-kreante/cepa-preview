"""Tests de CORS — no requieren BD (health no tiene dependencia de DB)."""
from fastapi.testclient import TestClient

from app.main import app


def test_cors_permite_origen_configurado():
    with TestClient(app) as client:
        r = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
