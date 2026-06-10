# EPIC-00 — Plataforma base, Autenticación (JWT) y RBAC + Log de auditoría — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan Task por Task. Los pasos usan checkbox (`- [ ]`) para tracking. **Todos los comandos se ejecutan desde `backend/` con `uv run …`.**

**Goal:** Implementar la base segura del Sistema CEPA sobre la Fundación FastAPI + SQLAlchemy portable: autenticación JWT (access + refresh), bloqueo por intentos fallidos, RBAC con los 3 perfiles operativos vigentes (`Coordinacion`, `Administrativo`, `Auditor`), gestión de usuarios (solo Coordinación), y un log de auditoría inmutable, consultable y filtrable. Esta épica **define las interfaces** (`app/auth/deps.py`, `app/audit/service.py`, fixtures `as_admin`/`as_coordinacion`/`as_auditor`) que el resto del backlog asume.

**Architecture:** Se construye encima de la Fundación (`app/db`, `app/config`, `app/main`, `tests/conftest.py`, modelo+API `audit_log` demostrador). Esta épica:
- Añade el modelo `usuario` (credenciales, rol, estado activo, contador de fallos, bloqueo temporal).
- **Reutiliza y extiende** la tabla `audit_log` de la Fundación como log definitivo (CEPA-003), añadiendo columnas `rol`, `valor_anterior`, `valor_nuevo` vía una migración Alembic incremental, y aplicando inmutabilidad a nivel de aplicación (sin endpoints de UPDATE/DELETE) y de BD (trigger portable en la migración).
- Centraliza auth en `app/auth/` (hashing, JWT, dependencias `get_current_user`/`require_role`) y auditoría en `app/audit/service.py` (`record_audit`).
- Expone routers `/api/v1/auth`, `/api/v1/usuarios`, `/api/v1/audit-log` (este último se reescribe: el POST público de la Fundación se elimina; las trazas solo se crean vía `record_audit`, y la lectura queda restringida a Auditor/Coordinación con filtros).

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pydantic-settings. **JWT con `pyjwt`** (decodificación/firma HS256). **Hashing con `pwdlib[argon2]`** (API moderna, sin la deuda de `passlib`/`bcrypt` 72-byte truncation). pytest + httpx contra **Postgres real**. Reglas de portabilidad D15 (tipos genéricos, `Identity`, identificadores ≤30 chars en minúscula, UTC) innegociables.

**Referencias:** `docs/issues/EPIC-00-plataforma-auth-rbac.md` (spec), `docs/superpowers/plans/2026-06-10-00-roadmap-y-convenciones.md` (convenciones), `docs/superpowers/plans/2026-06-10-backend-foundation-fastapi-sqlalchemy.md` (Fundación), `docs/issues/00-decisiones-v4.md` (D1 roles, D13 parametrización, D15 portabilidad).

**Convención de ejecución:** todos los comandos desde `backend/` con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`); el `conftest.py` de la Fundación aplica migraciones Alembic (no `create_all`).

---

## Decisiones tomadas en este plan (consistencia)

- **JWT:** `pyjwt` (HS256, secreto simétrico desde `Settings`). Access token corto, refresh largo. `type` (`access`/`refresh`) en el claim para no aceptar un refresh donde se espera un access.
- **Hashing:** `pwdlib[argon2]` con `PasswordHash.recommended()`. Una sola dependencia, sin warnings de bcrypt.
- **`audit_log`:** se **reutiliza** la tabla de la Fundación (no se crea una nueva). Se extiende con `rol`, `valor_anterior`, `valor_nuevo` y se le añade inmutabilidad real (CEPA-003). El POST público demostrador se elimina.
- **Roles** (v4 D1, exactos): `"Coordinacion"`, `"Administrativo"`, `"Auditor"`. No existe `"Clinico"`.
- **Auditor = solo lectura:** escritura → `require_role("Administrativo", "Coordinacion")`; lectura sensible → añade `"Auditor"`.
- **Gestión de usuarios:** solo `"Coordinacion"`.
- **Bloqueo:** tras N intentos fallidos (configurable, `LOGIN_MAX_INTENTOS`, default 5) la cuenta se bloquea por `LOGIN_BLOQUEO_MINUTOS` (default 15). El desbloqueo es por tiempo o por reseteo de credenciales/estado por Coordinación.

---

### Task 1: Dependencias (pyjwt, pwdlib) y parámetros de configuración de auth

Añade las librerías de auth y los parámetros configurables (vigencia de tokens, intentos máximos, ventana de bloqueo, secreto JWT). Cubre RN-1/RN-3 de CEPA-001 (parametrización, D13).

**Files:**
- Modify: `backend/pyproject.toml` (vía `uv add`)
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_config_auth.py`

- [ ] **Step 1: Añadir dependencias con uv**

Run (desde `backend/`):
```bash
uv add "pyjwt>=2.9" "pwdlib[argon2]>=0.2.1"
```
Expected: `pyproject.toml` lista `pyjwt` y `pwdlib[argon2]` en `dependencies`; `uv.lock` actualizado; `uv sync` implícito sin errores.

- [ ] **Step 2: Escribir el test que falla**

Crear `backend/tests/test_config_auth.py`:

```python
from app.config import Settings


def test_parametros_de_auth_tienen_defaults():
    settings = Settings(_env_file=None)
    assert settings.jwt_secret  # hay un secreto por defecto (override en prod)
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expira_min == 15
    assert settings.refresh_token_expira_min == 60 * 24 * 7
    assert settings.login_max_intentos == 5
    assert settings.login_bloqueo_minutos == 15


def test_parametros_de_auth_se_leen_del_entorno(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "supersecreto-de-prod")
    monkeypatch.setenv("LOGIN_MAX_INTENTOS", "3")
    settings = Settings(_env_file=None)
    assert settings.jwt_secret == "supersecreto-de-prod"
    assert settings.login_max_intentos == 3
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_config_auth.py -v`
Expected: FAIL con `AttributeError`/`ValidationError` (los campos no existen en `Settings`).

- [ ] **Step 4: Extender `app/config.py`**

Reemplazar el contenido de `backend/app/config.py` por:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación. El motor de BD se elige solo aquí, vía DATABASE_URL."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cepa:cepa@localhost:5432/cepa"
    app_name: str = "Sistema CEPA API"

    # --- Autenticación / JWT (EPIC-00, parametrizable; D13) ---
    jwt_secret: str = "cambiar-en-produccion-secreto-jwt-cepa"
    jwt_algorithm: str = "HS256"
    access_token_expira_min: int = 15
    refresh_token_expira_min: int = 60 * 24 * 7  # 7 días

    # --- Bloqueo por intentos fallidos (CEPA-001 RN-3) ---
    login_max_intentos: int = 5
    login_bloqueo_minutos: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Documentar variables en `.env.example`**

Reemplazar el contenido de `backend/.env.example` por:

```bash
# Motor de base de datos. Postgres en dev/CI; Oracle en producción.
# Postgres (psycopg v3):
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa
# Oracle (python-oracledb, thin mode) — ejemplo para producción:
# DATABASE_URL=oracle+oracledb://usuario:clave@host:1521/?service_name=NOMBRE_PDB

# --- Autenticación / JWT (EPIC-00) ---
# OBLIGATORIO cambiar en producción por un secreto largo y aleatorio:
JWT_SECRET=cambiar-en-produccion-secreto-jwt-cepa
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRA_MIN=15
REFRESH_TOKEN_EXPIRA_MIN=10080

# --- Bloqueo por intentos fallidos (CEPA-001 RN-3) ---
LOGIN_MAX_INTENTOS=5
LOGIN_BLOQUEO_MINUTOS=15
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_config_auth.py -v`
Expected: `2 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/config.py backend/.env.example backend/tests/test_config_auth.py
git commit -m "feat(auth): dependencias pyjwt/pwdlib y parámetros JWT/bloqueo configurables"
```

---

### Task 2: Hashing de contraseñas (`app/auth/security.py`)

Util de hashing con `pwdlib[argon2]`. RN-4 de CEPA-001 (las claves nunca viajan en claro ni en el JWT).

**Files:**
- Create: `backend/app/auth/__init__.py` (vacío)
- Create: `backend/app/auth/security.py`
- Test: `backend/tests/test_auth_security.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auth_security.py`:

```python
from app.auth.security import hash_password, verify_password


def test_hash_no_es_la_clave_en_claro():
    hashed = hash_password("Secreto123")
    assert hashed != "Secreto123"
    assert len(hashed) > 20


def test_verify_password_acepta_clave_correcta():
    hashed = hash_password("Secreto123")
    assert verify_password("Secreto123", hashed) is True


def test_verify_password_rechaza_clave_incorrecta():
    hashed = hash_password("Secreto123")
    assert verify_password("otra-clave", hashed) is False
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auth_security.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.auth.security'`.

- [ ] **Step 3: Implementar el módulo**

Crear `backend/app/auth/__init__.py` vacío.

Crear `backend/app/auth/security.py`:

```python
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Devuelve el hash (argon2) de una contraseña en claro."""
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña en claro contra su hash almacenado."""
    return _password_hash.verify(plain, hashed)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auth_security.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/__init__.py backend/app/auth/security.py backend/tests/test_auth_security.py
git commit -m "feat(auth): hashing de contraseñas con pwdlib (argon2)"
```

---

### Task 3: Emisión y verificación de JWT (`app/auth/jwt.py`)

Tokens access/refresh firmados HS256, con `sub` (id), `username`, `role`, `type` y `exp`. RN-1/RN-4 de CEPA-001 (JWT firmado, payload solo identidad + rol).

**Files:**
- Create: `backend/app/auth/jwt.py`
- Test: `backend/tests/test_auth_jwt.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auth_jwt.py`:

```python
import jwt
import pytest

from app.auth.jwt import (
    TokenInvalido,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
)
from app.config import get_settings


def test_access_token_porta_identidad_y_rol_no_la_clave():
    token = crear_access_token(user_id=7, username="maria", role="Coordinacion")
    payload = decodificar_token(token, tipo_esperado="access")
    assert payload["sub"] == "7"
    assert payload["username"] == "maria"
    assert payload["role"] == "Coordinacion"
    assert payload["type"] == "access"
    assert "password" not in payload and "hashed_password" not in payload


def test_refresh_token_tiene_type_refresh():
    token = crear_refresh_token(user_id=7, username="maria", role="Coordinacion")
    payload = decodificar_token(token, tipo_esperado="refresh")
    assert payload["type"] == "refresh"


def test_no_se_acepta_refresh_donde_se_espera_access():
    refresh = crear_refresh_token(user_id=7, username="maria", role="Auditor")
    with pytest.raises(TokenInvalido):
        decodificar_token(refresh, tipo_esperado="access")


def test_token_con_firma_invalida_es_rechazado():
    token = crear_access_token(user_id=1, username="x", role="Administrativo")
    falso = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(TokenInvalido):
        decodificar_token(falso, tipo_esperado="access")


def test_token_expirado_es_rechazado():
    settings = get_settings()
    payload = {
        "sub": "1",
        "username": "x",
        "role": "Administrativo",
        "type": "access",
        "exp": 1,  # 1970, ya expirado
    }
    expirado = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(TokenInvalido):
        decodificar_token(expirado, tipo_esperado="access")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auth_jwt.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.auth.jwt'`.

- [ ] **Step 3: Implementar el módulo**

Crear `backend/app/auth/jwt.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.config import get_settings


class TokenInvalido(Exception):
    """El token JWT es inválido, expiró o no es del tipo esperado."""


def _crear_token(
    user_id: int, username: str, role: str, tipo: Literal["access", "refresh"], expira_min: int
) -> str:
    settings = get_settings()
    ahora = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": tipo,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=expira_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def crear_access_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    return _crear_token(user_id, username, role, "access", settings.access_token_expira_min)


def crear_refresh_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    return _crear_token(user_id, username, role, "refresh", settings.refresh_token_expira_min)


def decodificar_token(token: str, tipo_esperado: Literal["access", "refresh"]) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:  # firma inválida, expirado, malformado
        raise TokenInvalido(str(exc)) from exc
    if payload.get("type") != tipo_esperado:
        raise TokenInvalido(f"se esperaba un token '{tipo_esperado}'")
    return payload
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auth_jwt.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/jwt.py backend/tests/test_auth_jwt.py
git commit -m "feat(auth): emisión/verificación de JWT access y refresh con pyjwt"
```

---

### Task 4: Modelo `Usuario` + migración (credenciales, rol, estado, bloqueo)

Tabla `usuario` portable (D15). Soporta RBAC (CEPA-002) y bloqueo por intentos (CEPA-001 RN-3).

**Files:**
- Create: `backend/app/models/usuario.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0002_crear_usuario.py`
- Test: `backend/tests/test_usuario_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_usuario_model.py`:

```python
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String

from app.models.usuario import Usuario


def test_tabla_y_columnas_esperadas():
    tabla = Usuario.__table__
    assert tabla.name == "usuario"
    assert set(tabla.columns.keys()) == {
        "id",
        "username",
        "nombre",
        "hashed_password",
        "rol",
        "activo",
        "intentos_fallidos",
        "bloqueado_hasta",
        "created_at",
    }


def test_reglas_de_portabilidad_en_identificadores():
    tabla = Usuario.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera el límite de 30 chars de Oracle"


def test_tipos_genericos_y_pk_identity():
    cols = Usuario.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["username"].type, String)
    assert isinstance(cols["rol"].type, String)
    assert isinstance(cols["activo"].type, Boolean)
    assert isinstance(cols["intentos_fallidos"].type, Integer)
    assert isinstance(cols["bloqueado_hasta"].type, DateTime)
    assert cols["bloqueado_hasta"].type.timezone is True
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_username_es_unico():
    assert Usuario.__table__.columns["username"].unique is True
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_usuario_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.usuario'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/usuario.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Roles operativos vigentes (Decisiones v4 D1). No existe "Clinico".
ROLES_VALIDOS = ("Coordinacion", "Administrativo", "Auditor")


class Usuario(Base):
    """Usuario del Sistema CEPA con rol RBAC y control de bloqueo por intentos fallidos."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    username: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
```

Reemplazar `backend/app/models/__init__.py` por:

```python
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
```

- [ ] **Step 4: Crear la migración `0002_crear_usuario.py`**

Crear `backend/migrations/versions/0002_crear_usuario.py`:

```python
"""crear usuario

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("username", sa.String(length=60), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("intentos_fallidos", sa.Integer(), nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_usuario_username", "usuario", ["username"])


def downgrade() -> None:
    op.drop_constraint("uq_usuario_username", "usuario", type_="unique")
    op.drop_table("usuario")
```

- [ ] **Step 5: Correr el test del modelo y verificar que pasa**

Run: `uv run pytest tests/test_usuario_model.py -v`
Expected: `4 passed`.

- [ ] **Step 6: Verificar la migración (upgrade/downgrade en Postgres)**

Run:
```bash
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade base
```
Expected: ambos sin error (crea y elimina `usuario` y `audit_log`).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/usuario.py backend/app/models/__init__.py backend/migrations/versions/0002_crear_usuario.py backend/tests/test_usuario_model.py
git commit -m "feat(auth): modelo y migración usuario (rol, activo, bloqueo, portable)"
```

---

### Task 5: Extender `audit_log` (columnas rol/valor_anterior/valor_nuevo + inmutabilidad)

Convierte el `audit_log` demostrador de la Fundación en el log definitivo de CEPA-003: añade columnas (RN-2) e inmutabilidad a nivel de BD (RN-3, CA-2) con un trigger **portable** (sintaxis válida en Postgres y Oracle).

**Files:**
- Modify: `backend/app/models/audit_log.py`
- Create: `backend/migrations/versions/0003_audit_log_extendido.py`
- Test: `backend/tests/test_audit_log_model.py` (extender)
- Test: `backend/tests/test_audit_log_inmutable.py`

- [ ] **Step 1: Escribir/extender el test que falla (modelo)**

Reemplazar el contenido de `backend/tests/test_audit_log_model.py` por:

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
        "rol",
        "action",
        "entity",
        "entity_id",
        "valor_anterior",
        "valor_nuevo",
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
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["actor"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_default_created_at_es_utc():
    default = AuditLog.__table__.columns["created_at"].default
    assert default is not None and default.is_callable
    valor = default.arg()
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `uv run pytest tests/test_audit_log_model.py -v`
Expected: FAIL en `test_tabla_y_columnas_esperadas` (faltan `rol`, `valor_anterior`, `valor_nuevo`).

- [ ] **Step 3: Extender el modelo `AuditLog`**

Reemplazar el contenido de `backend/app/models/audit_log.py` por:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Traza append-only e inmutable de operaciones (CEPA-003).

    Registra quién (actor/rol), qué (action/entity/entity_id), valores y cuándo (created_at).
    La inmutabilidad se garantiza en la aplicación (sin endpoints de update/delete) y en la BD
    (trigger que rechaza UPDATE/DELETE; ver migración 0003).
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    rol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    entity: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    valor_anterior: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
```

- [ ] **Step 4: Crear la migración `0003_audit_log_extendido.py`**

Crear `backend/migrations/versions/0003_audit_log_extendido.py`. Añade columnas y aplica inmutabilidad a nivel de BD con sintaxis **específica por dialecto** (Postgres: función + trigger; Oracle: trigger PL/SQL), elegida en runtime por `op.get_bind().dialect.name`. Esto mantiene la portabilidad: cada motor usa su mecanismo nativo, pero la migración corre limpia en ambos.

```python
"""audit_log extendido + inmutable

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10 00:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("rol", sa.String(length=20), nullable=True))
    op.add_column("audit_log", sa.Column("valor_anterior", sa.Text(), nullable=True))
    op.add_column("audit_log", sa.Column("valor_nuevo", sa.Text(), nullable=True))

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION audit_log_inmutable()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log es inmutable: no se permite % ', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_log_inmutable
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION audit_log_inmutable();
            """
        )
    elif dialect == "oracle":
        op.execute(
            """
            CREATE OR REPLACE TRIGGER trg_audit_log_inmutable
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            BEGIN
                RAISE_APPLICATION_ERROR(-20001, 'audit_log es inmutable');
            END;
            """
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_log_inmutable ON audit_log;")
        op.execute("DROP FUNCTION IF EXISTS audit_log_inmutable();")
    elif dialect == "oracle":
        op.execute("DROP TRIGGER trg_audit_log_inmutable")

    op.drop_column("audit_log", "valor_nuevo")
    op.drop_column("audit_log", "valor_anterior")
    op.drop_column("audit_log", "rol")
```

> Nota de portabilidad: el trigger es el único punto donde se usa SQL específico por dialecto, y está **encapsulado en una migración** seleccionando por `dialect.name` — el código de negocio sigue 100% agnóstico. El job Oracle gated del CI valida la rama Oracle.

- [ ] **Step 5: Escribir el test de inmutabilidad**

Crear `backend/tests/test_audit_log_inmutable.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session


def test_update_sobre_audit_log_es_rechazado_por_la_bd(db_session: Session):
    db_session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, created_at) "
            "VALUES ('tester', 'CREATE', 'prueba', now())"
        )
    )
    db_session.flush()
    with pytest.raises(DatabaseError):
        db_session.execute(text("UPDATE audit_log SET actor = 'hacker' WHERE actor = 'tester'"))
        db_session.flush()


def test_delete_sobre_audit_log_es_rechazado_por_la_bd(db_session: Session):
    db_session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, created_at) "
            "VALUES ('tester2', 'CREATE', 'prueba', now())"
        )
    )
    db_session.flush()
    with pytest.raises(DatabaseError):
        db_session.execute(text("DELETE FROM audit_log WHERE actor = 'tester2'"))
        db_session.flush()
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_audit_log_model.py tests/test_audit_log_inmutable.py -v`
Expected: modelo `4 passed`; inmutabilidad `2 passed` (la BD rechaza UPDATE/DELETE vía trigger).

- [ ] **Step 7: Verificar la migración (upgrade/downgrade)**

Run:
```bash
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade base
```
Expected: ambos sin error (crea/elimina trigger, función y columnas).

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/audit_log.py backend/migrations/versions/0003_audit_log_extendido.py backend/tests/test_audit_log_model.py backend/tests/test_audit_log_inmutable.py
git commit -m "feat(audit): audit_log extendido (rol/valores) e inmutable a nivel BD (trigger portable)"
```

---

### Task 6: Servicio de auditoría (`app/audit/service.py` — `record_audit`)

Helper que el resto del backlog invoca para registrar trazas (CEPA-003 CA-1, RN-1). Firma exacta prometida en las convenciones, con parámetros opcionales `rol`, `valor_anterior`, `valor_nuevo`.

**Files:**
- Create: `backend/app/audit/__init__.py` (vacío)
- Create: `backend/app/audit/service.py`
- Test: `backend/tests/test_audit_service.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_audit_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.audit_log import AuditLog


def test_record_audit_crea_una_traza(db_session: Session):
    record_audit(
        db_session,
        actor="maria",
        action="CREATE",
        entity="usuario",
        entity_id="42",
        rol="Coordinacion",
    )
    db_session.flush()
    traza = db_session.scalars(select(AuditLog).where(AuditLog.entity_id == "42")).one()
    assert traza.actor == "maria"
    assert traza.action == "CREATE"
    assert traza.entity == "usuario"
    assert traza.rol == "Coordinacion"
    assert traza.created_at is not None


def test_record_audit_guarda_valores_anterior_y_nuevo(db_session: Session):
    record_audit(
        db_session,
        actor="ana",
        action="UPDATE",
        entity="usuario",
        entity_id="7",
        valor_anterior='{"activo": true}',
        valor_nuevo='{"activo": false}',
    )
    db_session.flush()
    traza = db_session.scalars(select(AuditLog).where(AuditLog.entity_id == "7")).one()
    assert traza.valor_anterior == '{"activo": true}'
    assert traza.valor_nuevo == '{"activo": false}'


def test_record_audit_no_hace_commit_se_integra_en_la_transaccion(db_session: Session):
    # record_audit añade a la sesión pero NO commitea: la traza vive o muere con la
    # transacción del caller (CEPA-003 TC-003-05: sin trazas parciales).
    record_audit(db_session, actor="x", action="DELETE", entity="prueba", entity_id="1")
    assert any(isinstance(obj, AuditLog) for obj in db_session.new)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_audit_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.audit.service'`.

- [ ] **Step 3: Implementar el servicio**

Crear `backend/app/audit/__init__.py` vacío.

Crear `backend/app/audit/service.py`:

```python
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    entity: str,
    entity_id: str | None = None,
    rol: str | None = None,
    valor_anterior: str | None = None,
    valor_nuevo: str | None = None,
) -> AuditLog:
    """Registra una traza append-only de auditoría (CEPA-003).

    `action` ∈ {CREATE, UPDATE, DELETE, LOGIN, LOGIN_FALLIDO, BLOQUEO}.
    NO hace commit: la traza se confirma o se revierte junto con la transacción del caller,
    evitando trazas parciales (TC-003-05).
    """
    traza = AuditLog(
        actor=actor,
        rol=rol,
        action=action,
        entity=entity,
        entity_id=entity_id,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
    )
    db.add(traza)
    return traza
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_audit_service.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/audit/__init__.py backend/app/audit/service.py backend/tests/test_audit_service.py
git commit -m "feat(audit): servicio record_audit (append-only, sin commit, valores anterior/nuevo)"
```

---

### Task 7: Dependencias RBAC (`app/auth/deps.py` — `get_current_user`, `require_role`)

Interfaz central que el resto del backlog importa. `CurrentUser(id, username, role)`, `get_current_user` (401 sin token), `require_role(*roles)` (403 sin permiso). RN de CEPA-002 (permisos diferenciados).

**Files:**
- Create: `backend/app/auth/deps.py`
- Test: `backend/tests/test_auth_deps.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auth_deps.py`. Monta una mini-app que ejercita las dependencias contra usuarios reales en BD, con tokens reales.

```python
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, get_current_user, require_role
from app.auth.jwt import crear_access_token
from app.auth.security import hash_password
from app.db.session import get_db
from app.models.usuario import Usuario


@pytest.fixture
def mini_app(db_session: Session):
    app = FastAPI()

    @app.get("/yo")
    def yo(user: CurrentUser = Depends(get_current_user)) -> dict:
        return {"id": user.id, "username": user.username, "role": user.role}

    @app.get("/solo-coordinacion", dependencies=[Depends(require_role("Coordinacion"))])
    def solo_coord() -> dict:
        return {"ok": True}

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def _crear_usuario(db: Session, username: str, rol: str, activo: bool = True) -> Usuario:
    u = Usuario(
        username=username,
        nombre=username.title(),
        hashed_password=hash_password("Clave123"),
        rol=rol,
        activo=activo,
        intentos_fallidos=0,
    )
    db.add(u)
    db.flush()
    return u


def test_sin_token_devuelve_401(mini_app):
    client = TestClient(mini_app)
    assert client.get("/yo").status_code == 401


def test_token_invalido_devuelve_401(mini_app):
    client = TestClient(mini_app)
    r = client.get("/yo", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert r.status_code == 401


def test_token_valido_resuelve_current_user(mini_app, db_session):
    u = _crear_usuario(db_session, "maria", "Coordinacion")
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"id": u.id, "username": "maria", "role": "Coordinacion"}


def test_usuario_desactivado_devuelve_401(mini_app, db_session):
    u = _crear_usuario(db_session, "expulsado", "Administrativo", activo=False)
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_require_role_permite_rol_correcto(mini_app, db_session):
    u = _crear_usuario(db_session, "coord", "Coordinacion")
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/solo-coordinacion", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_require_role_rechaza_rol_incorrecto_con_403(mini_app, db_session):
    u = _crear_usuario(db_session, "admin", "Administrativo")
    token = crear_access_token(user_id=u.id, username=u.username, role=u.rol)
    client = TestClient(mini_app)
    r = client.get("/solo-coordinacion", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auth_deps.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.auth.deps'`.

- [ ] **Step 3: Implementar `app/auth/deps.py`**

Crear `backend/app/auth/deps.py`:

```python
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import TokenInvalido, decodificar_token
from app.db.session import get_db
from app.models.usuario import Usuario

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """Identidad mínima del usuario autenticado, derivada del JWT + BD."""

    id: int
    username: str
    role: str


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Resuelve al usuario autenticado a partir del access token. 401 si falta/expira/inactivo."""
    if credenciales is None or not credenciales.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decodificar_token(credenciales.credentials, tipo_esperado="access")
    except TokenInvalido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o desactivado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(id=usuario.id, username=usuario.username, role=usuario.rol)


def require_role(*roles: str):
    """Dependencia que exige que el usuario autenticado tenga uno de los roles dados (403 si no)."""

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta operación",
            )
        return user

    return _checker
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auth_deps.py -v`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/deps.py backend/tests/test_auth_deps.py
git commit -m "feat(auth): dependencias RBAC get_current_user y require_role (401/403)"
```

---

### Task 8: Fixtures de tests autenticados (`as_admin`, `as_coordinacion`, `as_auditor`)

Extiende `tests/conftest.py` con los clientes autenticados por rol que las convenciones prometen al resto del backlog. Esto desbloquea el testing RBAC de todas las épicas de dominio.

**Files:**
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/test_fixtures_auth.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_fixtures_auth.py`:

```python
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.deps import CurrentUser, get_current_user


def test_as_coordinacion_lleva_jwt_de_coordinacion(as_coordinacion):
    r = as_coordinacion.get("/whoami-test")
    assert r.status_code == 200
    assert r.json()["role"] == "Coordinacion"


def test_as_admin_lleva_jwt_de_administrativo(as_admin):
    r = as_admin.get("/whoami-test")
    assert r.status_code == 200
    assert r.json()["role"] == "Administrativo"


def test_as_auditor_lleva_jwt_de_auditor(as_auditor):
    r = as_auditor.get("/whoami-test")
    assert r.status_code == 200
    assert r.json()["role"] == "Auditor"
```

Y registrar una ruta de prueba en la app de test. Para no tocar `app/main.py`, se añade en `conftest.py` (ver Step 3) un router de diagnóstico montado solo en tests.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_fixtures_auth.py -v`
Expected: FAIL (fixtures `as_coordinacion`/`as_admin`/`as_auditor` no existen).

- [ ] **Step 3: Extender `tests/conftest.py`**

Reemplazar el contenido de `backend/tests/conftest.py` por (mantiene lo de la Fundación y añade usuarios sembrados + clientes por rol + ruta `/whoami-test`):

```python
import os

# Apuntar el motor a la BD de pruebas ANTES de importar la app.
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
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def as_coordinacion(client: TestClient, db_session: Session) -> TestClient:
    return _cliente_autenticado(client, db_session, "coord_test", "Coordinacion")


@pytest.fixture
def as_admin(client: TestClient, db_session: Session) -> TestClient:
    return _cliente_autenticado(client, db_session, "admin_test", "Administrativo")


@pytest.fixture
def as_auditor(client: TestClient, db_session: Session) -> TestClient:
    return _cliente_autenticado(client, db_session, "auditor_test", "Auditor")
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_fixtures_auth.py -v`
Expected: `3 passed` (cada cliente lleva el JWT del rol y `/whoami-test` lo refleja).

- [ ] **Step 5: Verificar que la suite completa sigue verde**

Run: `uv run pytest -v`
Expected: todos los tests previos siguen pasando (la ruta `/whoami-test` no rompe nada).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_fixtures_auth.py
git commit -m "test(auth): fixtures as_admin/as_coordinacion/as_auditor (clientes JWT por rol)"
```

---

### Task 9: Schemas de auth y usuario (Pydantic v2)

Schemas para login, tokens y CRUD de usuarios. Validan el rol contra `ROLES_VALIDOS` (CEPA-002 CA-2: el rol "Clinico" se rechaza).

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/usuario.py`
- Test: `backend/tests/test_schemas_usuario.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_schemas_usuario.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.usuario import UsuarioCreate


def test_usuario_create_acepta_roles_validos():
    for rol in ("Coordinacion", "Administrativo", "Auditor"):
        u = UsuarioCreate(username="x", nombre="X", password="Clave123!", rol=rol)
        assert u.rol == rol


def test_usuario_create_rechaza_rol_clinico():
    with pytest.raises(ValidationError):
        UsuarioCreate(username="x", nombre="X", password="Clave123!", rol="Clinico")


def test_usuario_create_rechaza_rol_arbitrario():
    with pytest.raises(ValidationError):
        UsuarioCreate(username="x", nombre="X", password="Clave123!", rol="SuperUser")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_schemas_usuario.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.usuario'`.

- [ ] **Step 3: Implementar los schemas**

Crear `backend/app/schemas/auth.py`:

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

Crear `backend/app/schemas/usuario.py`:

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Rol = Literal["Coordinacion", "Administrativo", "Auditor"]


class UsuarioCreate(BaseModel):
    username: str
    nombre: str
    password: str
    rol: Rol


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    password: str | None = None
    rol: Rol | None = None


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nombre: str
    rol: str
    activo: bool
    created_at: datetime
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_schemas_usuario.py -v`
Expected: `3 passed` (el `Literal` rechaza "Clinico" y "SuperUser").

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/schemas/usuario.py backend/tests/test_schemas_usuario.py
git commit -m "feat(auth): schemas Pydantic de login/token y usuario (rol restringido a v4 D1)"
```

---

### Task 10: Servicio de autenticación (login con bloqueo por intentos)

Lógica de login: verificación de credenciales, contador de fallos, bloqueo temporal y emisión de tokens. CEPA-001 CA-1/CA-3 (RN-1, RN-3, RN-5).

**Files:**
- Create: `backend/app/auth/service.py`
- Test: `backend/tests/test_auth_service_login.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auth_service_login.py`:

```python
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auth_service_login.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.auth.service'`.

- [ ] **Step 3: Implementar el servicio**

Crear `backend/app/auth/service.py`:

```python
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
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auth_service_login.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/service.py backend/tests/test_auth_service_login.py
git commit -m "feat(auth): servicio de login con bloqueo por intentos y auditoría de eventos"
```

---

### Task 11: Router de autenticación (`/api/v1/auth/login` y `/refresh`)

Endpoints de login y refresh. CEPA-001 CA-1/CA-2/CA-4 (TC-001-01/02/03/04/05).

**Files:**
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auth_api.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import get_settings
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


def test_login_exitoso_devuelve_par_de_tokens(client: TestClient, db_session: Session):
    _crear(db_session)
    r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "Clave123!"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["access_token"] and cuerpo["refresh_token"]
    assert cuerpo["token_type"] == "bearer"


def test_login_con_clave_incorrecta_devuelve_401_generico(client: TestClient, db_session: Session):
    _crear(db_session)
    r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "mala"})
    assert r.status_code == 401
    # mensaje genérico, no revela el campo fallido (TC-001-03)
    assert "inválid" in r.json()["detail"].lower()


def test_login_usuario_inexistente_devuelve_401(client: TestClient):
    r = client.post("/api/v1/auth/login", json={"username": "fantasma", "password": "x"})
    assert r.status_code == 401


def test_login_bloqueo_tras_n_intentos_devuelve_429(client: TestClient, db_session: Session):
    settings = get_settings()
    _crear(db_session)
    # N-1 fallos: 401
    for _ in range(settings.login_max_intentos - 1):
        r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "mala"})
        assert r.status_code == 401
    # intento N: bloqueo -> 429
    r = client.post("/api/v1/auth/login", json={"username": "maria", "password": "mala"})
    assert r.status_code == 429


def test_refresh_renueva_access_token(client: TestClient, db_session: Session):
    _crear(db_session)
    login = client.post("/api/v1/auth/login", json={"username": "maria", "password": "Clave123!"})
    refresh = login.json()["refresh_token"]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"


def test_refresh_con_token_invalido_devuelve_401(client: TestClient):
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "no-es-jwt"})
    assert r.status_code == 401


def test_endpoint_protegido_sin_token_devuelve_401(client: TestClient):
    # /whoami-test (montado en conftest) requiere get_current_user
    assert client.get("/whoami-test").status_code == 401
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auth_api.py -v`
Expected: FAIL con `404` (rutas `/api/v1/auth/...` no existen aún).

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import (
    TokenInvalido,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
)
from app.auth.service import CredencialesInvalidas, CuentaBloqueada, autenticar
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        usuario = autenticar(db, payload.username, payload.password)
    except CuentaBloqueada as exc:
        db.commit()  # persiste el bloqueo y su traza de auditoría
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except CredencialesInvalidas as exc:
        db.commit()  # persiste el incremento de intentos y la traza LOGIN_FALLIDO
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    db.commit()
    return TokenPair(
        access_token=crear_access_token(usuario.id, usuario.username, usuario.rol),
        refresh_token=crear_refresh_token(usuario.id, usuario.username, usuario.rol),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    try:
        claims = decodificar_token(payload.refresh_token, tipo_esperado="refresh")
    except TokenInvalido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado"
        )

    usuario = db.get(Usuario, int(claims["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inexistente o desactivado"
        )
    return AccessTokenResponse(
        access_token=crear_access_token(usuario.id, usuario.username, usuario.rol)
    )
```

- [ ] **Step 4: Conectar el router en `app/main.py`**

Reemplazar el contenido de `backend/app/main.py` por:

```python
from fastapi import FastAPI

from app.config import get_settings
from app.routers import audit_log, auth, usuarios

app = FastAPI(title=get_settings().app_name)
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(audit_log.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

> Nota: `usuarios` y la reescritura de `audit_log` se implementan en las Tasks 12 y 13. Para que este `main.py` importe sin error **ya en esta Task**, crear stubs vacíos provisionales NO es deseable; en su lugar, **ordena la ejecución**: implementa las Tasks 12 y 13 en la misma sesión antes de correr la suite global. Si ejecutas Task 11 aislada, comenta temporalmente las dos líneas de `usuarios`/`audit_log` y descoméntalas al llegar a esas Tasks. (El loop subagent-driven ejecuta las tres en orden, por lo que la suite global se corre al cerrar Task 13.)

- [ ] **Step 5: Correr el test del router auth (aislado) y verificar que pasa**

Para correr Task 11 de forma aislada, deja en `main.py` solo `auth.router` incluido (comenta `usuarios`/`audit_log`). Luego:

Run: `uv run pytest tests/test_auth_api.py -v`
Expected: `7 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/auth.py backend/app/main.py backend/tests/test_auth_api.py
git commit -m "feat(auth): endpoints /auth/login y /auth/refresh (401/429, par de tokens)"
```

---

### Task 12: Router de gestión de usuarios (`/api/v1/usuarios`, solo Coordinación)

CRUD de usuarios y activar/desactivar, restringido a `Coordinacion`. CEPA-002 CA-1/CA-4/CA-5 (TC-002-01/03/05/06). Cada operación audita (RN-7).

**Files:**
- Create: `backend/app/routers/usuarios.py`
- Test: `backend/tests/test_usuarios_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_usuarios_api.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.usuario import Usuario


def test_coordinacion_crea_usuario_administrativo(as_coordinacion: TestClient):
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "nuevo", "nombre": "Nuevo", "password": "Clave123!", "rol": "Administrativo"},
    )
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["username"] == "nuevo"
    assert cuerpo["rol"] == "Administrativo"
    assert cuerpo["activo"] is True
    assert "hashed_password" not in cuerpo  # nunca se expone el hash


def test_crear_usuario_rol_clinico_es_rechazado_422(as_coordinacion: TestClient):
    r = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "x", "nombre": "X", "password": "Clave123!", "rol": "Clinico"},
    )
    assert r.status_code == 422  # el rol "Clinico" no existe (CEPA-002 CA-2)


def test_administrativo_no_puede_crear_usuarios_403(as_admin: TestClient):
    r = as_admin.post(
        "/api/v1/usuarios",
        json={"username": "x", "nombre": "X", "password": "Clave123!", "rol": "Administrativo"},
    )
    assert r.status_code == 403


def test_auditor_no_puede_crear_usuarios_403(as_auditor: TestClient):
    r = as_auditor.post(
        "/api/v1/usuarios",
        json={"username": "x", "nombre": "X", "password": "Clave123!", "rol": "Administrativo"},
    )
    assert r.status_code == 403


def test_coordinacion_lista_usuarios(as_coordinacion: TestClient):
    as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "u1", "nombre": "U1", "password": "Clave123!", "rol": "Administrativo"},
    )
    r = as_coordinacion.get("/api/v1/usuarios")
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "u1" in usernames


def test_coordinacion_desactiva_usuario_revoca_acceso(
    as_coordinacion: TestClient, db_session: Session
):
    create = as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "rotativo", "nombre": "Rot", "password": "Clave123!", "rol": "Administrativo"},
    )
    uid = create.json()["id"]
    r = as_coordinacion.patch(f"/api/v1/usuarios/{uid}/desactivar")
    assert r.status_code == 200
    assert r.json()["activo"] is False
    usuario = db_session.get(Usuario, uid)
    db_session.refresh(usuario)
    assert usuario.activo is False


def test_alta_de_usuario_genera_traza_de_auditoria(
    as_coordinacion: TestClient, db_session: Session
):
    as_coordinacion.post(
        "/api/v1/usuarios",
        json={"username": "auditado", "nombre": "A", "password": "Clave123!", "rol": "Auditor"},
    )
    trazas = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "usuario", AuditLog.action == "CREATE")
    ).all()
    assert any(t.actor == "coord_test" for t in trazas)


def test_alta_rotacion_crea_varios_usuarios_sin_limite(as_coordinacion: TestClient):
    for i in range(5):
        r = as_coordinacion.post(
            "/api/v1/usuarios",
            json={"username": f"adm{i}", "nombre": f"A{i}", "password": "Clave123!", "rol": "Administrativo"},
        )
        assert r.status_code == 201


def test_username_duplicado_devuelve_409(as_coordinacion: TestClient):
    payload = {"username": "dup", "nombre": "D", "password": "Clave123!", "rol": "Administrativo"}
    assert as_coordinacion.post("/api/v1/usuarios", json=payload).status_code == 201
    r = as_coordinacion.post("/api/v1/usuarios", json=payload)
    assert r.status_code == 409
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_usuarios_api.py -v`
Expected: FAIL con `404` (rutas `/api/v1/usuarios` no existen).

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/usuarios.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import CurrentUser, require_role
from app.auth.security import hash_password
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])

# Toda la gestión de usuarios es exclusiva de Coordinación (CEPA-002 RN-4).
_solo_coordinacion = require_role("Coordinacion")


def _get_usuario_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = Usuario(
        username=payload.username,
        nombre=payload.nombre,
        hashed_password=hash_password(payload.password),
        rol=payload.rol,
        activo=True,
        intentos_fallidos=0,
    )
    db.add(usuario)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El username ya existe"
        )
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="CREATE",
        entity="usuario",
        entity_id=str(usuario.id),
        valor_nuevo=f'{{"username": "{usuario.username}", "rol": "{usuario.rol}"}}',
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("", response_model=list[UsuarioRead])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_solo_coordinacion),
) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id)))


@router.get("/{usuario_id}", response_model=UsuarioRead)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    return _get_usuario_o_404(db, usuario_id)


@router.put("/{usuario_id}", response_model=UsuarioRead)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    if payload.nombre is not None:
        usuario.nombre = payload.nombre
    if payload.rol is not None:
        usuario.rol = payload.rol
    if payload.password is not None:
        usuario.hashed_password = hash_password(payload.password)
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="UPDATE",
        entity="usuario",
        entity_id=str(usuario.id),
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/desactivar", response_model=UsuarioRead)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    usuario.activo = False
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="UPDATE",
        entity="usuario",
        entity_id=str(usuario.id),
        valor_anterior='{"activo": true}',
        valor_nuevo='{"activo": false}',
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/activar", response_model=UsuarioRead)
def activar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_solo_coordinacion),
) -> Usuario:
    usuario = _get_usuario_o_404(db, usuario_id)
    usuario.activo = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    record_audit(
        db,
        actor=actor.username,
        rol=actor.role,
        action="UPDATE",
        entity="usuario",
        entity_id=str(usuario.id),
        valor_anterior='{"activo": false}',
        valor_nuevo='{"activo": true}',
    )
    db.commit()
    db.refresh(usuario)
    return usuario
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Asegúrate de que `app/main.py` (Task 11 Step 4) incluye `usuarios.router`.

Run: `uv run pytest tests/test_usuarios_api.py -v`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/usuarios.py backend/tests/test_usuarios_api.py
git commit -m "feat(usuarios): CRUD + activar/desactivar (solo Coordinación, con auditoría)"
```

---

### Task 13: Reescritura del router `audit_log` (consulta filtrable, solo Auditor/Coordinación, sin POST público)

CEPA-003 CA-2/CA-3/CA-4 (TC-003-02/03/04/06). El POST público demostrador de la Fundación se **elimina** (las trazas solo se crean vía `record_audit`). La lectura se restringe a Auditor/Coordinación y se vuelve filtrable.

**Files:**
- Modify: `backend/app/schemas/audit_log.py`
- Modify: `backend/app/routers/audit_log.py`
- Delete (tests): `backend/tests/test_audit_log_api.py` (POST público de la Fundación ya no aplica)
- Test: `backend/tests/test_audit_log_query_api.py`

- [ ] **Step 1: Eliminar el test obsoleto de la Fundación**

El test `backend/tests/test_audit_log_api.py` (Fundación) ejercita un `POST /api/v1/audit-log` público que esta épica retira. Eliminarlo:

```bash
git rm backend/tests/test_audit_log_api.py
```

- [ ] **Step 2: Escribir el test que falla (consulta filtrable + permisos + inmutabilidad por API)**

Crear `backend/tests/test_audit_log_query_api.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audit.service import record_audit


def _sembrar_trazas(db: Session) -> None:
    record_audit(db, actor="maria", rol="Coordinacion", action="CREATE", entity="ingreso", entity_id="F1")
    record_audit(db, actor="juan", rol="Administrativo", action="UPDATE", entity="farmaco", entity_id="X9")
    record_audit(db, actor="maria", rol="Coordinacion", action="DELETE", entity="ingreso", entity_id="F2")
    db.flush()


def test_auditor_puede_listar_el_log(as_auditor: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_auditor.get("/api/v1/audit-log")
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_coordinacion_puede_listar_el_log(as_coordinacion: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_coordinacion.get("/api/v1/audit-log")
    assert r.status_code == 200


def test_administrativo_no_puede_ver_el_log_403(as_admin: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_admin.get("/api/v1/audit-log")
    assert r.status_code == 403


def test_sin_token_el_log_devuelve_401(client: TestClient):
    assert client.get("/api/v1/audit-log").status_code == 401


def test_filtro_por_actor(as_auditor: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_auditor.get("/api/v1/audit-log", params={"actor": "maria"})
    assert r.status_code == 200
    assert all(t["actor"] == "maria" for t in r.json())
    assert len(r.json()) == 2


def test_filtro_por_entity_y_action(as_auditor: TestClient, db_session: Session):
    _sembrar_trazas(db_session)
    r = as_auditor.get("/api/v1/audit-log", params={"entity": "ingreso", "action": "DELETE"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["entity_id"] == "F2"


def test_no_existe_endpoint_para_crear_trazas_via_api(as_coordinacion: TestClient):
    # El POST público fue retirado; las trazas solo nacen vía record_audit (inmutabilidad/append-only).
    r = as_coordinacion.post(
        "/api/v1/audit-log",
        json={"actor": "x", "action": "CREATE", "entity": "y"},
    )
    assert r.status_code in (404, 405)


def test_no_existe_endpoint_para_borrar_trazas_via_api(as_coordinacion: TestClient):
    r = as_coordinacion.delete("/api/v1/audit-log/1")
    assert r.status_code in (404, 405)
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_audit_log_query_api.py -v`
Expected: FAIL (la lectura es pública/sin filtros y el POST aún existe; varios asserts fallan).

- [ ] **Step 4: Extender los schemas de `audit_log`**

Reemplazar el contenido de `backend/app/schemas/audit_log.py` por:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    rol: str | None
    action: str
    entity: str
    entity_id: str | None
    valor_anterior: str | None
    valor_nuevo: str | None
    created_at: datetime
```

- [ ] **Step 5: Reescribir el router `audit_log`**

Reemplazar el contenido de `backend/app/routers/audit_log.py` por:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit-log"])

# Lectura del log restringida a Auditor y Coordinación (CEPA-003 RN-5).
_solo_auditoria = require_role("Auditor", "Coordinacion")


@router.get("", response_model=list[AuditLogRead], dependencies=[Depends(_solo_auditoria)])
def listar_audit_log(
    db: Session = Depends(get_db),
    actor: str | None = Query(default=None),
    entity: str | None = Query(default=None, description="Módulo/entidad afectada"),
    action: str | None = Query(default=None),
    desde: datetime | None = Query(default=None, description="created_at >= desde (UTC)"),
    hasta: datetime | None = Query(default=None, description="created_at <= hasta (UTC)"),
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if actor is not None:
        stmt = stmt.where(AuditLog.actor == actor)
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if desde is not None:
        stmt = stmt.where(AuditLog.created_at >= desde)
    if hasta is not None:
        stmt = stmt.where(AuditLog.created_at <= hasta)
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return list(db.scalars(stmt))
```

> El router ya no expone POST ni DELETE: la creación de trazas es exclusiva de `record_audit` (append-only) y la inmutabilidad la refuerza el trigger de BD (Task 5). Esto satisface CA-2 a nivel de API (no hay verbo para alterar) y a nivel de BD (trigger).

- [ ] **Step 6: Correr el test y verificar que pasa**

Asegúrate de que `app/main.py` incluye `audit_log.router` (Task 11 Step 4).

Run: `uv run pytest tests/test_audit_log_query_api.py -v`
Expected: `8 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/audit_log.py backend/app/routers/audit_log.py backend/tests/test_audit_log_query_api.py
git rm --cached backend/tests/test_audit_log_api.py 2>/dev/null || true
git commit -m "feat(audit): API de consulta filtrable del log (solo Auditor/Coordinación, append-only)"
```

---

### Task 14: Seed de usuario inicial de Coordinación (bootstrap) + comando

Sin un primer usuario de Coordinación nadie puede crear usuarios (gallina y huevo). Se provee un script idempotente para sembrar el usuario administrador inicial. CEPA-002 (habilita el bootstrap operativo).

**Files:**
- Create: `backend/app/scripts/__init__.py` (vacío)
- Create: `backend/app/scripts/seed_admin.py`
- Test: `backend/tests/test_seed_admin.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_seed_admin.py`:

```python
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_seed_admin.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.scripts.seed_admin'`.

- [ ] **Step 3: Implementar el script**

Crear `backend/app/scripts/__init__.py` vacío.

Crear `backend/app/scripts/seed_admin.py`:

```python
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
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_seed_admin.py -v`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scripts/__init__.py backend/app/scripts/seed_admin.py backend/tests/test_seed_admin.py
git commit -m "feat(auth): seed idempotente del usuario inicial de Coordinación (bootstrap)"
```

---

### Task 15: Verificación final integral de EPIC-00

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa + lint**

Run (desde `backend/`):
```bash
uv run pytest -v
uv run ruff check .
```
Expected: todos los tests pasan (Fundación + EPIC-00); ruff sin errores.

- [ ] **Step 2: Migración aplica desde cero (paridad con producción)**

Run:
```bash
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade base
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head
```
Expected: baja a vacío y vuelve a `head` (audit_log + usuario + trigger) sin errores.

- [ ] **Step 3: Humo manual del flujo auth completo**

Run: `uv run uvicorn app.main:app` y en otra terminal (usando `cepa`, no `cepa_test`):
```bash
# Bootstrap del primer usuario de Coordinación
DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa \
  uv run python -m app.scripts.seed_admin --username root --password 'Inicial123!' --nombre 'Coordinación'

# Login
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"root","password":"Inicial123!"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Crear un usuario Administrativo (requiere rol Coordinación)
curl -s -X POST localhost:8000/api/v1/usuarios -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"username":"ana","nombre":"Ana","password":"Clave123!","rol":"Administrativo"}'

# Consultar el log (Coordinación puede)
curl -s localhost:8000/api/v1/audit-log -H "Authorization: Bearer $TOKEN"
```
Expected: login devuelve tokens; el POST a `/usuarios` devuelve 201; el GET del log lista las trazas (LOGIN, CREATE). Detener con Ctrl-C.

- [ ] **Step 4: Verificar Swagger (OI3, DoD de las 3 historias)**

Run: `uv run uvicorn app.main:app` → abrir `http://127.0.0.1:8000/docs`.
Expected: aparecen los grupos `auth`, `usuarios`, `audit-log` con sus endpoints y schemas. Detener con Ctrl-C.

- [ ] **Step 5: Commit final (si quedó algo, p. ej. `uv.lock`)**

```bash
git add -A
git commit -m "chore(epic-00): plataforma auth/RBAC/auditoría completa y verificada" || echo "nada que commitear"
```

---

## Cobertura (CEPA-00X ↔ Tasks y Test Cases)

### CEPA-001 — Autenticación JWT e inicio de sesión
- **Tasks:** 1 (parámetros configurables), 2 (hashing), 3 (JWT access/refresh), 7 (get_current_user 401), 10 (login + bloqueo), 11 (endpoints `/auth/login` y `/auth/refresh`).
- **Test Cases:**
  - TC-001-01 (login válido → JWT) → `test_auth_api.py::test_login_exitoso_devuelve_par_de_tokens`.
  - TC-001-02 (refresh renueva sin credenciales) → `test_auth_api.py::test_refresh_renueva_access_token`.
  - TC-001-03 (clave incorrecta, mensaje genérico) → `test_auth_api.py::test_login_con_clave_incorrecta_devuelve_401_generico` + `test_auth_service_login.py`.
  - TC-001-04 (bloqueo al intento N) → `test_auth_api.py::test_login_bloqueo_tras_n_intentos_devuelve_429` + `test_auth_service_login.py::test_login_se_bloquea_al_alcanzar_el_maximo`.
  - TC-001-05 (endpoint protegido sin/expirado token → 401) → `test_auth_api.py::test_endpoint_protegido_sin_token_devuelve_401`, `test_auth_deps.py::test_sin_token_devuelve_401`/`test_token_invalido_devuelve_401`, `test_auth_jwt.py::test_token_expirado_es_rechazado`.
  - TC-001-06 (rechazar canal no cifrado) → **fuera del código de app**: TLS se termina en el proxy/nginx (ver Notas de cierre). Se documenta como responsabilidad de despliegue (RN-2).

### CEPA-002 — Gestión de usuarios y roles RBAC
- **Tasks:** 4 (modelo `usuario`), 7 (`require_role`), 8 (fixtures por rol), 9 (schemas, rol restringido), 12 (router `/usuarios`), 14 (seed bootstrap).
- **Test Cases:**
  - TC-002-01 (crear Administrativo) → `test_usuarios_api.py::test_coordinacion_crea_usuario_administrativo`.
  - TC-002-02 (rol "Clinico" no disponible) → `test_usuarios_api.py::test_crear_usuario_rol_clinico_es_rechazado_422` + `test_schemas_usuario.py::test_usuario_create_rechaza_rol_clinico`.
  - TC-002-03 (Administrativo no gestiona usuarios → 403) → `test_usuarios_api.py::test_administrativo_no_puede_crear_usuarios_403`.
  - TC-002-04 (Auditor solo lectura, no edita) → `test_usuarios_api.py::test_auditor_no_puede_crear_usuarios_403` + `test_audit_log_query_api.py::test_auditor_puede_listar_el_log` (Auditor lee, no escribe). La regla general "Auditor no edita datos" se materializa porque todo endpoint de escritura del backlog usa `require_role("Administrativo","Coordinacion")` (Task 7, convención).
  - TC-002-05 (desactivar revoca acceso + traza) → `test_usuarios_api.py::test_coordinacion_desactiva_usuario_revoca_acceso` + `test_auth_deps.py::test_usuario_desactivado_devuelve_401` (acceso revocado) + `test_usuarios_api.py::test_alta_de_usuario_genera_traza_de_auditoria` (patrón de traza).
  - TC-002-06 (alta rotación, sin límite de cupo) → `test_usuarios_api.py::test_alta_rotacion_crea_varios_usuarios_sin_limite`.

### CEPA-003 — Log de auditoría del sistema
- **Tasks:** 5 (audit_log extendido + inmutable), 6 (`record_audit`), 13 (API de consulta filtrable).
- **Test Cases:**
  - TC-003-01 (operación CRUD genera traza) → `test_audit_service.py::test_record_audit_crea_una_traza` + `test_usuarios_api.py::test_alta_de_usuario_genera_traza_de_auditoria`.
  - TC-003-02 (traza inmutable, no editable/borrable) → `test_audit_log_inmutable.py` (UPDATE/DELETE en BD) + `test_audit_log_query_api.py::test_no_existe_endpoint_para_crear/borrar_trazas_via_api` (sin verbos de alteración en la API).
  - TC-003-03 (filtros por usuario/módulo/operación/fechas) → `test_audit_log_query_api.py::test_filtro_por_actor`/`test_filtro_por_entity_y_action` (y parámetros `desde`/`hasta` en el router).
  - TC-003-04 (Administrativo no accede al log → 403) → `test_audit_log_query_api.py::test_administrativo_no_puede_ver_el_log_403`.
  - TC-003-05 (sin trazas parciales si la transacción falla) → `test_audit_service.py::test_record_audit_no_hace_commit_se_integra_en_la_transaccion` (la traza vive/muere con la transacción del caller).
  - TC-003-06 (Auditor consulta en solo lectura) → `test_audit_log_query_api.py::test_auditor_puede_listar_el_log` + ausencia de endpoints de escritura para Auditor.

### Interfaces prometidas a otras épicas (convenciones)
- `app/auth/deps.py::get_current_user -> CurrentUser(id, username, role)` y `require_role(*roles)` → Task 7.
- `app/audit/service.py::record_audit(db, actor, action, entity, entity_id, ...)` → Task 6.
- Fixtures `as_admin`, `as_coordinacion`, `as_auditor` → Task 8.

---

## Notas de cierre

### Qué depende de la Fundación / EPIC-00 y debe verificarse contra el código real antes del loop
- **`tests/conftest.py`** de la Fundación se **reemplaza** en Task 8. Verificar que las fixtures `db_session` y `client` (savepoint, override de `get_db`) coinciden literalmente con lo que la Fundación dejó en `main`; si la Fundación cambió firmas, ajustar antes de correr.
- **`audit_log`** se **reutiliza y extiende** (no se crea nueva tabla). Confirmar que la migración `0001` de la Fundación dejó exactamente las columnas `id/actor/action/entity/entity_id/created_at`; la migración `0003` asume ese punto de partida.
- **`app/main.py`** se reescribe en Task 11 incluyendo `auth`, `usuarios` y `audit_log`. Las tres Tasks (11, 12, 13) deben cerrarse en la misma oleada; el loop subagent-driven las ejecuta en orden y corre la suite global al final de Task 13/15.
- **`app/models/__init__.py`** debe registrar `Usuario` además de `AuditLog` (Task 4) para que Alembic y `target_metadata` los vean.
- **`pyproject.toml` / `uv.lock`:** Task 1 agrega `pyjwt` y `pwdlib[argon2]`; verificar que `uv add` no entre en conflicto con las versiones fijadas por la Fundación.

### Decisiones de librería tomadas (justificadas)
- **JWT → `pyjwt`** (explícitamente pedido por la consigna; HS256 con secreto simétrico desde `Settings`).
- **Hashing → `pwdlib[argon2]`** (sobre `passlib[bcrypt]`): API moderna mantenida, sin el límite de 72 bytes de bcrypt ni los warnings de compatibilidad de `passlib` con bcrypt 4.x. Una sola dependencia.

### Decisiones de negocio abiertas del spec (declaradas, no resueltas aquí)
- **Valor de N, ventana de bloqueo y vigencia de tokens** (CEPA-001 Notas, D13): implementados como parámetros configurables con defaults razonables (N=5, bloqueo 15 min, access 15 min, refresh 7 días); **confirmar con Coordinación / Mario (TI UTalca)** los valores definitivos.
- **Desbloqueo de cuentas** (CEPA-002 Notas): aquí el desbloqueo es por tiempo (ventana) o vía `PATCH /usuarios/{id}/activar` (Coordinación, que resetea `intentos_fallidos` y `bloqueado_hasta`). Confirmar si debe ser atribución **exclusiva** de Coordinación (hoy lo es: el endpoint exige rol Coordinación).
- **TLS / TC-001-06** (CEPA-001 RN-2): el rechazo de tráfico no cifrado se resuelve en el **proxy/nginx** (terminación TLS y redirección 301 HTTP→HTTPS / HSTS), no en el código FastAPI; se documenta en el runbook de despliegue de la Fundación. La app asume tráfico ya cifrado por el proxy.
- **Auditoría de lecturas sensibles** (CEPA-003 Notas, RN-1 "leer-sensible"): este plan audita escrituras y eventos de login/bloqueo. Si se confirma que las lecturas de datos sensibles también deben dejar traza, se añade un `record_audit(..., action="READ")` en los endpoints de lectura de las épicas de dominio (decisión transversal pendiente).
- **Política de retención del log** (CEPA-003 Notas, PA3/D13): fuera del alcance de esta épica; definir con normativa institucional de datos de salud mental.

### Portabilidad (D15) — punto de atención
- El **único SQL específico por dialecto** vive en la migración `0003` (trigger de inmutabilidad), seleccionado por `op.get_bind().dialect.name`. El job **Oracle gated** del CI valida la rama Oracle del trigger; si Oracle aún no está habilitado, ese job es *allowed-to-fail* y debe revisarse manualmente la sintaxis PL/SQL antes de producción.
- Todo lo demás (modelos, servicios, routers) es **agnóstico del motor**: tipos genéricos, `Identity`, identificadores ≤30 chars en minúscula, fechas UTC.
