from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación. El motor de BD se elige solo aquí, vía DATABASE_URL."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cepa:cepa@localhost:5432/cepa"
    app_name: str = "Sistema CEPA API"

    @field_validator("database_url")
    @classmethod
    def _normalizar_driver(cls, v: str) -> str:
        """Los PaaS (Render/Railway/Fly/Heroku) entregan DATABASE_URL como
        ``postgres://`` o ``postgresql://`` sin driver. SQLAlchemy 2.0 necesita el
        driver explícito; normalizamos a psycopg v3 sin tocar el resto de la URL.
        Las URLs de Oracle (``oracle+oracledb://``) u otras con driver se dejan tal cual.
        """
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

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

    # --- Rate limiting (CEPA-120 RN-4) ---
    rate_limit_per_minute: int = 60

    # --- IMED feature flag (CEPA-122, P2, PA5) ---
    imed_enabled: bool = False

    # --- CORS (integración frontend) ---
    cors_origins: str = "http://localhost:5173,http://localhost:4173,https://cepa-preview.vercel.app"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
