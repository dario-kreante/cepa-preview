from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación. El motor de BD se elige solo aquí, vía DATABASE_URL."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cepa:cepa@localhost:5432/cepa"
    app_name: str = "Sistema CEPA API"

    # --- Autenticación / JWT (EPIC-00, parametrizable; D13) ---
    jwt_secret: str = "cambiar-en-produccion-secreto-jwt-cepa"
    jwt_algorithm: str = "HS256"
    access_token_expira_min: int = 15
    refresh_token_expira_min: int = 60 * 24 * 7  # 7 días

    # --- Bloqueo por intentos fallidos (CEPA-001 RN-3) ---
    login_max_intentos: int = 5
    login_bloqueo_minutos: int = 15

    # --- SMTP para alertas (CEPA-102, D12). Opcionales — si smtp_host está vacío,
    # los correos quedan desactivados y la alerta in-app sigue funcionando (PA6). ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_addr: str = "cepa-alertas@utalca.cl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
