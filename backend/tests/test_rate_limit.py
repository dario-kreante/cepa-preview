"""TC-120-04 — rate limiting: N solicitudes → 2xx; N+1 → 429."""


def test_rate_limit_dispara_429_sobre_la_app_real():
    """Primeras 3 solicitudes a la app real → 200; la 4ª → 429.

    Reemplaza temporalmente el limiter en app.state para usar 3/minute,
    lo que evita enviar 60+ solicitudes. El limiter original se restaura
    en el bloque finally para no contaminar otros tests.
    """
    from fastapi.testclient import TestClient
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    from app.main import app

    original_limiter = app.state.limiter
    test_limiter = Limiter(key_func=get_remote_address, default_limits=["3/minute"])
    try:
        app.state.limiter = test_limiter
        with TestClient(app, raise_server_exceptions=False) as c:
            for i in range(3):
                r = c.get("/health")
                assert r.status_code == 200, f"Solicitud {i + 1}/3 falló: {r.status_code}"
            r_extra = c.get("/health")
            assert r_extra.status_code == 429
    finally:
        app.state.limiter = original_limiter


def test_rate_limit_dispara_429_al_exceder_cuota(monkeypatch):
    """Primeras N solicitudes → 200; la N+1 → 429 (app aislada, sin afectar estado global).

    Test sintético con app propia para verificar el comportamiento de slowapi.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    # Crear una app aislada con cuota de 3/minute
    test_app = FastAPI()
    test_limiter = Limiter(key_func=get_remote_address, default_limits=["3/minute"])

    test_app.state.limiter = test_limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)

    @test_app.get("/health")
    def _health():
        return {"status": "ok"}

    with TestClient(test_app, raise_server_exceptions=False) as c:
        for i in range(3):
            r = c.get("/health")
            assert r.status_code == 200, f"Solicitud {i+1}/3 falló: {r.status_code}"
        r_extra = c.get("/health")
        assert r_extra.status_code == 429
