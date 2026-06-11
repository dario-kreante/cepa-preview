import os

# Apuntar el motor a la BD de pruebas ANTES de importar la app.
# Si DATABASE_URL ya está definido (CI), gana; si no, se usa la BD local de tests.
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test"),
)

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth.deps import CurrentUser, get_current_user  # noqa: E402
from app.auth.jwt import crear_access_token  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.session import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.ingreso import Ingreso  # noqa: E402
from app.models.paciente import Paciente  # noqa: E402


# --- Ruta de diagnóstico, montada solo bajo tests ---
@app.get("/whoami-test")
def _whoami_test(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role}


def _alembic_config() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _migrated_schema() -> Generator[None, None, None]:
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint" permite que session.commit() del endpoint
    # opere sobre un savepoint sin cerrar la transacción externa, que luego se revierte.
    session = Session(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _sembrar_usuario(db: Session, username: str, rol: str) -> Usuario:
    usuario = Usuario(
        username=username,
        nombre=username.title(),
        hashed_password=hash_password("Clave123!"),
        rol=rol,
        activo=True,
        intentos_fallidos=0,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _cliente_autenticado(client: TestClient, db_session: Session, username: str, rol: str) -> TestClient:
    usuario = _sembrar_usuario(db_session, username, rol)
    token = crear_access_token(user_id=usuario.id, username=usuario.username, role=usuario.rol)
    # Crear un nuevo cliente con headers independientes para cada rol
    authenticated_client = TestClient(app)
    authenticated_client.headers.update({"Authorization": f"Bearer {token}"})
    # Usar el mismo override de BD
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session
    authenticated_client.app.dependency_overrides[get_db] = _override_get_db
    return authenticated_client


@pytest.fixture
def as_coordinacion(client: TestClient, db_session: Session) -> TestClient:
    return _cliente_autenticado(client, db_session, "coord_test", "Coordinacion")


@pytest.fixture
def as_admin(client: TestClient, db_session: Session) -> TestClient:
    return _cliente_autenticado(client, db_session, "admin_test", "Administrativo")


@pytest.fixture
def as_auditor(client: TestClient, db_session: Session) -> TestClient:
    return _cliente_autenticado(client, db_session, "auditor_test", "Auditor")


import datetime  # noqa: E402


@pytest.fixture
def ingreso_fixture(db_session: Session) -> Ingreso:
    """Crea un paciente + ingreso de prueba para tests del módulo EPT."""
    paciente = Paciente(
        rut="123456785",
        nombre="Pedro Soto",
        sexo="M",
        edad=35,
        region="Maule",
    )
    db_session.add(paciente)
    db_session.flush()

    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio="F-2026-TEST",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo",
        estado="activo",
    )
    db_session.add(ingreso)
    db_session.flush()
    return ingreso
