"""Activación del modo Thick de python-oracledb.

El usuario institucional de UTalca (``utcepa01``) tiene un verificador de contraseña
0x939, que el modo Thin de python-oracledb no sabe negociar y falla con ``DPY-3015``.
El modo Thick sí lo soporta, pero necesita las librerías del Oracle Instant Client.

Lo usan tanto la app (``app.db.session``) como las migraciones (``migrations/env.py``),
porque Alembic construye su propio engine y no pasa por el módulo de sesión.
"""

from app.config import get_settings

_inicializado = False


def init_oracle_thick() -> bool:
    """Inicializa el cliente Oracle en modo Thick si corresponde.

    Debe invocarse antes de crear el engine: ``init_oracle_client`` afecta al proceso
    completo y no puede llamarse una vez abierta la primera conexión. Es idempotente.

    No hace nada si el motor no es Oracle o si no se configuró
    ``Settings.oracle_client_lib_dir`` — así, PostgreSQL y los tests no se ven afectados.

    Returns:
        True si se activó el modo Thick; False si se omitió.
    """
    global _inicializado

    if _inicializado:
        return True

    settings = get_settings()
    if not settings.oracle_client_lib_dir or not settings.database_url.startswith("oracle"):
        return False

    import oracledb

    oracledb.init_oracle_client(lib_dir=settings.oracle_client_lib_dir)
    _inicializado = True
    return True
