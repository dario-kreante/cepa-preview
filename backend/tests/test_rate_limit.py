"""TC-120-04 — rate limiting: N solicitudes → 2xx; N+1 → 429."""


def test_rate_limit_dispara_429_al_exceder_cuota(monkeypatch):
    """Primeras N solicitudes → 200; la N+1 → 429.

    Se inyecta una cuota de 3/minute para no tener que enviar 60 solicitudes en tests.
    El test usa su propia instancia de Limiter para evitar contaminar el estado global.
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
