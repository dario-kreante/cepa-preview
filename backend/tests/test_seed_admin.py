from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.models.usuario import Usuario
from app.scripts.seed_admin import seed_admin


def test_seed_admin_crea_coordinacion_si_no_existe(db_session: Session):
    creado = seed_admin(db_session, username="root", password="Inicial123!", nombre="Root")
    assert creado is True
    usuario = db_session.scalars(select(Usuario).where(Usuario.username == "root")).one()
    assert usuario.rol == "Coordinacion"
    assert usuario.activo is True
    assert verify_password("Inicial123!", usuario.hashed_password)


def test_seed_admin_es_idempotente(db_session: Session):
    assert seed_admin(db_session, username="root", password="x", nombre="Root") is True
    # segunda corrida no duplica ni falla
    assert seed_admin(db_session, username="root", password="x", nombre="Root") is False
    usuarios = db_session.scalars(select(Usuario).where(Usuario.username == "root")).all()
    assert len(usuarios) == 1
