# Backend Foundation (FastAPI + SQLAlchemy, portable Oracle⇄Postgres) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levantar el esqueleto del backend del Sistema CEPA con FastAPI + SQLAlchemy 2.0 + Alembic, portable entre PostgreSQL y Oracle, con tests contra Postgres real y CI dual-target, dejando todo preparado para construir las épicas encima.

**Architecture:** Backend Python en `backend/`, gestionado con `uv`. La capa de datos vive aislada en `app/db/` (único lugar que conoce el motor, vía `DATABASE_URL`). Todo el dominio habla SQLAlchemy con tipos genéricos. Migraciones Alembic portables. Una tabla demostradora (`audit_log`, append-only) recorre todo el stack end-to-end (modelo → migración → endpoint → test sobre Postgres real). CI corre la suite contra Postgres (obligatorio) y contra Oracle free (gated).

**Tech Stack:** Python 3.12 (vía uv), FastAPI, SQLAlchemy 2.0, Alembic, pydantic-settings, psycopg v3 (Postgres), python-oracledb (Oracle), pytest, httpx, ruff. GitHub Actions. Docker Compose (solo para despliegue de contingencia en servidor).

**Referencia de diseño:** `docs/superpowers/specs/2026-06-10-portabilidad-bd-postgres-fallback-design.md` (D14 FastAPI, D15 portabilidad).

**Convención de ejecución:** salvo que se indique lo contrario, **todos los comandos se ejecutan desde `backend/`** y con `uv run …`. uv instalará Python 3.12 y creará `.venv` automáticamente en el primer `uv sync`.

---

### Task 1: Scaffolding del proyecto backend

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py` (vacío)
- Create: `backend/tests/__init__.py` (vacío)
- Create: `backend/tests/test_smoke.py`
- Modify: `.gitignore` (raíz del repo)

- [ ] **Step 1: Crear `backend/pyproject.toml`**

```toml
[project]
name = "cepa-backend"
version = "0.1.0"
description = "Backend del Sistema CEPA (FastAPI, portable Oracle/Postgres)"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0.30",
    "alembic>=1.13",
    "pydantic-settings>=2.3",
    "psycopg[binary]>=3.2",
    "oracledb>=2.2",
]

[dependency-groups]
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: Fijar la versión de Python para uv**

Crear `backend/.python-version` con el contenido:

```
3.12
```

- [ ] **Step 3: Crear `backend/.env.example`**

```bash
# Motor de base de datos. Postgres en dev/CI; Oracle en producción.
# Postgres (psycopg v3):
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa
# Oracle (python-oracledb, thin mode) — ejemplo para producción:
# DATABASE_URL=oracle+oracledb://usuario:clave@host:1521/?service_name=NOMBRE_PDB
```

- [ ] **Step 4: Crear los paquetes vacíos**

Crear `backend/app/__init__.py` y `backend/tests/__init__.py`, ambos vacíos (archivo sin contenido).

- [ ] **Step 5: Escribir un test de humo**

Crear `backend/tests/test_smoke.py`:

```python
def test_smoke():
    assert True
```

- [ ] **Step 6: Añadir entradas de backend a `.gitignore` de la raíz**

El `.gitignore` de la raíz hoy contiene exactamente:

```
.claude/
.DS_Store
node_modules/
```

Reemplazarlo por:

```
.claude/
.DS_Store
node_modules/

# Backend (Python / uv)
backend/.venv/
__pycache__/
*.pyc
backend/.env
.pytest_cache/
.ruff_cache/
```

Nota: `backend/uv.lock` SÍ se versiona (no lo ignores).

- [ ] **Step 7: Instalar dependencias y correr el test de humo**

Run (desde `backend/`):
```bash
uv sync
uv run pytest
```
Expected: uv crea `.venv` y `uv.lock`; pytest reporta `1 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/ .gitignore
git commit -m "chore(backend): scaffolding FastAPI + uv (Python 3.12)"
```

---

### Task 2: Módulo de configuración (`Settings`)

**Files:**
- Create: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_config.py`:

```python
from app.config import Settings


def test_database_url_se_lee_de_la_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_app_name_tiene_default():
    settings = Settings(_env_file=None)
    assert settings.app_name == "Sistema CEPA API"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 3: Implementar `app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación. El motor de BD se elige solo aquí, vía DATABASE_URL."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cepa:cepa@localhost:5432/cepa"
    app_name: str = "Sistema CEPA API"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_config.py -v`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat(backend): módulo de configuración con DATABASE_URL"
```

---

### Task 3: Capa de datos — Base declarativa y sesión

**Files:**
- Create: `backend/app/db/__init__.py` (vacío)
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Test: `backend/tests/test_session.py`

**Precondición de entorno (una sola vez):** tener Postgres local corriendo (Homebrew) y las bases creadas. Desde una terminal normal:
```bash
brew services start postgresql@16
psql postgres -c "CREATE ROLE cepa LOGIN PASSWORD 'cepa';"
createdb -O cepa cepa
createdb -O cepa cepa_test
```

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_session.py`:

```python
from sqlalchemy import text

from app.db.session import get_db


def test_get_db_entrega_una_sesion_funcional():
    gen = get_db()
    db = next(gen)
    try:
        assert db.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        gen.close()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_session.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.db.session'`.

- [ ] **Step 3: Implementar la capa de datos**

Crear `backend/app/db/__init__.py` vacío.

Crear `backend/app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos del dominio CEPA."""
```

Crear `backend/app/db/session.py` (único módulo que conoce el motor):

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run pytest tests/test_session.py -v`
Expected: `1 passed` (la conexión a Postgres responde `SELECT 1`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/
git add backend/tests/test_session.py
git commit -m "feat(backend): capa de datos aislada (Base declarativa + sesión SQLAlchemy)"
```

---

### Task 4: Aplicación FastAPI con endpoint de salud

**Files:**
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_responde_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_health.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Implementar `app/main.py` (solo health por ahora)**

```python
from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title=get_settings().app_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_health.py -v`
Expected: `1 passed`.

- [ ] **Step 5: Levantar el servidor manualmente (verificación opcional)**

Run: `uv run uvicorn app.main:app --reload`
Expected: arranca en `http://127.0.0.1:8000`; `GET /health` devuelve `{"status":"ok"}`; `GET /docs` muestra Swagger UI. Detener con Ctrl-C.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_health.py
git commit -m "feat(backend): app FastAPI con endpoint /health"
```

---

### Task 5: Modelo `AuditLog` (aplica reglas de portabilidad)

Tabla demostradora append-only. Su test verifica las reglas anti-lock-in del diseño (identificadores en minúscula y ≤30 chars, PK por `Identity`, tipos genéricos).

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/audit_log.py`
- Test: `backend/tests/test_audit_log_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_audit_log_model.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, String

from app.models.audit_log import AuditLog


def test_tabla_y_columnas_esperadas():
    tabla = AuditLog.__table__
    assert tabla.name == "audit_log"
    assert set(tabla.columns.keys()) == {
        "id",
        "actor",
        "action",
        "entity",
        "entity_id",
        "created_at",
    }


def test_reglas_de_portabilidad_en_identificadores():
    tabla = AuditLog.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera el límite de 30 chars de Oracle"


def test_tipos_genericos_y_pk_identity():
    cols = AuditLog.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None  # PK por Identity, no SERIAL ni secuencia manual
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["actor"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True  # fechas con zona (UTC)


def test_default_created_at_es_utc():
    default = AuditLog.__table__.columns["created_at"].default
    assert default is not None and default.is_callable
    valor = default.arg()
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_audit_log_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.audit_log'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/audit_log.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Traza append-only de operaciones. Demostrador de las reglas de portabilidad (D15).

    La inmutabilidad completa y el RBAC de CEPA-003 se implementan en su épica;
    aquí solo establecemos el modelo portable y append-only.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    entity: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
```

Crear `backend/app/models/__init__.py` (registra los modelos para Alembic):

```python
from app.models.audit_log import AuditLog  # noqa: F401
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_audit_log_model.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/
git add backend/tests/test_audit_log_model.py
git commit -m "feat(backend): modelo AuditLog portable (Identity, tipos genéricos, UTC)"
```

---

### Task 6: Alembic + migración inicial + conftest (schema vía migraciones)

A partir de aquí los tests integran contra una BD migrada. `conftest.py` aplica las migraciones (no `create_all`), de modo que **cada corrida de tests ejercita las migraciones** — esto es lo que mantiene el fallback probado.

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_crear_audit_log.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_migrations.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_migrations.py`:

```python
from sqlalchemy import inspect

from app.db.session import engine


def test_la_migracion_crea_la_tabla_audit_log():
    tablas = inspect(engine).get_table_names()
    assert "audit_log" in tablas
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: FAIL (no existe `conftest.py` que migre, ni la tabla; el `inspect` no encuentra `audit_log`, o falla al no haber `tests/conftest.py`). Cualquier fallo aquí es esperado.

- [ ] **Step 3: Crear `backend/alembic.ini`**

```ini
[alembic]
script_location = migrations
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 4: Crear `backend/migrations/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Crear `backend/migrations/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  registra los modelos en Base.metadata
from app.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Si el llamador (tests) no fijó la URL, se toma de la configuración de la app.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: Crear la migración inicial `backend/migrations/versions/0001_crear_audit_log.py`**

```python
"""crear audit_log

Revision ID: 0001
Revises:
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("entity", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
```

- [ ] **Step 7: Crear `backend/tests/conftest.py`**

```python
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
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.session import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


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
```

- [ ] **Step 8: Verificar que `alembic upgrade head` aplica sobre una BD limpia (prueba de runbook)**

Run:
```bash
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade base
```
Expected: ambos comandos terminan sin error (crea y luego elimina `audit_log`). Esto valida el paso central del runbook de switch de motor.

- [ ] **Step 9: Correr el test de migración y verificar que pasa**

Run: `uv run pytest tests/test_migrations.py -v`
Expected: `1 passed` (el fixture autouse migró el esquema; `audit_log` existe).

- [ ] **Step 10: Commit**

```bash
git add backend/alembic.ini backend/migrations/ backend/tests/conftest.py backend/tests/test_migrations.py
git commit -m "feat(backend): Alembic + migración inicial audit_log; tests sobre esquema migrado"
```

---

### Task 7: Schemas + router de `audit-log` (integración end-to-end)

**Files:**
- Create: `backend/app/schemas/__init__.py` (vacío)
- Create: `backend/app/schemas/audit_log.py`
- Create: `backend/app/routers/__init__.py` (vacío)
- Create: `backend/app/routers/audit_log.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_audit_log_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_audit_log_api.py`:

```python
from fastapi.testclient import TestClient


def test_crear_y_listar_audit_log(client: TestClient):
    payload = {
        "actor": "maria.garcia",
        "action": "CREATE",
        "entity": "ingreso",
        "entity_id": "F-2026-0001",
    }
    create = client.post("/api/v1/audit-log", json=payload)
    assert create.status_code == 201
    cuerpo = create.json()
    assert cuerpo["id"] >= 1
    assert cuerpo["actor"] == "maria.garcia"
    assert cuerpo["created_at"] is not None

    listado = client.get("/api/v1/audit-log")
    assert listado.status_code == 200
    actores = [item["actor"] for item in listado.json()]
    assert "maria.garcia" in actores


def test_entity_id_es_opcional(client: TestClient):
    payload = {"actor": "sistema", "action": "LOGIN", "entity": "sesion"}
    create = client.post("/api/v1/audit-log", json=payload)
    assert create.status_code == 201
    assert create.json()["entity_id"] is None
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_audit_log_api.py -v`
Expected: FAIL con `404 Not Found` (la ruta no existe todavía).

- [ ] **Step 3: Crear los schemas Pydantic**

Crear `backend/app/schemas/__init__.py` vacío.

Crear `backend/app/schemas/audit_log.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    actor: str
    action: str
    entity: str
    entity_id: str | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    entity: str
    entity_id: str | None
    created_at: datetime
```

- [ ] **Step 4: Crear el router**

Crear `backend/app/routers/__init__.py` vacío.

Crear `backend/app/routers/audit_log.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogRead

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit-log"])


@router.post("", response_model=AuditLogRead, status_code=status.HTTP_201_CREATED)
def create_audit_log(payload: AuditLogCreate, db: Session = Depends(get_db)) -> AuditLog:
    entry = AuditLog(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[AuditLogRead])
def list_audit_log(db: Session = Depends(get_db)) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)))
```

- [ ] **Step 5: Conectar el router en `app/main.py`**

Reemplazar el contenido de `backend/app/main.py` por:

```python
from fastapi import FastAPI

from app.config import get_settings
from app.routers import audit_log

app = FastAPI(title=get_settings().app_name)
app.include_router(audit_log.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_audit_log_api.py -v`
Expected: `2 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/ backend/app/routers/ backend/app/main.py backend/tests/test_audit_log_api.py
git commit -m "feat(backend): API audit-log (crear/listar) end-to-end sobre Postgres"
```

---

### Task 8: CI dual-target (Postgres obligatorio, Oracle gated)

**Files:**
- Create: `.github/workflows/backend-ci.yml` (raíz del repo)

- [ ] **Step 1: Crear el workflow**

Crear `.github/workflows/backend-ci.yml`:

```yaml
name: backend-ci

on:
  push:
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"
  pull_request:
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"

jobs:
  postgres:
    name: tests (PostgreSQL — obligatorio)
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: cepa
          POSTGRES_PASSWORD: cepa
          POSTGRES_DB: cepa_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U cepa"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      DATABASE_URL: postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --dev
      - name: Smoke de migraciones (upgrade/downgrade)
        run: |
          uv run alembic upgrade head
          uv run alembic downgrade base
      - name: Tests
        run: uv run pytest -v
      - name: Lint
        run: uv run ruff check .

  oracle:
    name: tests (Oracle free — gated, allowed-to-fail)
    runs-on: ubuntu-latest
    continue-on-error: true
    services:
      oracle:
        image: gvenzl/oracle-free:23-slim
        env:
          ORACLE_PASSWORD: cepa
        ports:
          - 1521:1521
        options: >-
          --health-cmd "healthcheck.sh"
          --health-interval 10s
          --health-timeout 10s
          --health-retries 30
    env:
      DATABASE_URL: oracle+oracledb://system:cepa@localhost:1521/?service_name=FREEPDB1
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --dev
      - name: Smoke de migraciones en Oracle
        run: uv run alembic upgrade head
      - name: Tests en Oracle
        run: uv run pytest -v
```

- [ ] **Step 2: Validación local de la sintaxis del workflow (opcional pero recomendado)**

Si `actionlint` está disponible: `actionlint .github/workflows/backend-ci.yml` → sin errores.
Si no está disponible, omitir este paso (el workflow se validará al pushear).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/backend-ci.yml
git commit -m "ci(backend): pipeline dual-target (Postgres obligatorio, Oracle gated)"
```

---

### Task 9: Artefactos de despliegue de contingencia + runbook + README backend

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/docker-compose.yml`
- Create: `backend/.dockerignore`
- Create: `docs/superpowers/runbooks/2026-06-10-switch-db-engine.md`
- Create: `backend/README.md`

- [ ] **Step 1: Crear `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Crear `backend/.dockerignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.env
tests/
```

- [ ] **Step 3: Crear `backend/docker-compose.yml` (contingencia en servidor U)**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: cepa
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cepa}
      POSTGRES_DB: cepa
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cepa"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: .
    environment:
      DATABASE_URL: postgresql+psycopg://cepa:${POSTGRES_PASSWORD:-cepa}@db:5432/cepa
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  pgdata:
```

Nota: para producción detrás de `nginx`, terminar TLS en nginx y hacer proxy_pass a `api:8000` (fuera del alcance de este compose mínimo; ver runbook).

- [ ] **Step 4: Crear el runbook `docs/superpowers/runbooks/2026-06-10-switch-db-engine.md`**

```markdown
# Runbook — Cambiar el motor de base de datos (Oracle ⇄ PostgreSQL)

Aplica la estrategia de D15. El motor se selecciona por `DATABASE_URL`; no hay cambios de código.

## Formato de DATABASE_URL
- PostgreSQL: `postgresql+psycopg://USUARIO:CLAVE@HOST:5432/BASE`
- Oracle:     `oracle+oracledb://USUARIO:CLAVE@HOST:1521/?service_name=PDB`

## Procedimiento de switch
1. Provisionar el motor destino y crear la base/esquema vacío.
2. Definir `DATABASE_URL` apuntando al motor destino (env del servicio o `.env`).
3. Aplicar el esquema: `uv run alembic upgrade head`.
4. (Si hay datos) migrar datos con la herramienta del motor destino — ver Backups.
5. Reiniciar la API. Verificar `GET /health` y un `GET /api/v1/audit-log`.

## Despliegue de contingencia (Postgres en servidor U vía SSH)
- **Con Docker:** `docker compose up -d --build` (levanta db + api; la api corre
  `alembic upgrade head` al arrancar).
- **Bare-metal (sin Docker):**
  1. Instalar Postgres del SO y crear rol/base.
  2. `uv sync --no-dev` en el host.
  3. `DATABASE_URL=... uv run alembic upgrade head`.
  4. Servir con `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` (o gunicorn
     con workers uvicorn) detrás de `nginx` con TLS.

## Backups
- PostgreSQL: `pg_dump` / `pg_restore`.
- Oracle: `expdp` / `impdp`.

## Reglas que mantienen el switch barato (no romper)
- Solo tipos genéricos de SQLAlchemy; nada de SQL específico de motor.
- PK por `Identity()`; identificadores en minúscula y ≤30 chars; fechas en UTC.
- Toda migración debe pasar el job Oracle gated en CI antes de considerarse portable.
```

- [ ] **Step 5: Crear `backend/README.md`**

```markdown
# Backend — Sistema CEPA

FastAPI + SQLAlchemy 2.0 + Alembic, portable entre PostgreSQL (dev/CI/contingencia) y
Oracle (producción objetivo). Ver `docs/superpowers/specs/2026-06-10-portabilidad-bd-postgres-fallback-design.md`.

## Requisitos
- `uv` (gestiona Python 3.12 y el entorno).
- PostgreSQL local (Homebrew): `brew services start postgresql@16`.

## Setup inicial
```bash
# Bases de datos locales (una sola vez)
psql postgres -c "CREATE ROLE cepa LOGIN PASSWORD 'cepa';"
createdb -O cepa cepa
createdb -O cepa cepa_test

cd backend
cp .env.example .env
uv sync
```

## Correr
```bash
uv run alembic upgrade head          # aplica el esquema
uv run uvicorn app.main:app --reload # http://127.0.0.1:8000  (/docs para Swagger)
```

## Tests
```bash
uv run pytest            # usa cepa_test (o TEST_DATABASE_URL)
```

## Migraciones
```bash
uv run alembic revision -m "descripcion"   # nueva migración (escribir portable)
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Cambiar de motor
Ver `docs/superpowers/runbooks/2026-06-10-switch-db-engine.md`.
```

- [ ] **Step 6: Verificar que la suite completa sigue verde**

Run (desde `backend/`): `uv run pytest -v`
Expected: todos los tests pasan (config, session, health, modelo, migración, API).

- [ ] **Step 7: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore backend/docker-compose.yml backend/README.md docs/superpowers/runbooks/
git commit -m "docs(backend): artefactos de contingencia (compose/Dockerfile) + runbook switch + README"
```

---

### Task 10: Verificación final integral

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa + lint**

Run (desde `backend/`):
```bash
uv run pytest -v
uv run ruff check .
```
Expected: todos los tests pasan; ruff sin errores.

- [ ] **Step 2: Verificar que la migración aplica desde cero (paridad con producción)**

Run (desde `backend/`):
```bash
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade base
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head
```
Expected: baja a vacío y vuelve a `head` sin errores.

- [ ] **Step 3: Arranque manual de la app (humo final)**

Run: `uv run uvicorn app.main:app` y en otra terminal:
```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/api/v1/audit-log -H 'content-type: application/json' \
  -d '{"actor":"dev","action":"CREATE","entity":"smoke"}'
curl -s localhost:8000/api/v1/audit-log
```
Expected: `/health` → `{"status":"ok"}`; el POST devuelve 201 con `id` y `created_at`; el GET lista la entrada. Detener con Ctrl-C.

- [ ] **Step 4: Commit final (si quedó algo sin commitear, p. ej. `uv.lock`)**

```bash
git add -A
git commit -m "chore(backend): fundación lista — FastAPI + SQLAlchemy portable, CI dual-target" || echo "nada que commitear"
```

---

## Notas de cierre

- **Qué queda preparado:** estructura del backend, configuración por entorno, capa de datos aislada, app FastAPI con `/health`, primer modelo+API portable end-to-end, migraciones Alembic, CI dual-target y artefactos de contingencia con runbook. Las épicas (Ingresos, Fármacos, etc.) se construyen agregando modelos/routers siguiendo este patrón.
- **Fuera de alcance (deliberado):** autenticación JWT/RBAC (EPIC-00), inmutabilidad real del log y su política (CEPA-003), e integraciones SALUTEM/IMED (EPIC-12). `audit_log` aquí es solo el demostrador portable.
- **Dependencia operativa:** el job Oracle gated en CI valida portabilidad en cada push sin Oracle local; cuando la U habilite Oracle, quitar `continue-on-error: true` para volverlo obligatorio.
```

