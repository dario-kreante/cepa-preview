from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación. El motor de BD se elige solo aquí, vía DATABASE_URL."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cepa:cepa@localhost:5432/cepa"
    app_name: str = "Sistema CEPA API"


@lru_cache
def get_settings() -> Settings:
    return Settings()
