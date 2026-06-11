"""Bootstrap: crea el primer usuario de Coordinación si no existe.

Uso (desde backend/):
    uv run python -m app.scripts.seed_admin --username root --password 'CAMBIAR' --nombre 'Coordinación'
"""
import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models.usuario import Usuario


def seed_admin(db: Session, *, username: str, password: str, nombre: str) -> bool:
    """Crea un usuario Coordinación si el username no existe. Devuelve True si lo creó."""
    existe = db.scalars(select(Usuario).where(Usuario.username == username)).one_or_none()
    if existe is not None:
        return False
    usuario = Usuario(
        username=username,
        nombre=nombre,
        hashed_password=hash_password(password),
        rol="Coordinacion",
        activo=True,
        intentos_fallidos=0,
    )
    db.add(usuario)
    db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed del usuario inicial de Coordinación")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--nombre", default="Coordinación")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        creado = seed_admin(db, username=args.username, password=args.password, nombre=args.nombre)
        print("Usuario creado." if creado else "El usuario ya existía; no se hizo nada.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
