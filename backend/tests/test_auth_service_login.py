import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.auth.service import (
    CredencialesInvalidas,
    CuentaBloqueada,
    autenticar,
)
from app.models.audit_log import AuditLog
from app.models.usuario import Usuario


def _crear(db: Session, username="maria", rol="Coordinacion", activo=True) -> Usuario:
    u = Usuario(
        username=username,
        nombre="Maria",
        hashed_password=hash_password("Clave123!"),
        rol=rol,
        activo=activo,
        intentos_fallidos=0,
    )
    db.add(u)
    db.flush()
    return u


def test_login_correcto_resetea_intentos_y_audita(db_session: Session):
    u = _crear(db_session)
    usuario = autenticar(db_session, "maria", "Clave123!")
    assert usuario.id == u.id
    assert usuario.intentos_fallidos == 0
    trazas = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "LOGIN", AuditLog.actor == "maria")
    ).all()
    assert len(trazas) == 1


def test_login_incorrecto_incrementa_intentos_y_audita(db_session: Session):
    _crear(db_session)
    with pytest.raises(CredencialesInvalidas):
        autenticar(db_session, "maria", "mala-clave")
    u = db_session.scalars(select(Usuario).where(Usuario.username == "maria")).one()
    assert u.intentos_fallidos == 1
    trazas = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "LOGIN_FALLIDO")
    ).all()
    assert len(trazas) == 1


def test_login_se_bloquea_al_alcanzar_el_maximo(db_session: Session, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "login_max_intentos", 3)
    _crear(db_session)
    for _ in range(2):
        with pytest.raises(CredencialesInvalidas):
            autenticar(db_session, "maria", "mala")
    # 3er intento fallido alcanza el máximo -> bloquea
    with pytest.raises(CuentaBloqueada):
        autenticar(db_session, "maria", "mala")
    u = db_session.scalars(select(Usuario).where(Usuario.username == "maria")).one()
    assert u.bloqueado_hasta is not None
    trazas = db_session.scalars(select(AuditLog).where(AuditLog.action == "BLOQUEO")).all()
    assert len(trazas) == 1


def test_cuenta_bloqueada_rechaza_incluso_con_clave_correcta(db_session: Session, monkeypatch):
    from datetime import datetime, timedelta, timezone

    u = _crear(db_session)
    u.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=10)
    db_session.flush()
    with pytest.raises(CuentaBloqueada):
        autenticar(db_session, "maria", "Clave123!")


def test_usuario_desactivado_no_puede_autenticar(db_session: Session):
    _crear(db_session, activo=False)
    with pytest.raises(CredencialesInvalidas):
        autenticar(db_session, "maria", "Clave123!")
