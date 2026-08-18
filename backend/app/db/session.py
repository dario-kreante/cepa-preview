from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.oracle_client import init_oracle_thick

# Debe ejecutarse antes de crear el engine (ver docstring del módulo).
init_oracle_thick()

engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
