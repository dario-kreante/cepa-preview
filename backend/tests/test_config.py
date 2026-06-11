from app.config import Settings


def test_database_url_se_lee_de_la_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_app_name_tiene_default():
    settings = Settings(_env_file=None)
    assert settings.app_name == "Sistema CEPA API"
