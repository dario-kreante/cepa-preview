from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.security import verify_password
from app.config import get_settings
from app.models.usuario import Usuario


class CredencialesInvalidas(Exception):
    """Usuario inexistente, inactivo o contraseña incorrecta."""


class CuentaBloqueada(Exception):
    """La cuenta está temporalmente bloqueada por intentos fallidos."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def autenticar(db: Session, username: str, password: str) -> Usuario:
    """Autentica credenciales aplicando bloqueo por intentos fallidos (CEPA-001).

    No hace commit: el caller (router) decide la transacción. Audita LOGIN / LOGIN_FALLIDO / BLOQUEO.
    """
    settings = get_settings()
    usuario = db.scalars(select(Usuario).where(Usuario.username == username)).one_or_none()

    # Mensaje genérico: nunca se revela si falló el usuario o la clave (TC-001-03).
    if usuario is None or not usuario.activo:
        raise CredencialesInvalidas("Credenciales inválidas")

    # Cuenta bloqueada y la ventana aún no expira.
    if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > _utcnow():
        raise CuentaBloqueada("Cuenta temporalmente bloqueada")

    # Si el bloqueo expiró, se limpia antes de evaluar credenciales.
    if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta <= _utcnow():
        usuario.bloqueado_hasta = None
        usuario.intentos_fallidos = 0

    if not verify_password(password, usuario.hashed_password):
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= settings.login_max_intentos:
            usuario.bloqueado_hasta = _utcnow() + timedelta(
                minutes=settings.login_bloqueo_minutos
            )
            record_audit(
                db,
                actor=usuario.username,
                rol=usuario.rol,
                action="BLOQUEO",
                entity="usuario",
                entity_id=str(usuario.id),
            )
            db.flush()
            raise CuentaBloqueada("Cuenta bloqueada por intentos fallidos")
        record_audit(
            db,
            actor=usuario.username,
            rol=usuario.rol,
            action="LOGIN_FALLIDO",
            entity="usuario",
            entity_id=str(usuario.id),
        )
        db.flush()
        raise CredencialesInvalidas("Credenciales inválidas")

    # Login correcto: resetea contadores y audita.
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    record_audit(
        db,
        actor=usuario.username,
        rol=usuario.rol,
        action="LOGIN",
        entity="usuario",
        entity_id=str(usuario.id),
    )
    db.flush()
    return usuario
