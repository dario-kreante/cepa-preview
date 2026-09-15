from functools import lru_cache
from typing import Literal

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

    # --- Cliente Oracle en modo Thick ---
    # El usuario institucional de UTalca (utcepa01) tiene un verificador de contraseña
    # 0x939, que el modo Thin de python-oracledb no sabe negociar (DPY-3015). Apuntando
    # esta variable al Instant Client se activa el modo Thick, que sí lo soporta.
    # Vacío = modo Thin (por defecto; suficiente para PostgreSQL y para Oracle con
    # verificadores soportados). El directorio debe estar además en LD_LIBRARY_PATH.
    oracle_client_lib_dir: str = ""

    # --- SSO SAML institucional (IdP de UTalca) ---
    # `saml_idp_cert` vacío deja el SP fail-closed: sin certificado no se puede
    # verificar la firma de la aserción, así que el ACS no autentica a nadie.
    saml_sp_entity_id: str = "https://sige-cepa.utalca.cl/saml/metadata"
    saml_sp_acs_url: str = "https://sige-cepa.utalca.cl/api/v1/auth/saml/acs"
    saml_idp_cert: str = ""
    # A dónde vuelve el navegador tras el ACS, con el código de un solo uso.
    frontend_url: str = "http://localhost:5173"

    # --- Entorno de despliegue ---
    # Decide qué atajos de desarrollo se respetan. El valor por defecto es "prod"
    # a propósito: olvidar configurarlo nunca debe abrir nada.
    entorno: Literal["dev", "qa", "prod"] = "prod"

    # --- Acceso UTalca vía huemul (wrapper de SSO institucional) ---
    # huemul devuelve ?id=<RUT>&v=<ticket>, pero `v` es la constante "1": sin validar
    # el token contra UTalca, cualquiera puede escribir el RUT de otra persona.
    #   deshabilitado  -> el callback no autentica a nadie (por defecto)
    #   sin_verificar  -> confía en el RUT; SOLO se respeta con entorno=dev
    #   token          -> exige validar el token contra UTalca (pendiente de DTI)
    sso_huemul_modo: Literal["deshabilitado", "sin_verificar", "token"] = "deshabilitado"
    sso_huemul_login_url: str = "https://huemul.utalca.cl/sso/login.php"
    # URL pública del callback del backend: huemul devuelve el navegador aquí.
    sso_huemul_callback_url: str = "http://localhost:8000/api/v1/auth/sso/callback"

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

    # --- Integración SALUTEM (D12, solo lectura) ---
    # La empresa va en la RUTA, no como parámetro: .../salutem/{empresa}/personas
    # Vacíos = integración deshabilitada; la fábrica devuelve el stub y no se
    # sale a la red (fail-closed, mismo criterio que SMTP y SAML).
    salutem_base_url: str = "https://qa.salutem.cl/api/integraciones/salutem"
    salutem_empresa: str = ""
    salutem_api_key: str = ""
    salutem_timeout_s: float = 30.0

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
