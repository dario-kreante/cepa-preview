from app.config import Settings


def test_parametros_de_auth_tienen_defaults():
    settings = Settings(_env_file=None)
    assert settings.jwt_secret  # hay un secreto por defecto (override en prod)
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expira_min == 15
    assert settings.refresh_token_expira_min == 60 * 24 * 7
    assert settings.login_max_intentos == 5
    assert settings.login_bloqueo_minutos == 15


def test_parametros_de_auth_se_leen_del_entorno(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "supersecreto-de-prod")
    monkeypatch.setenv("LOGIN_MAX_INTENTOS", "3")
    settings = Settings(_env_file=None)
    assert settings.jwt_secret == "supersecreto-de-prod"
    assert settings.login_max_intentos == 3
