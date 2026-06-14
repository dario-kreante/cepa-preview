"""Configuración de rate limiting con slowapi.

Límite configurable por `rate_limit_per_minute` en Settings (RN-4 de CEPA-120).
Se aplica por dirección IP del cliente (o por token si se extiende el key_func).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.rate_limit_per_minute}/minute"],
)
