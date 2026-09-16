# Sync SALUTEM fase 1 — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copiar todo SALUTEM (empresa 96) al CEPA desde el primer día con datos, mantenerlo al día cada 5 minutos y vincular las atenciones con `ficha_clinica`, sin escribir nunca en SALUTEM.

**Architecture:** Dos pasos desacoplados. (1) *Copiar*: barridos por día contra la API (solo GET) guardan personas, citas y atenciones crudas en tablas `salutem_*`, con hash para detectar cambios y marca de desaparición. (2) *Vincular*: sin red, pasa la copia a `ficha_clinica` por RUT y ventana del ingreso. Un CLI lanzado por cron ejecuta los modos `backfill`/`caliente`/`tibia`/`fria`/`vincular` con lease en BD y bitácora.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (Postgres en dev/CI y Oracle 19c en la VM), Alembic, httpx, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-09-16-salutem-sync-fase1-design.md`

---

## Convenciones que el ejecutor debe conocer

- Todo comando corre desde `backend/`. Tests: `uv run pytest <ruta> -v`. Lint: `uv run ruff check app tests`.
- Los tests usan Postgres local (`postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test`, ver `tests/conftest.py`). Si no está arriba: `docker compose up -d db` desde `backend/` (revisar `backend/docker-compose.yml`). La sesión de tests corre `alembic upgrade head` una vez; cada test usa `db_session`, que envuelve todo en una transacción que se revierte. **Los `db.commit()` de los servicios son seguros en tests** (operan sobre un savepoint).
- `SessionLocal` usa `autoflush=False`: después de `db.add(...)` hay que hacer `db.flush()` si luego se consulta o se hace `db.get(...)` del mismo objeto.
- Portabilidad Oracle: nombres de tabla/índice ≤ 30 caracteres; nunca `.is_(False)` (usar `== false()`); `.is_(None)` sí funciona; no usar `hash` como nombre de columna; no comparar en Python datetimes leídos de la BD (Oracle puede devolverlos sin zona): comparar en SQL.
- **D12:** el cliente SALUTEM es solo lectura. Ningún código nuevo nombra métodos del cliente con create/update/delete/push/write/patch.
- Commits en español, estilo Conventional Commits, terminando con `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Rama de trabajo: `claude/salutem-realtime-sync-0315fd` (ya existe; la spec está commiteada ahí).

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `app/config.py` (mod) | Settings del sync: bandera, ritmo, días vacíos, ruta de log |
| `app/integrations/salutem/protocol.py`, `client.py` (mod) | `obtener_persona(salutem_id)` |
| `app/models/salutem_copia.py` (nuevo) | `SalutemPersona`, `SalutemCita`, `SalutemAtencion` |
| `app/models/salutem_sync.py` (nuevo) | `SalutemSyncDia`, `SalutemSyncEjecucion`, `SalutemSyncLease` |
| `app/models/ficha_clinica.py` (mod) | columnas `salutem_cita_id`, `eliminada_en_origen` |
| `app/models/__init__.py` (mod) | registrar modelos nuevos |
| `migrations/versions/1250_salutem_copia.py` (nuevo) | tablas, columnas, lease sembrado, relleno de `salutem_cita_id` |
| `app/services/salutem_sync/__init__.py` (nuevo) | paquete |
| `app/services/salutem_sync/tipos.py` | `Resultado`, `Contadores`, `MODOS` |
| `app/services/salutem_sync/hash.py` | hash canónico |
| `app/services/salutem_sync/ritmo.py` | limitador + reintentos |
| `app/services/salutem_sync/lease.py` | tomar/soltar lease |
| `app/services/salutem_sync/bitacora.py` | abrir/cerrar ejecución |
| `app/services/salutem_sync/copia.py` | guardado con detección de cambios |
| `app/services/salutem_sync/barrido.py` | barrer un día, traer atención/persona, refrescar atenciones |
| `app/services/salutem_sync/backfill.py` | carga inicial reanudable + verificación |
| `app/services/salutem_sync/incremental.py` | ventanas caliente/tibia/fría |
| `app/services/salutem_sync/vinculacion.py` | copia → `ficha_clinica` |
| `app/services/salutem_sync/orquestador.py` | `correr(modo, ...)`: lease, bitácora, errores |
| `app/services/salutem_sync/estado.py` | estado del sync |
| `app/schemas/salutem_sync.py` | `EjecucionRead`, `EstadoSyncRead` |
| `app/routers/salutem_sync.py` + `app/main.py` (mod) | `GET /api/v1/salutem/sync/estado` |
| `app/scripts/salutem_sync.py` | CLI |
| `app/services/ficha_clinica.py`, `licencias_sugeridas.py`, `schemas/ficha_clinica.py` (mod) | pull manual deduplica por `salutem_cita_id`; licencias ignoran eliminadas |
| `tests/salutem_falso.py` | SALUTEM en memoria |
| `tests/salutem_sync/` | tests del sync |
| `ops/vm/run-salutem-sync.sh`, `ops/vm/crontab-salutem-sync.txt` | operación en la VM |
| `docs/operacion/salutem-sync.md` | runbook |

---

### Task 1: Configuración y `obtener_persona` en el cliente

**Files:**
- Modify: `backend/app/config.py` (bloque SALUTEM, después de `salutem_timeout_s`)
- Modify: `backend/app/integrations/salutem/protocol.py`
- Modify: `backend/app/integrations/salutem/client.py`
- Test: `backend/tests/test_salutem_http_client.py` (agregar al final)
- Test: `backend/tests/salutem_sync/__init__.py` (vacío), `backend/tests/salutem_sync/test_config.py`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/salutem_sync/__init__.py` vacío y `backend/tests/salutem_sync/test_config.py`:

```python
from app.config import Settings


def test_el_sync_viene_apagado_y_con_ritmo_conservador():
    s = Settings(_env_file=None)
    assert s.salutem_sync_habilitado is False
    assert s.salutem_sync_llamadas_por_seg == 2.0
    assert s.salutem_backfill_dias_vacios == 365
    assert s.salutem_sync_log == ""
```

Agregar al final de `backend/tests/test_salutem_http_client.py`:

```python
# ── obtener_persona (sync fase 1) ─────────────────────────────────────────────


def test_obtener_persona_envia_persona_id_en_el_cuerpo():
    vistos = []

    def handler(request):
        vistos.append((request.url.path, json.loads(request.content)))
        return _ok(
            {"demograficos": {"SALUTEM_ID": 338735, "identificacion": "11168636-k", "nombres": "ALEX"}}
        )

    persona = _cliente(handler).obtener_persona(338735)

    assert persona is not None
    assert persona.salutem_id == 338735
    assert vistos == [
        (
            f"/api/integraciones/salutem/{EMPRESA}/personas",
            {"persona_id": 338735, "agrupacion": "demograficos"},
        )
    ]


def test_obtener_persona_inexistente_devuelve_none():
    cliente = _cliente(lambda request: _falla("ERROR_PERSONA_NO_EXISTE"))
    assert cliente.obtener_persona(1) is None


def test_stub_obtener_persona_devuelve_none():
    from app.integrations.salutem.client import SalutemStubClient

    assert SalutemStubClient().obtener_persona(1) is None
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_config.py tests/test_salutem_http_client.py -v -k "sync or obtener_persona"`
Expected: FAIL (`AttributeError: 'Settings' object has no attribute 'salutem_sync_habilitado'` y `'SalutemHttpClient' object has no attribute 'obtener_persona'`).

- [ ] **Step 3: Implementar**

En `backend/app/config.py`, justo después de `salutem_timeout_s: float = 30.0`:

```python

    # --- Sync SALUTEM (fase 1, solo lectura) ---
    # Apagado por defecto: el cron puede quedar instalado sin que nada salga a la red.
    salutem_sync_habilitado: bool = False
    # No se conoce el límite de la API: se parte conservador y se ajusta con FabricApp.
    salutem_sync_llamadas_por_seg: float = 2.0
    # La carga inicial se detiene tras esta cantidad de días seguidos sin citas.
    salutem_backfill_dias_vacios: int = 365
    # Vacío = log a stderr. En la VM: ~/sige-cepa/logs/salutem-sync.log
    salutem_sync_log: str = ""
```

En `backend/app/integrations/salutem/protocol.py`, dentro de `SalutemClientProtocol`, después de `resolver_persona`:

```python
    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        """Trae una persona por su id de SALUTEM. None si no existe.

        El sync conoce a las personas por el `personaId` de sus citas, no por RUT.
        """
        ...
```

En `backend/app/integrations/salutem/client.py`, en `SalutemStubClient` después de `resolver_persona`:

```python
    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:  # noqa: ARG002
        return None
```

Y en `SalutemHttpClient`, después de `resolver_persona`:

```python
    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        r = self._get("personas", {"persona_id": salutem_id, "agrupacion": "demograficos"})
        if not r or "demograficos" not in r:
            return None
        return PersonaSalutem.desde_api(r["demograficos"])
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_config.py tests/test_salutem_http_client.py tests/test_salutem_no_escribe.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add app/config.py app/integrations/salutem/protocol.py app/integrations/salutem/client.py tests/test_salutem_http_client.py tests/salutem_sync/__init__.py tests/salutem_sync/test_config.py
git commit -m "feat(salutem): configuración del sync y obtener_persona por id

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Modelos y migración 1250

**Files:**
- Create: `backend/app/models/salutem_copia.py`
- Create: `backend/app/models/salutem_sync.py`
- Modify: `backend/app/models/ficha_clinica.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/1250_salutem_copia.py`
- Test: `backend/tests/salutem_sync/test_migracion.py`

- [ ] **Step 1: Escribir el test que falla**

`backend/tests/salutem_sync/test_migracion.py`:

```python
"""Migración 1250: copia de SALUTEM, checkpoint, bitácora, lease y columnas de ficha_clinica."""

import importlib.util
from pathlib import Path

from sqlalchemy import inspect

from app.db.session import engine
from app.models.ficha_clinica import FichaClinica
from app.models.salutem_sync import SalutemSyncLease


def _migracion():
    ruta = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "1250_salutem_copia.py"
    spec = importlib.util.spec_from_file_location("migracion_1250", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_tablas_del_sync_existen():
    insp = inspect(engine)
    for nombre in [
        "salutem_persona",
        "salutem_cita",
        "salutem_atencion",
        "salutem_sync_dia",
        "salutem_sync_ejecucion",
        "salutem_sync_lease",
    ]:
        assert insp.has_table(nombre), f"Falta la tabla {nombre!r}"
    columnas = {c["name"] for c in insp.get_columns("ficha_clinica")}
    assert {"salutem_cita_id", "eliminada_en_origen"} <= columnas


def test_el_lease_viene_sembrado_y_libre(db_session):
    lease = db_session.get(SalutemSyncLease, "salutem")
    assert lease is not None
    assert lease.dueno is None


def test_rellena_salutem_cita_id_desde_el_contenido(db_session, ingreso_fixture):
    de_salutem = FichaClinica(
        ingreso_id=ingreso_fixture.id,
        folio=ingreso_fixture.folio,
        origen="SALUTEM",
        contenido={"citaId": 425562},
    )
    de_push = FichaClinica(
        ingreso_id=ingreso_fixture.id,
        folio=ingreso_fixture.folio,
        origen="SAM",
        contenido={"citaId": 1},
    )
    db_session.add_all([de_salutem, de_push])
    db_session.flush()

    rellenadas = _migracion().rellenar_salutem_cita_id(db_session.connection())
    db_session.expire_all()

    assert rellenadas >= 1
    assert db_session.get(FichaClinica, de_salutem.id).salutem_cita_id == 425562
    assert db_session.get(FichaClinica, de_push.id).salutem_cita_id is None
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `uv run pytest tests/salutem_sync/test_migracion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.salutem_sync'`.

- [ ] **Step 3: Crear los modelos**

`backend/app/models/salutem_copia.py`:

```python
"""Copia local de SALUTEM (sync fase 1, solo lectura — D12).

Guarda lo que devuelve SALUTEM tal cual, con un hash para detectar cambios.
Nunca se borra una fila: lo que deja de aparecer en SALUTEM se marca con
`desaparecida_en`. El dominio CEPA no lee estas tablas directamente; la
vinculación (services/salutem_sync/vinculacion.py) las pasa a ficha_clinica.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import PortableJSON


class _RegistroCopia:
    """Columnas comunes: contenido crudo, hash y marcas de tiempo."""

    contenido: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    # `hash` a secas es palabra clave en Oracle.
    hash_contenido: Mapped[str] = mapped_column(String(64), nullable=False)
    visto_primera_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    visto_ultima_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cambiado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SalutemPersona(_RegistroCopia, Base):
    __tablename__ = "salutem_persona"

    salutem_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    # RUT en la forma canónica del CEPA (`<cuerpo><DV>`); None si SALUTEM no trae uno válido.
    rut: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)


class SalutemCita(_RegistroCopia, Base):
    __tablename__ = "salutem_cita"

    cita_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    # Sin FK: la cita puede llegar antes que su persona.
    persona_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    fecha_cita: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fecha_creacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estado_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    desaparecida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SalutemAtencion(_RegistroCopia, Base):
    __tablename__ = "salutem_atencion"

    cita_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    persona_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    fecha_cita: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # Hash que la vinculación ya aplicó a ficha_clinica. Distinto de hash_contenido = pendiente.
    hash_vinculado: Mapped[str | None] = mapped_column(String(64), nullable=True)
    desaparecida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`backend/app/models/salutem_sync.py`:

```python
"""Control del sync SALUTEM: checkpoint por día, bitácora de ejecuciones y lease."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SalutemSyncDia(Base):
    """Día ya barrido por completo en la carga inicial (permite reanudarla)."""

    __tablename__ = "salutem_sync_dia"

    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    tipo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    citas: Mapped[int] = mapped_column(Integer, nullable=False)
    completado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SalutemSyncEjecucion(Base):
    """Bitácora: una fila por ejecución de un modo del sync."""

    __tablename__ = "salutem_sync_ejecucion"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    modo: Mapped[str] = mapped_column(String(20), nullable=False)
    # en_curso | ok | con_errores | error | omitida
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llamadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nuevos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cambiados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    desaparecidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class SalutemSyncLease(Base):
    """Un solo proceso de sync a la vez. La fila `salutem` la siembra la migración 1250."""

    __tablename__ = "salutem_sync_lease"

    nombre: Mapped[str] = mapped_column(String(30), primary_key=True)
    dueno: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

En `backend/app/models/ficha_clinica.py`: agregar `Index` al import de sqlalchemy (`from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String`) y, dentro de `FichaClinica`, después de `__tablename__`:

```python
    # Índice no único a propósito: los push externos dejan salutem_cita_id en NULL y
    # Oracle consideraría duplicadas dos filas (ingreso_id, NULL) en un índice único.
    __table_args__ = (Index("ix_ficha_clin_sal_cita", "salutem_cita_id"),)
```

y después de `created_at`:

```python
    # Id de la cita en SALUTEM cuando origen = SALUTEM; clave de deduplicación del sync.
    salutem_cita_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # La atención dejó de existir en SALUTEM. La ficha se conserva, marcada.
    eliminada_en_origen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

En `backend/app/models/__init__.py`, al final:

```python
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona  # noqa: F401
from app.models.salutem_sync import (  # noqa: F401
    SalutemSyncDia,
    SalutemSyncEjecucion,
    SalutemSyncLease,
)
```

- [ ] **Step 4: Crear la migración**

`backend/migrations/versions/1250_salutem_copia.py`:

```python
"""Sync SALUTEM fase 1: copia local, checkpoint, bitácora, lease y columnas en ficha_clinica

Revision ID: 1250
Revises: 1240
"""

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from app.db.types import PortableJSON

revision = "1250"
down_revision = "1240"
branch_labels = None
depends_on = None


def _columnas_copia() -> list[sa.Column]:
    # Objetos nuevos en cada llamada: una Column no puede pertenecer a dos tablas.
    return [
        sa.Column("contenido", PortableJSON(), nullable=False),
        sa.Column("hash_contenido", sa.String(length=64), nullable=False),
        sa.Column("visto_primera_vez", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visto_ultima_vez", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cambiado_en", sa.DateTime(timezone=True), nullable=False),
    ]


def rellenar_salutem_cita_id(conn) -> int:
    """Copia contenido.citaId a la columna nueva en las fichas de SALUTEM.

    Se hace en Python porque en Oracle el JSON es un CLOB y no hay una
    expresión SQL portable para leerlo.
    """
    filas = conn.execute(
        sa.text("SELECT id, contenido FROM ficha_clinica WHERE origen = 'SALUTEM'")
    ).all()
    rellenadas = 0
    for fila_id, contenido in filas:
        if hasattr(contenido, "read"):  # LOB de Oracle
            contenido = contenido.read()
        if isinstance(contenido, str):
            contenido = json.loads(contenido)
        cita_id = (contenido or {}).get("citaId")
        if cita_id is None:
            continue
        conn.execute(
            sa.text("UPDATE ficha_clinica SET salutem_cita_id = :cita WHERE id = :id"),
            {"cita": int(cita_id), "id": fila_id},
        )
        rellenadas += 1
    return rellenadas


def upgrade() -> None:
    op.create_table(
        "salutem_persona",
        sa.Column("salutem_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("rut", sa.String(length=12), nullable=True),
        *_columnas_copia(),
    )
    op.create_index("ix_salutem_persona_rut", "salutem_persona", ["rut"])

    op.create_table(
        "salutem_cita",
        sa.Column("cita_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_cita", sa.Date(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("estado_id", sa.Integer(), nullable=True),
        *_columnas_copia(),
        sa.Column("desaparecida_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_salutem_cita_persona_id", "salutem_cita", ["persona_id"])
    op.create_index("ix_salutem_cita_fecha_cita", "salutem_cita", ["fecha_cita"])

    op.create_table(
        "salutem_atencion",
        sa.Column("cita_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_cita", sa.Date(), nullable=True),
        *_columnas_copia(),
        sa.Column("hash_vinculado", sa.String(length=64), nullable=True),
        sa.Column("desaparecida_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_salutem_atencion_persona_id", "salutem_atencion", ["persona_id"])
    op.create_index("ix_salutem_atencion_fecha_cita", "salutem_atencion", ["fecha_cita"])

    op.create_table(
        "salutem_sync_dia",
        sa.Column("fecha", sa.Date(), primary_key=True),
        sa.Column("tipo", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("citas", sa.Integer(), nullable=False),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "salutem_sync_ejecucion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("modo", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("llamadas", sa.Integer(), nullable=False),
        sa.Column("nuevos", sa.Integer(), nullable=False),
        sa.Column("cambiados", sa.Integer(), nullable=False),
        sa.Column("desaparecidos", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=2000), nullable=True),
    )

    lease = op.create_table(
        "salutem_sync_lease",
        sa.Column("nombre", sa.String(length=30), primary_key=True),
        sa.Column("dueno", sa.String(length=80), nullable=True),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.bulk_insert(
        lease,
        [{"nombre": "salutem", "dueno": None, "vence_en": datetime(2000, 1, 1, tzinfo=timezone.utc)}],
    )

    op.add_column("ficha_clinica", sa.Column("salutem_cita_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "ficha_clinica",
        sa.Column("eliminada_en_origen", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ficha_clin_sal_cita", "ficha_clinica", ["salutem_cita_id"])
    rellenar_salutem_cita_id(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_ficha_clin_sal_cita", table_name="ficha_clinica")
    op.drop_column("ficha_clinica", "eliminada_en_origen")
    op.drop_column("ficha_clinica", "salutem_cita_id")
    op.drop_table("salutem_sync_lease")
    op.drop_table("salutem_sync_ejecucion")
    op.drop_table("salutem_sync_dia")
    op.drop_index("ix_salutem_atencion_fecha_cita", table_name="salutem_atencion")
    op.drop_index("ix_salutem_atencion_persona_id", table_name="salutem_atencion")
    op.drop_table("salutem_atencion")
    op.drop_index("ix_salutem_cita_fecha_cita", table_name="salutem_cita")
    op.drop_index("ix_salutem_cita_persona_id", table_name="salutem_cita")
    op.drop_table("salutem_cita")
    op.drop_index("ix_salutem_persona_rut", table_name="salutem_persona")
    op.drop_table("salutem_persona")
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `uv run pytest tests/salutem_sync/test_migracion.py tests/test_fichas_clinicas_api.py tests/test_salutem_no_escribe.py -v`
Expected: PASS.

Verificar también el ciclo completo de la migración contra la BD de tests:
Run: `DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade 1240 && DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head`
Expected: ambos terminan sin error.

- [ ] **Step 6: Commit**

```bash
git add app/models/salutem_copia.py app/models/salutem_sync.py app/models/ficha_clinica.py app/models/__init__.py migrations/versions/1250_salutem_copia.py tests/salutem_sync/test_migracion.py
git commit -m "feat(salutem): tablas de la copia local, bitácora y lease del sync (migración 1250)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: SALUTEM falso, tipos, hash y ritmo

**Files:**
- Create: `backend/tests/salutem_falso.py`
- Create: `backend/tests/salutem_sync/conftest.py`
- Create: `backend/app/services/salutem_sync/__init__.py`
- Create: `backend/app/services/salutem_sync/tipos.py`
- Create: `backend/app/services/salutem_sync/hash.py`
- Create: `backend/app/services/salutem_sync/ritmo.py`
- Test: `backend/tests/salutem_sync/test_hash_ritmo.py`

- [ ] **Step 1: Crear el doble de prueba y los fixtures**

`backend/tests/salutem_falso.py`:

```python
"""SALUTEM en memoria para probar el sync sin red.

Implementa `SalutemClientProtocol` con los mismos formatos crudos que la API
real (claves camelCase, fechas como string) y registra cada llamada.
"""

from datetime import date

from app.integrations.salutem.errors import (
    SalutemAuthError,
    SalutemRequestError,
    SalutemUnavailableError,
)
from app.integrations.salutem.models import (
    AtencionSalutem,
    CitaSalutem,
    EstadoCitaSalutem,
    PersonaSalutem,
    TipoFechaCita,
)


class SalutemFalso:
    def __init__(self) -> None:
        self.personas: dict[int, dict] = {}
        self.citas: dict[int, dict] = {}
        self.atenciones: dict[int, dict] = {}
        self.llamadas: list[tuple] = []
        # (dia, estado) que SALUTEM rechaza con SalutemRequestError.
        self.dias_con_error: set[tuple[date, int]] = set()
        # Cuántas de las próximas llamadas fallan con SalutemUnavailableError.
        self.caidas_pendientes = 0
        self.credencial_rechazada = False

    # ── Carga de datos ─────────────────────────────────────────────────────
    def agregar_persona(self, salutem_id: int, rut: str = "12345678-5", **extra) -> None:
        self.personas[salutem_id] = {
            "SALUTEM_ID": salutem_id,
            "identificacion": rut,
            "tipoIdentificacion": "RUT",
            **extra,
        }

    def agregar_cita(
        self,
        cita_id: int,
        persona_id: int,
        fecha: date,
        estado: int = EstadoCitaSalutem.ATENDIDO,
        creada: str | None = None,
        **extra,
    ) -> None:
        self.citas[cita_id] = {
            "personaId": persona_id,
            "citaId": cita_id,
            "citaFecha": fecha.isoformat(),
            "citaFechaCreacion": creada or f"{fecha.isoformat()} 08:00",
            "estadoCitaId": int(estado),
            **extra,
        }

    def agregar_atencion(self, cita_id: int, **contenido) -> None:
        self.atenciones[cita_id] = {"anamnesis": "", **contenido}

    # ── Protocolo ──────────────────────────────────────────────────────────
    def _registrar(self, *llamada) -> None:
        self.llamadas.append(llamada)
        if self.credencial_rechazada:
            raise SalutemAuthError("credencial rechazada", codigo="API_KEY_NO_VALIDA")
        if self.caidas_pendientes > 0:
            self.caidas_pendientes -= 1
            raise SalutemUnavailableError("caída simulada")

    def resolver_persona(self, rut: str) -> PersonaSalutem | None:
        self._registrar("resolver_persona", rut)
        for p in self.personas.values():
            if p["identificacion"] == rut:
                return PersonaSalutem.desde_api(p)
        return None

    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        self._registrar("obtener_persona", salutem_id)
        p = self.personas.get(salutem_id)
        return PersonaSalutem.desde_api(p) if p else None

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:
        self._registrar("listar_atenciones", salutem_id)
        return [
            CitaSalutem.desde_api(self.citas[cita_id])
            for cita_id in self.atenciones
            if self.citas[cita_id]["personaId"] == salutem_id
        ]

    def obtener_atencion(self, salutem_id: int, cita_id: int) -> AtencionSalutem | None:
        self._registrar("obtener_atencion", salutem_id, cita_id)
        cita = self.citas.get(cita_id)
        if cita_id not in self.atenciones or cita is None or cita["personaId"] != salutem_id:
            return None
        return AtencionSalutem.desde_api({**cita, **self.atenciones[cita_id]})

    def listar_citas(
        self,
        dia: date,
        estado: EstadoCitaSalutem,
        por: TipoFechaCita = TipoFechaCita.FECHA_CITA,
    ) -> list[CitaSalutem]:
        self._registrar("listar_citas", dia, int(estado), int(por))
        if (dia, int(estado)) in self.dias_con_error:
            raise SalutemRequestError("rechazada", codigo="ERROR_INTERVALO_SUPERADO")
        campo = "citaFecha" if por == TipoFechaCita.FECHA_CITA else "citaFechaCreacion"
        return [
            CitaSalutem.desde_api(c)
            for c in self.citas.values()
            if c[campo][:10] == dia.isoformat() and c["estadoCitaId"] == int(estado)
        ]

    def llamadas_a(self, metodo: str) -> list[tuple]:
        return [ll for ll in self.llamadas if ll[0] == metodo]
```

`backend/tests/salutem_sync/conftest.py`:

```python
from datetime import datetime, timezone

import pytest

from app.services.salutem_sync.ritmo import Ritmo
from tests.salutem_falso import SalutemFalso

# 12:00 en Santiago (UTC-3 en septiembre).
AHORA = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def salutem() -> SalutemFalso:
    return SalutemFalso()


@pytest.fixture
def ritmo() -> Ritmo:
    """Sin límite de frecuencia ni esperas reales."""
    return Ritmo(0, dormir=lambda segundos: None)
```

- [ ] **Step 2: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_hash_ritmo.py`:

```python
import pytest

from app.integrations.salutem.errors import SalutemAuthError, SalutemUnavailableError
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.services.salutem_sync import hash as modulo_hash
from app.services.salutem_sync.hash import hash_contenido
from app.services.salutem_sync.ritmo import Ritmo
from tests.salutem_falso import SalutemFalso


def test_el_falso_cumple_el_protocolo():
    assert isinstance(SalutemFalso(), SalutemClientProtocol)


# ── hash ─────────────────────────────────────────────────────────────────────


def test_hash_no_depende_del_orden_de_las_claves():
    assert hash_contenido({"a": 1, "b": {"x": 1, "y": 2}}) == hash_contenido(
        {"b": {"y": 2, "x": 1}, "a": 1}
    )


def test_hash_cambia_con_el_contenido():
    h = hash_contenido({"anamnesis": "uno"})
    assert h != hash_contenido({"anamnesis": "dos"})
    assert len(h) == 64


def test_hash_ignora_campos_volatiles(monkeypatch):
    monkeypatch.setattr(modulo_hash, "CAMPOS_VOLATILES", frozenset({"tamanioBytes"}))
    assert hash_contenido({"a": 1, "tamanioBytes": 10}) == hash_contenido({"a": 1, "tamanioBytes": 99})


# ── ritmo ────────────────────────────────────────────────────────────────────


def test_espacia_las_llamadas_segun_la_frecuencia():
    dormidas: list[float] = []
    ritmo = Ritmo(2, dormir=dormidas.append, reloj=lambda: 10.0)

    ritmo.llamar(lambda: 1)
    ritmo.llamar(lambda: 1)

    assert dormidas == [0.5]
    assert ritmo.llamadas == 2


def test_reintenta_caidas_y_se_recupera():
    dormidas: list[float] = []
    intentos = {"n": 0}

    def inestable():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise SalutemUnavailableError("caída")
        return "ok"

    ritmo = Ritmo(0, dormir=dormidas.append)

    assert ritmo.llamar(inestable) == "ok"
    assert dormidas == [2.0, 4.0]
    assert ritmo.llamadas == 3


def test_tras_tres_reintentos_propaga_la_caida():
    dormidas: list[float] = []

    def caido():
        raise SalutemUnavailableError("caída")

    ritmo = Ritmo(0, dormir=dormidas.append)

    with pytest.raises(SalutemUnavailableError):
        ritmo.llamar(caido)
    assert dormidas == [2.0, 4.0, 8.0]
    assert ritmo.llamadas == 4


def test_no_reintenta_una_credencial_rechazada():
    def rechazo():
        raise SalutemAuthError("no")

    ritmo = Ritmo(0, dormir=lambda s: None)

    with pytest.raises(SalutemAuthError):
        ritmo.llamar(rechazo)
    assert ritmo.llamadas == 1
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_hash_ritmo.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync'`.

- [ ] **Step 4: Implementar**

`backend/app/services/salutem_sync/__init__.py`:

```python
"""Sync SALUTEM fase 1 (solo lectura, D12). Ver docs/superpowers/specs/2026-09-16-salutem-sync-fase1-design.md."""
```

`backend/app/services/salutem_sync/tipos.py`:

```python
"""Tipos compartidos por los módulos del sync."""

from dataclasses import dataclass
from enum import Enum

MODOS = ("backfill", "caliente", "tibia", "fria", "vincular")


class Resultado(Enum):
    """Qué pasó al guardar un registro en la copia."""

    NUEVO = "nuevo"
    CAMBIADO = "cambiado"
    IGUAL = "igual"


@dataclass
class Contadores:
    nuevos: int = 0
    cambiados: int = 0
    desaparecidos: int = 0

    def registrar(self, resultado: Resultado) -> None:
        if resultado is Resultado.NUEVO:
            self.nuevos += 1
        elif resultado is Resultado.CAMBIADO:
            self.cambiados += 1

    def sumar(self, otros: "Contadores") -> None:
        self.nuevos += otros.nuevos
        self.cambiados += otros.cambiados
        self.desaparecidos += otros.desaparecidos
```

`backend/app/services/salutem_sync/hash.py`:

```python
"""Hash canónico del contenido que devuelve SALUTEM.

Dos respuestas con los mismos datos deben dar el mismo hash aunque cambie el
orden de las claves. Si la validación en QA muestra campos que cambian entre
consultas sin un cambio real, se agregan a CAMPOS_VOLATILES.
"""

import hashlib
import json
from typing import Any

CAMPOS_VOLATILES: frozenset[str] = frozenset()


def hash_contenido(contenido: dict[str, Any]) -> str:
    limpio = {k: v for k, v in contenido.items() if k not in CAMPOS_VOLATILES}
    canonico = json.dumps(
        limpio, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
```

`backend/app/services/salutem_sync/ritmo.py`:

```python
"""Ritmo de llamadas a SALUTEM: limita la frecuencia y reintenta caídas.

Solo se reintenta `SalutemUnavailableError` (timeout, cuerpo ilegible). Una
credencial rechazada o una petición inválida no mejoran insistiendo.
"""

import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.integrations.salutem.errors import SalutemUnavailableError

T = TypeVar("T")

ESPERAS_REINTENTO_S = (2.0, 4.0, 8.0)


class Ritmo:
    def __init__(
        self,
        llamadas_por_seg: float,
        *,
        dormir: Callable[[float], None] = time.sleep,
        reloj: Callable[[], float] = time.monotonic,
        esperas_reintento: tuple[float, ...] = ESPERAS_REINTENTO_S,
    ) -> None:
        self._intervalo = 1.0 / llamadas_por_seg if llamadas_por_seg > 0 else 0.0
        self._dormir = dormir
        self._reloj = reloj
        self._esperas = esperas_reintento
        self._ultima: float | None = None
        self.llamadas = 0

    def llamar(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        for intento in range(len(self._esperas) + 1):
            self._esperar_turno()
            self.llamadas += 1
            try:
                return fn(*args, **kwargs)
            except SalutemUnavailableError:
                if intento == len(self._esperas):
                    raise
                self._dormir(self._esperas[intento])
        raise AssertionError("inalcanzable")

    def _esperar_turno(self) -> None:
        if self._ultima is not None and self._intervalo:
            falta = self._intervalo - (self._reloj() - self._ultima)
            if falta > 0:
                self._dormir(falta)
        self._ultima = self._reloj()
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_hash_ritmo.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add tests/salutem_falso.py tests/salutem_sync/conftest.py tests/salutem_sync/test_hash_ritmo.py app/services/salutem_sync/
git commit -m "feat(salutem): hash canónico, ritmo de llamadas y SALUTEM falso para tests

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Lease y bitácora

**Files:**
- Create: `backend/app/services/salutem_sync/lease.py`
- Create: `backend/app/services/salutem_sync/bitacora.py`
- Test: `backend/tests/salutem_sync/test_lease_bitacora.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_lease_bitacora.py`:

```python
from datetime import timedelta

from app.models.salutem_sync import SalutemSyncEjecucion, SalutemSyncLease
from app.services.salutem_sync.bitacora import abrir_ejecucion, cerrar_ejecucion, registrar_omitida
from app.services.salutem_sync.lease import soltar_lease, tomar_lease
from app.services.salutem_sync.tipos import Contadores
from tests.salutem_sync.conftest import AHORA


def test_toma_el_lease_libre(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)


def test_otro_proceso_no_puede_tomar_un_lease_vigente(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    assert not tomar_lease(db_session, "proceso-b", AHORA + timedelta(minutes=1))


def test_el_mismo_dueno_lo_renueva(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    assert tomar_lease(db_session, "proceso-a", AHORA + timedelta(minutes=5))


def test_un_lease_vencido_se_recupera(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    assert tomar_lease(db_session, "proceso-b", AHORA + timedelta(minutes=11))


def test_soltar_lo_libera(db_session):
    assert tomar_lease(db_session, "proceso-a", AHORA)
    soltar_lease(db_session, "proceso-a")
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None
    assert tomar_lease(db_session, "proceso-b", AHORA)


def test_bitacora_abre_y_cierra_con_contadores(db_session):
    ejecucion = abrir_ejecucion(db_session, "caliente", AHORA)
    assert ejecucion.estado == "en_curso"

    cerrar_ejecucion(
        db_session,
        ejecucion,
        estado="ok",
        ahora=AHORA + timedelta(minutes=1),
        llamadas=36,
        contadores=Contadores(nuevos=2, cambiados=1, desaparecidos=0),
    )

    guardada = db_session.get(SalutemSyncEjecucion, ejecucion.id)
    assert (guardada.estado, guardada.llamadas, guardada.nuevos, guardada.cambiados) == ("ok", 36, 2, 1)
    assert guardada.fin is not None


def test_bitacora_recorta_errores_largos(db_session):
    ejecucion = abrir_ejecucion(db_session, "tibia", AHORA)
    cerrar_ejecucion(db_session, ejecucion, estado="error", ahora=AHORA, error="x" * 5000)
    assert len(db_session.get(SalutemSyncEjecucion, ejecucion.id).error) == 2000


def test_registra_una_ejecucion_omitida(db_session):
    omitida = registrar_omitida(db_session, "caliente", AHORA)
    assert db_session.get(SalutemSyncEjecucion, omitida.id).estado == "omitida"
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_lease_bitacora.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync.bitacora'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/lease.py`:

```python
"""Lease en base de datos: un solo proceso de sync a la vez.

No usa SELECT FOR UPDATE: una carga inicial dura horas y mantener una
transacción abierta tanto tiempo en Oracle es frágil. El lease vence solo, así
que un proceso que muere lo libera al cabo de DURACION.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.models.salutem_sync import SalutemSyncLease

NOMBRE = "salutem"
DURACION = timedelta(minutes=10)
_LIBRE = datetime(2000, 1, 1, tzinfo=timezone.utc)


def tomar_lease(
    db: Session, dueno: str, ahora: datetime, duracion: timedelta = DURACION
) -> bool:
    """Toma o renueva el lease. False si otro proceso lo tiene vigente. Confirma la transacción."""
    resultado = db.execute(
        update(SalutemSyncLease)
        .where(
            SalutemSyncLease.nombre == NOMBRE,
            or_(SalutemSyncLease.vence_en < ahora, SalutemSyncLease.dueno == dueno),
        )
        .values(dueno=dueno, vence_en=ahora + duracion)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return resultado.rowcount == 1


def soltar_lease(db: Session, dueno: str) -> None:
    db.execute(
        update(SalutemSyncLease)
        .where(SalutemSyncLease.nombre == NOMBRE, SalutemSyncLease.dueno == dueno)
        .values(dueno=None, vence_en=_LIBRE)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
```

`backend/app/services/salutem_sync/bitacora.py`:

```python
"""Bitácora de ejecuciones del sync (tabla salutem_sync_ejecucion)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync.tipos import Contadores

_MAX_ERROR = 2000


def abrir_ejecucion(db: Session, modo: str, ahora: datetime) -> SalutemSyncEjecucion:
    ejecucion = SalutemSyncEjecucion(
        modo=modo, estado="en_curso", inicio=ahora,
        llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    db.add(ejecucion)
    db.commit()
    return ejecucion


def cerrar_ejecucion(
    db: Session,
    ejecucion: SalutemSyncEjecucion,
    *,
    estado: str,
    ahora: datetime,
    llamadas: int = 0,
    contadores: Contadores | None = None,
    error: str | None = None,
) -> None:
    contadores = contadores or Contadores()
    ejecucion.estado = estado
    ejecucion.fin = ahora
    ejecucion.llamadas = llamadas
    ejecucion.nuevos = contadores.nuevos
    ejecucion.cambiados = contadores.cambiados
    ejecucion.desaparecidos = contadores.desaparecidos
    ejecucion.error = error[:_MAX_ERROR] if error else None
    db.commit()


def registrar_omitida(db: Session, modo: str, ahora: datetime) -> SalutemSyncEjecucion:
    """Otro proceso tenía el lease: se deja constancia y no se hace nada."""
    ejecucion = SalutemSyncEjecucion(
        modo=modo, estado="omitida", inicio=ahora, fin=ahora,
        llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    db.add(ejecucion)
    db.commit()
    return ejecucion
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_lease_bitacora.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/lease.py app/services/salutem_sync/bitacora.py tests/salutem_sync/test_lease_bitacora.py
git commit -m "feat(salutem): lease en BD y bitácora de ejecuciones del sync

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Copia con detección de cambios

**Files:**
- Create: `backend/app/services/salutem_sync/copia.py`
- Test: `backend/tests/salutem_sync/test_copia.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_copia.py`:

```python
from datetime import date, timedelta

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, PersonaSalutem
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync import copia
from app.services.salutem_sync.tipos import Resultado
from tests.salutem_sync.conftest import AHORA

DIA = date(2025, 1, 22)
DESPUES = AHORA + timedelta(minutes=5)


def _cita(cita_id=9001, estado=3, fecha=DIA, **extra) -> CitaSalutem:
    return CitaSalutem.desde_api(
        {
            "personaId": 501,
            "citaId": cita_id,
            "citaFecha": fecha.isoformat(),
            "citaFechaCreacion": "2025-01-20 15:16",
            "estadoCitaId": estado,
            **extra,
        }
    )


def _atencion(cita_id=9001, anamnesis="inicial") -> AtencionSalutem:
    return AtencionSalutem.desde_api(
        {"personaId": 501, "citaId": cita_id, "citaFecha": DIA.isoformat(), "anamnesis": anamnesis}
    )


def test_cita_nueva_igual_y_cambiada(db_session):
    assert copia.guardar_cita(db_session, _cita(), AHORA) is Resultado.NUEVO
    assert copia.guardar_cita(db_session, _cita(), DESPUES) is Resultado.IGUAL
    assert copia.guardar_cita(db_session, _cita(estado=2), DESPUES) is Resultado.CAMBIADO

    fila = db_session.get(SalutemCita, 9001)
    assert fila.estado_id == 2
    assert fila.persona_id == 501
    assert fila.fecha_cita == DIA
    assert fila.fecha_creacion.strftime("%Y-%m-%d %H:%M") == "2025-01-20 15:16"
    assert fila.contenido["estadoCitaId"] == 2


def test_persona_guarda_el_rut_en_forma_canonica(db_session):
    copia.guardar_persona(
        db_session, PersonaSalutem.desde_api({"SALUTEM_ID": 501, "identificacion": "12.345.678-5"}), AHORA
    )
    copia.guardar_persona(
        db_session, PersonaSalutem.desde_api({"SALUTEM_ID": 502, "identificacion": "no-es-rut"}), AHORA
    )
    assert db_session.get(SalutemPersona, 501).rut == "123456785"
    assert db_session.get(SalutemPersona, 502).rut is None


def test_marca_desaparecidas_solo_las_no_vistas_y_la_reaparicion_limpia_la_marca(db_session):
    copia.guardar_cita(db_session, _cita(9001), AHORA)
    copia.guardar_cita(db_session, _cita(9002), AHORA)

    marcadas = copia.marcar_citas_desaparecidas(db_session, DIA, {9001}, DESPUES)

    assert marcadas == 1
    assert db_session.get(SalutemCita, 9001).desaparecida_en is None
    assert db_session.get(SalutemCita, 9002).desaparecida_en is not None
    assert copia.marcar_citas_desaparecidas(db_session, DIA, {9001}, DESPUES) == 0

    assert copia.guardar_cita(db_session, _cita(9002), DESPUES) is Resultado.CAMBIADO
    assert db_session.get(SalutemCita, 9002).desaparecida_en is None


def test_atencion_cambiada_queda_pendiente_de_vincular(db_session):
    copia.guardar_atencion(db_session, _atencion(), AHORA)
    fila = db_session.get(SalutemAtencion, 9001)
    fila.hash_vinculado = fila.hash_contenido

    assert copia.guardar_atencion(db_session, _atencion(anamnesis="editada"), DESPUES) is Resultado.CAMBIADO
    fila = db_session.get(SalutemAtencion, 9001)
    assert fila.hash_vinculado != fila.hash_contenido


def test_atencion_desaparecida_y_reaparecida_vuelve_a_quedar_pendiente(db_session):
    copia.guardar_atencion(db_session, _atencion(), AHORA)
    fila = db_session.get(SalutemAtencion, 9001)
    fila.hash_vinculado = fila.hash_contenido

    assert copia.marcar_atencion_desaparecida(db_session, 9001, DESPUES) is True
    assert copia.marcar_atencion_desaparecida(db_session, 9001, DESPUES) is False
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is None

    fila.hash_vinculado = fila.hash_contenido
    assert copia.guardar_atencion(db_session, _atencion(), DESPUES) is Resultado.CAMBIADO
    fila = db_session.get(SalutemAtencion, 9001)
    assert fila.desaparecida_en is None
    assert fila.hash_vinculado is None


def test_marcar_atencion_inexistente_no_hace_nada(db_session):
    assert copia.marcar_atencion_desaparecida(db_session, 123, AHORA) is False
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_copia.py -v`
Expected: FAIL con `ImportError: cannot import name 'copia'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/copia.py`:

```python
"""Guardado en la copia local de SALUTEM con detección de cambios por hash.

Cada función hace `flush` al terminar: SessionLocal usa autoflush=False y el
barrido consulta en el mismo día registros que acaba de agregar.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, PersonaSalutem
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync.hash import hash_contenido
from app.services.salutem_sync.tipos import Resultado
from app.util.rut import RutInvalidoError, normalizar_rut


def _rut_cepa(identificacion: str | None) -> str | None:
    if not identificacion:
        return None
    try:
        return normalizar_rut(identificacion)
    except RutInvalidoError:
        return None


def _fecha_creacion(crudo: dict[str, Any]) -> datetime | None:
    valor = crudo.get("citaFechaCreacion")
    if not isinstance(valor, str):
        return None
    try:
        return datetime.strptime(valor[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _guardar(
    db: Session,
    modelo: type,
    clave: int,
    contenido: dict[str, Any],
    campos: dict[str, Any],
    ahora: datetime,
) -> Resultado:
    nuevo_hash = hash_contenido(contenido)
    fila = db.get(modelo, clave)
    if fila is None:
        db.add(
            modelo(
                **campos,
                contenido=contenido,
                hash_contenido=nuevo_hash,
                visto_primera_vez=ahora,
                visto_ultima_vez=ahora,
                cambiado_en=ahora,
            )
        )
        db.flush()
        return Resultado.NUEVO

    fila.visto_ultima_vez = ahora
    reaparecio = getattr(fila, "desaparecida_en", None) is not None
    if fila.hash_contenido == nuevo_hash and not reaparecio:
        db.flush()
        return Resultado.IGUAL

    for nombre, valor in campos.items():
        setattr(fila, nombre, valor)
    fila.contenido = contenido
    fila.hash_contenido = nuevo_hash
    fila.cambiado_en = ahora
    if reaparecio:
        fila.desaparecida_en = None
        if hasattr(fila, "hash_vinculado"):
            # Con el mismo hash la vinculación no la vería: hay que forzarla.
            fila.hash_vinculado = None
    db.flush()
    return Resultado.CAMBIADO


def guardar_persona(db: Session, persona: PersonaSalutem, ahora: datetime) -> Resultado:
    return _guardar(
        db,
        SalutemPersona,
        persona.salutem_id,
        persona.crudo,
        {"salutem_id": persona.salutem_id, "rut": _rut_cepa(persona.identificacion)},
        ahora,
    )


def guardar_cita(db: Session, cita: CitaSalutem, ahora: datetime) -> Resultado:
    return _guardar(
        db,
        SalutemCita,
        cita.cita_id,
        cita.crudo,
        {
            "cita_id": cita.cita_id,
            "persona_id": cita.persona_id,
            "fecha_cita": cita.fecha,
            "fecha_creacion": _fecha_creacion(cita.crudo),
            "estado_id": cita.estado_id,
        },
        ahora,
    )


def guardar_atencion(db: Session, atencion: AtencionSalutem, ahora: datetime) -> Resultado:
    return _guardar(
        db,
        SalutemAtencion,
        atencion.cita.cita_id,
        atencion.contenido,
        {
            "cita_id": atencion.cita.cita_id,
            "persona_id": atencion.cita.persona_id,
            "fecha_cita": atencion.cita.fecha,
        },
        ahora,
    )


def marcar_citas_desaparecidas(
    db: Session, fecha: date, vistas: set[int], ahora: datetime
) -> int:
    """Marca las citas de `fecha` que no volvieron en un barrido completo de ese día."""
    filas = db.scalars(
        select(SalutemCita).where(
            SalutemCita.fecha_cita == fecha, SalutemCita.desaparecida_en.is_(None)
        )
    ).all()
    marcadas = 0
    for fila in filas:
        if fila.cita_id not in vistas:
            fila.desaparecida_en = ahora
            marcadas += 1
    db.flush()
    return marcadas


def marcar_atencion_desaparecida(db: Session, cita_id: int, ahora: datetime) -> bool:
    fila = db.get(SalutemAtencion, cita_id)
    if fila is None or fila.desaparecida_en is not None:
        return False
    fila.desaparecida_en = ahora
    fila.hash_vinculado = None
    db.flush()
    return True
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_copia.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/copia.py tests/salutem_sync/test_copia.py
git commit -m "feat(salutem): copia local con detección de cambios y marcas de desaparición

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Barrido de un día y refresco de atenciones

**Files:**
- Create: `backend/app/services/salutem_sync/barrido.py`
- Test: `backend/tests/salutem_sync/test_barrido.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_barrido.py`:

```python
from datetime import date, timedelta

import pytest

from app.integrations.salutem.errors import SalutemAuthError
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync.barrido import barrer_dia, refrescar_atenciones
from tests.salutem_sync.conftest import AHORA

DIA = date(2025, 1, 22)
DESPUES = AHORA + timedelta(minutes=5)
POR_CITA = TipoFechaCita.FECHA_CITA


@pytest.fixture
def con_datos(salutem):
    salutem.agregar_persona(501, "12345678-5")
    salutem.agregar_cita(9001, 501, DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9001, anamnesis="inicial")
    salutem.agregar_cita(9002, 501, DIA, EstadoCitaSalutem.AGENDADO)
    return salutem


def test_primer_barrido_trae_citas_persona_y_atencion(db_session, con_datos, ritmo):
    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)

    assert r.completo
    assert r.citas == 2
    assert r.contadores.nuevos == 4  # 2 citas + 1 persona + 1 atención
    assert len(con_datos.llamadas_a("listar_citas")) == 9
    assert db_session.get(SalutemPersona, 501) is not None
    assert db_session.get(SalutemAtencion, 9001).contenido["anamnesis"] == "inicial"
    assert db_session.get(SalutemAtencion, 9002) is None


def test_segundo_barrido_sin_cambios_no_trae_nada_mas(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    con_datos.llamadas.clear()

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert (r.contadores.nuevos, r.contadores.cambiados, r.contadores.desaparecidos) == (0, 0, 0)
    assert con_datos.llamadas_a("obtener_atencion") == []
    assert con_datos.llamadas_a("obtener_persona") == []


def test_cita_que_pasa_a_atendida_trae_su_atencion(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    con_datos.citas[9002]["estadoCitaId"] = int(EstadoCitaSalutem.ATENDIDO)
    con_datos.agregar_atencion(9002, anamnesis="segunda")

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert r.contadores.cambiados == 1
    assert r.contadores.nuevos == 1
    assert db_session.get(SalutemAtencion, 9002) is not None


def test_cita_que_ya_no_aparece_queda_marcada(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    del con_datos.citas[9002]

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert r.contadores.desaparecidos == 1
    assert db_session.get(SalutemCita, 9002).desaparecida_en is not None


def test_un_estado_rechazado_no_marca_desaparecidas(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    del con_datos.citas[9002]
    con_datos.dias_con_error.add((DIA, int(EstadoCitaSalutem.AGENDADO)))

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert not r.completo
    assert r.errores
    assert r.contadores.desaparecidos == 0
    assert db_session.get(SalutemCita, 9002).desaparecida_en is None


def test_por_fecha_de_creacion_no_marca_desaparecidas(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    del con_datos.citas[9002]

    r = barrer_dia(db_session, con_datos, ritmo, DIA, TipoFechaCita.FECHA_CREACION, DESPUES)

    assert r.contadores.desaparecidos == 0


def test_credencial_rechazada_se_propaga(db_session, con_datos, ritmo):
    con_datos.credencial_rechazada = True
    with pytest.raises(SalutemAuthError):
        barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)


def test_refrescar_detecta_ediciones_y_atenciones_borradas(db_session, con_datos, ritmo):
    con_datos.agregar_cita(9003, 501, DIA, EstadoCitaSalutem.ATENDIDO)
    con_datos.agregar_atencion(9003)
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    con_datos.atenciones[9001]["anamnesis"] = "editada"
    del con_datos.atenciones[9003]

    contadores = refrescar_atenciones(db_session, con_datos, ritmo, DIA, DIA, DESPUES)

    assert contadores.cambiados == 1
    assert contadores.desaparecidos == 1
    assert db_session.get(SalutemAtencion, 9001).contenido["anamnesis"] == "editada"
    assert db_session.get(SalutemAtencion, 9003).desaparecida_en is not None
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_barrido.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync.barrido'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/barrido.py`:

```python
"""Barrido de SALUTEM hacia la copia local: un día a la vez (solo lectura, D12)."""

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.errors import SalutemRequestError
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.salutem_sync import copia
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores, Resultado

# Hipótesis a validar en QA (Task 15): solo las citas atendidas tienen ficha clínica.
ESTADOS_CON_ATENCION = frozenset({int(EstadoCitaSalutem.ATENDIDO)})


@dataclass
class ResultadoDia:
    fecha: date
    tipo: TipoFechaCita
    citas: int = 0
    completo: bool = True
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)


def barrer_dia(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    fecha: date,
    tipo: TipoFechaCita,
    ahora: datetime,
) -> ResultadoDia:
    """Trae las citas de un día (9 estados), sus personas nuevas y sus atenciones.

    Confirma todo el día en una sola transacción: si el proceso muere a la
    mitad, el día se repite entero y el resultado es el mismo.
    """
    resultado = ResultadoDia(fecha=fecha, tipo=tipo)
    vistas: set[int] = set()

    for estado in EstadoCitaSalutem:
        try:
            citas = ritmo.llamar(cliente.listar_citas, fecha, estado, tipo)
        except SalutemRequestError as e:
            resultado.completo = False
            resultado.errores.append(f"{fecha.isoformat()} estado {int(estado)}: {e.codigo}")
            continue
        for cita in citas:
            vistas.add(cita.cita_id)
            guardado = copia.guardar_cita(db, cita, ahora)
            resultado.contadores.registrar(guardado)
            asegurar_persona(db, cliente, ritmo, cita.persona_id, ahora, resultado.contadores)
            if cita.estado_id in ESTADOS_CON_ATENCION and (
                guardado is not Resultado.IGUAL or db.get(SalutemAtencion, cita.cita_id) is None
            ):
                traer_atencion(
                    db, cliente, ritmo, cita.persona_id, cita.cita_id, ahora, resultado.contadores
                )

    resultado.citas = len(vistas)
    # Solo por fecha de cita y con los 9 estados respondidos se puede afirmar que
    # una cita ya no existe: por fecha de creación una cita puede cambiar de día.
    if tipo == TipoFechaCita.FECHA_CITA and resultado.completo:
        resultado.contadores.desaparecidos += copia.marcar_citas_desaparecidas(
            db, fecha, vistas, ahora
        )
    db.commit()
    return resultado


def asegurar_persona(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    persona_id: int,
    ahora: datetime,
    contadores: Contadores,
) -> None:
    if db.get(SalutemPersona, persona_id) is not None:
        return
    persona = ritmo.llamar(cliente.obtener_persona, persona_id)
    if persona is not None:
        contadores.registrar(copia.guardar_persona(db, persona, ahora))


def traer_atencion(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    persona_id: int,
    cita_id: int,
    ahora: datetime,
    contadores: Contadores,
) -> Resultado | None:
    """Trae una atención a la copia. None si SALUTEM ya no la tiene (queda marcada)."""
    atencion = ritmo.llamar(cliente.obtener_atencion, persona_id, cita_id)
    if atencion is None:
        if copia.marcar_atencion_desaparecida(db, cita_id, ahora):
            contadores.desaparecidos += 1
        return None
    guardado = copia.guardar_atencion(db, atencion, ahora)
    contadores.registrar(guardado)
    return guardado


def refrescar_atenciones(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    desde: date,
    hasta: date,
    ahora: datetime,
    lote: int = 50,
) -> Contadores:
    """Vuelve a traer las atenciones de un rango de fechas para detectar ediciones."""
    contadores = Contadores()
    claves = db.execute(
        select(SalutemAtencion.persona_id, SalutemAtencion.cita_id)
        .where(
            SalutemAtencion.fecha_cita >= desde,
            SalutemAtencion.fecha_cita <= hasta,
            SalutemAtencion.desaparecida_en.is_(None),
        )
        .order_by(SalutemAtencion.cita_id)
    ).all()
    for i, (persona_id, cita_id) in enumerate(claves, start=1):
        traer_atencion(db, cliente, ritmo, persona_id, cita_id, ahora, contadores)
        if i % lote == 0:
            db.commit()
    db.commit()
    return contadores
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_barrido.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/barrido.py tests/salutem_sync/test_barrido.py
git commit -m "feat(salutem): barrido diario de citas, personas y atenciones hacia la copia

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Carga inicial reanudable

**Files:**
- Create: `backend/app/services/salutem_sync/backfill.py`
- Test: `backend/tests/salutem_sync/test_backfill.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_backfill.py`:

```python
from datetime import date, timedelta

from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.models.salutem_sync import SalutemSyncDia
from app.services.salutem_sync.backfill import ejecutar_backfill
from tests.salutem_sync.conftest import AHORA

HOY = date(2026, 9, 16)
DIA = timedelta(days=1)


def _dias_barridos_por_cita(salutem) -> set[date]:
    return {ll[1] for ll in salutem.llamadas_a("listar_citas") if ll[3] == int(TipoFechaCita.FECHA_CITA)}


def test_recorre_hacia_atras_y_para_tras_n_dias_vacios(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - 2 * DIA, EstadoCitaSalutem.AGENDADO)
    salutem.agregar_cita(9002, 501, HOY - 5 * DIA, EstadoCitaSalutem.AGENDADO)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        dias_vacios_para_parar=3, dias_futuro=0, verificar=False,
    )

    assert r.primer_dia_con_datos == HOY - 5 * DIA
    assert r.dias_barridos == 9  # de HOY a HOY-8
    assert _dias_barridos_por_cita(salutem) == {HOY - i * DIA for i in range(9)}
    assert db_session.get(SalutemCita, 9002) is not None


def test_respeta_la_fecha_desde(db_session, salutem, ritmo):
    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - DIA, dias_futuro=0, verificar=False,
    )
    assert r.dias_barridos == 2


def test_se_reanuda_sin_repetir_dias_completos(db_session, salutem, ritmo):
    opciones = dict(hoy=HOY, ahora=AHORA, desde=HOY - 3 * DIA, dias_futuro=0, verificar=False)
    ejecutar_backfill(db_session, salutem, ritmo, **opciones)
    salutem.llamadas.clear()

    ejecutar_backfill(db_session, salutem, ritmo, **opciones)

    # Hoy nunca queda registrado (sigue cambiando); los días pasados sí.
    assert _dias_barridos_por_cita(salutem) == {HOY}
    assert db_session.get(SalutemSyncDia, (HOY, int(TipoFechaCita.FECHA_CITA))) is None
    assert db_session.get(SalutemSyncDia, (HOY - DIA, int(TipoFechaCita.FECHA_CITA))) is not None


def test_un_dia_con_error_no_queda_registrado(db_session, salutem, ritmo):
    salutem.dias_con_error.add((HOY - DIA, int(EstadoCitaSalutem.ATENDIDO)))

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - 2 * DIA, dias_futuro=0, verificar=False,
    )

    assert r.dias_con_error == 1
    assert r.errores
    assert db_session.get(SalutemSyncDia, (HOY - DIA, int(TipoFechaCita.FECHA_CITA))) is None
    assert db_session.get(SalutemSyncDia, (HOY - 2 * DIA, int(TipoFechaCita.FECHA_CITA))) is not None


def test_trae_las_citas_futuras(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9100, 501, HOY + 10 * DIA, EstadoCitaSalutem.AGENDADO)

    ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY, dias_futuro=15, verificar=False,
    )

    assert db_session.get(SalutemCita, 9100) is not None


def test_la_verificacion_recupera_atenciones_que_el_barrido_no_vio(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9001)
    # Atención antigua, fuera del rango barrido.
    salutem.agregar_cita(9200, 501, HOY - 400 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9200)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - 2 * DIA, dias_futuro=0, verificar=True,
    )

    assert r.atenciones_recuperadas == 1
    assert r.atenciones_anteriores == 1
    assert db_session.get(SalutemAtencion, 9200) is not None


def test_avisa_al_terminar_cada_dia(db_session, salutem, ritmo):
    avisos = []
    ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - DIA, dias_futuro=2, verificar=False,
        al_terminar_dia=lambda: avisos.append(1),
    )
    assert len(avisos) == 4  # 2 futuros + hoy + ayer
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_backfill.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync.backfill'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/backfill.py`:

```python
"""Carga inicial: todo SALUTEM desde el primer día con datos (solo lectura, D12).

1. Barre el futuro (agendas ya creadas).
2. Barre hacia atrás desde hoy, día por día, saltando los días ya registrados.
   Se detiene en `desde` o tras `dias_vacios_para_parar` días seguidos sin citas.
3. Verifica completitud persona por persona con el listado de atenciones.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.models import TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.models.salutem_sync import SalutemSyncDia
from app.services.salutem_sync.barrido import ResultadoDia, barrer_dia, traer_atencion
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores, Resultado

DIAS_FUTURO = 180
_UN_DIA = timedelta(days=1)


@dataclass
class ResultadoBackfill:
    dias_barridos: int = 0
    dias_con_error: int = 0
    primer_dia_con_datos: date | None = None
    atenciones_recuperadas: int = 0
    # Recuperadas con fecha anterior al primer día con citas: sugiere re-ejecutar con --desde.
    atenciones_anteriores: int = 0
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)

    def sumar_dia(self, dia: ResultadoDia) -> None:
        self.dias_barridos += 1
        self.contadores.sumar(dia.contadores)
        if not dia.completo:
            self.dias_con_error += 1
            self.errores.extend(dia.errores)


def ejecutar_backfill(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    *,
    hoy: date,
    ahora: datetime,
    desde: date | None = None,
    dias_vacios_para_parar: int = 365,
    dias_futuro: int = DIAS_FUTURO,
    verificar: bool = True,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoBackfill:
    resultado = ResultadoBackfill()
    tipo = TipoFechaCita.FECHA_CITA

    for i in range(1, dias_futuro + 1):
        resultado.sumar_dia(barrer_dia(db, cliente, ritmo, hoy + i * _UN_DIA, tipo, ahora))
        al_terminar_dia()

    dia = hoy
    vacios = 0
    while True:
        if desde is not None and dia < desde:
            break
        if desde is None and vacios >= dias_vacios_para_parar:
            break
        registrado = db.get(SalutemSyncDia, (dia, int(tipo))) if dia < hoy else None
        if registrado is not None:
            citas = registrado.citas
        else:
            barrido = barrer_dia(db, cliente, ritmo, dia, tipo, ahora)
            resultado.sumar_dia(barrido)
            citas = barrido.citas
            # Hoy no se registra: sigue cambiando. Un día con errores tampoco: se reintenta.
            if barrido.completo and dia < hoy:
                db.add(SalutemSyncDia(fecha=dia, tipo=int(tipo), citas=citas, completado_en=ahora))
                db.commit()
            al_terminar_dia()
        if citas > 0:
            vacios = 0
            resultado.primer_dia_con_datos = dia
        else:
            vacios += 1
        dia -= _UN_DIA

    if verificar:
        _verificar_completitud(db, cliente, ritmo, resultado, ahora, al_terminar_dia)
    return resultado


def _verificar_completitud(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    resultado: ResultadoBackfill,
    ahora: datetime,
    al_terminar_dia: Callable[[], None],
    lote: int = 50,
) -> None:
    """Pide la historia de cada persona y trae las atenciones que la copia no tiene."""
    personas = db.scalars(select(SalutemPersona.salutem_id).order_by(SalutemPersona.salutem_id)).all()
    limite = resultado.primer_dia_con_datos
    for n, persona_id in enumerate(personas, start=1):
        for cita in ritmo.llamar(cliente.listar_atenciones, persona_id):
            if db.get(SalutemAtencion, cita.cita_id) is not None:
                continue
            guardado = traer_atencion(
                db, cliente, ritmo, persona_id, cita.cita_id, ahora, resultado.contadores
            )
            if guardado is Resultado.NUEVO:
                resultado.atenciones_recuperadas += 1
                if limite is not None and cita.fecha is not None and cita.fecha < limite:
                    resultado.atenciones_anteriores += 1
        if n % lote == 0:
            db.commit()
            al_terminar_dia()
    db.commit()
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_backfill.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/backfill.py tests/salutem_sync/test_backfill.py
git commit -m "feat(salutem): carga inicial reanudable con parada por días vacíos y verificación

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Ventanas incrementales

**Files:**
- Create: `backend/app/services/salutem_sync/incremental.py`
- Test: `backend/tests/salutem_sync/test_incremental.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_incremental.py`:

```python
from datetime import date, datetime, timedelta, timezone

from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.services.salutem_sync.barrido import barrer_dia
from app.services.salutem_sync.incremental import ventana_caliente, ventana_fria, ventana_tibia
from tests.salutem_sync.conftest import AHORA

HOY = date(2026, 9, 16)
DIA = timedelta(days=1)
CITA = int(TipoFechaCita.FECHA_CITA)
CREACION = int(TipoFechaCita.FECHA_CREACION)


def _pares(salutem) -> set[tuple[date, int]]:
    return {(ll[1], ll[3]) for ll in salutem.llamadas_a("listar_citas")}


def test_caliente_al_mediodia_barre_creacion_de_hoy_y_citas_de_hoy_y_manana(db_session, salutem, ritmo):
    ventana_caliente(db_session, salutem, ritmo, AHORA)
    assert _pares(salutem) == {(HOY, CREACION), (HOY, CITA), (HOY + DIA, CITA)}


def test_caliente_pasada_la_medianoche_incluye_la_creacion_de_ayer(db_session, salutem, ritmo):
    medianoche_y_media = datetime(2026, 9, 16, 3, 30, tzinfo=timezone.utc)  # 00:30 en Santiago
    ventana_caliente(db_session, salutem, ritmo, medianoche_y_media)
    assert (HOY - DIA, CREACION) in _pares(salutem)


def test_caliente_detecta_una_cita_creada_hoy_para_otro_dia(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY + 3 * DIA, EstadoCitaSalutem.AGENDADO, creada="2026-09-16 11:40")

    r = ventana_caliente(db_session, salutem, ritmo, AHORA)

    assert r.contadores.nuevos >= 1
    assert db_session.get(SalutemCita, 9001) is not None


def test_tibia_refresca_una_atencion_editada_hace_tres_dias(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - 3 * DIA)
    salutem.agregar_atencion(9001, anamnesis="inicial")
    barrer_dia(db_session, salutem, ritmo, HOY - 3 * DIA, TipoFechaCita.FECHA_CITA, AHORA)
    salutem.atenciones[9001]["anamnesis"] = "editada"

    r = ventana_tibia(db_session, salutem, ritmo, AHORA)

    assert r.contadores.cambiados == 1
    assert db_session.get(SalutemAtencion, 9001).contenido["anamnesis"] == "editada"
    assert {d for d, t in _pares(salutem) if t == CITA} >= {HOY - 7 * DIA, HOY + 30 * DIA}


def test_fria_cubre_noventa_dias_atras_y_ciento_ochenta_adelante(db_session, salutem, ritmo):
    avisos = []
    ventana_fria(db_session, salutem, ritmo, AHORA, al_terminar_dia=lambda: avisos.append(1))

    dias = {d for d, t in _pares(salutem) if t == CITA}
    assert min(dias) == HOY - 90 * DIA
    assert max(dias) == HOY + 180 * DIA
    assert len(dias) == 271
    assert len(avisos) == 271


def test_un_dia_con_error_queda_en_los_errores_de_la_ventana(db_session, salutem, ritmo):
    salutem.dias_con_error.add((HOY, int(EstadoCitaSalutem.ATENDIDO)))
    r = ventana_caliente(db_session, salutem, ritmo, AHORA)
    assert r.errores
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_incremental.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync.incremental'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/incremental.py`:

```python
"""Ventanas del sync incremental (solo lectura, D12).

- caliente (cada 5 min): citas creadas hoy + citas de hoy y mañana.
- tibia (cada hora): citas de -7..+30 días y re-lectura de atenciones de la última semana.
- fría (cada noche): citas de -90..+180 días y re-lectura de atenciones del último mes.

"Hoy" es el día en Santiago: SALUTEM trabaja en hora local.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.integrations.salutem.models import TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.services.salutem_sync.barrido import barrer_dia, refrescar_atenciones
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores

ZONA = ZoneInfo("America/Santiago")
_UN_DIA = timedelta(days=1)

TIBIA_DIAS_ATRAS, TIBIA_DIAS_ADELANTE, TIBIA_ATENCIONES_DIAS = 7, 30, 7
FRIA_DIAS_ATRAS, FRIA_DIAS_ADELANTE, FRIA_ATENCIONES_DIAS = 90, 180, 30


@dataclass
class ResultadoVentana:
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)


def hoy_en_santiago(ahora: datetime) -> date:
    return ahora.astimezone(ZONA).date()


def _barrer(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    dias: list[date],
    tipo: TipoFechaCita,
    ahora: datetime,
    resultado: ResultadoVentana,
    al_terminar_dia: Callable[[], None],
) -> None:
    for dia in dias:
        barrido = barrer_dia(db, cliente, ritmo, dia, tipo, ahora)
        resultado.contadores.sumar(barrido.contadores)
        resultado.errores.extend(barrido.errores)
        al_terminar_dia()


def _rango(hoy: date, atras: int, adelante: int) -> list[date]:
    return [hoy + i * _UN_DIA for i in range(-atras, adelante + 1)]


def ventana_caliente(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoVentana:
    resultado = ResultadoVentana()
    local = ahora.astimezone(ZONA)
    hoy = local.date()
    # Pasada la medianoche, lo creado en los últimos minutos de ayer aún no se barrió.
    creacion = [hoy - _UN_DIA, hoy] if local.hour < 1 else [hoy]
    _barrer(db, cliente, ritmo, creacion, TipoFechaCita.FECHA_CREACION, ahora, resultado, al_terminar_dia)
    _barrer(db, cliente, ritmo, [hoy, hoy + _UN_DIA], TipoFechaCita.FECHA_CITA, ahora, resultado, al_terminar_dia)
    return resultado


def ventana_tibia(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoVentana:
    resultado = ResultadoVentana()
    hoy = hoy_en_santiago(ahora)
    _barrer(
        db, cliente, ritmo, _rango(hoy, TIBIA_DIAS_ATRAS, TIBIA_DIAS_ADELANTE),
        TipoFechaCita.FECHA_CITA, ahora, resultado, al_terminar_dia,
    )
    resultado.contadores.sumar(
        refrescar_atenciones(db, cliente, ritmo, hoy - TIBIA_ATENCIONES_DIAS * _UN_DIA, hoy, ahora)
    )
    return resultado


def ventana_fria(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoVentana:
    resultado = ResultadoVentana()
    hoy = hoy_en_santiago(ahora)
    _barrer(
        db, cliente, ritmo, _rango(hoy, FRIA_DIAS_ATRAS, FRIA_DIAS_ADELANTE),
        TipoFechaCita.FECHA_CITA, ahora, resultado, al_terminar_dia,
    )
    resultado.contadores.sumar(
        refrescar_atenciones(db, cliente, ritmo, hoy - FRIA_ATENCIONES_DIAS * _UN_DIA, hoy, ahora)
    )
    return resultado
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_incremental.py -v`
Expected: PASS (6 tests). Si `ZoneInfoNotFoundError`: agregar `tzdata` con `uv add tzdata` (en macOS/Debian normalmente no hace falta).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/incremental.py tests/salutem_sync/test_incremental.py
git commit -m "feat(salutem): ventanas caliente, tibia y fría del sync incremental

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Vinculación con `ficha_clinica`

**Files:**
- Create: `backend/app/services/salutem_sync/vinculacion.py`
- Test: `backend/tests/salutem_sync/test_vinculacion.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_vinculacion.py`:

```python
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, PersonaSalutem
from app.models.audit_log import AuditLog
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion
from app.services.salutem_sync import copia
from app.services.salutem_sync.vinculacion import ACTOR, vincular
from tests.salutem_sync.conftest import AHORA

RUT_SALUTEM = "12.345.678-5"
RUT_CEPA = "123456785"


def _copiar(db, *, cita_id=9001, persona_id=501, fecha=date(2026, 2, 10), **contenido):
    copia.guardar_persona(
        db, PersonaSalutem.desde_api({"SALUTEM_ID": persona_id, "identificacion": RUT_SALUTEM}), AHORA
    )
    crudo = {"personaId": persona_id, "citaId": cita_id, "citaFecha": fecha.isoformat(), **contenido}
    copia.guardar_atencion(db, AtencionSalutem.desde_api(crudo), AHORA)


def _paciente(db) -> Paciente:
    p = Paciente(rut=RUT_CEPA, nombre="Paciente Sync", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente, folio="F-SYNC-1", desde=date(2026, 1, 1), alta=None) -> Ingreso:
    ingreso = Ingreso(
        paciente_id=paciente.id, folio=folio, folio_manual=True, fecha_ingreso=desde,
        fecha_alta=alta, tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="test sync", estado="activo",
    )
    db.add(ingreso)
    db.flush()
    return ingreso


def _fichas(db) -> list[FichaClinica]:
    return list(db.scalars(select(FichaClinica).where(FichaClinica.salutem_cita_id.is_not(None))).all())


def test_crea_la_ficha_para_una_atencion_dentro_de_la_ventana(db_session):
    ingreso = _ingreso(db_session, _paciente(db_session))
    _copiar(db_session, anamnesis="hola")

    r = vincular(db_session, AHORA)

    fichas = _fichas(db_session)
    assert r.fichas_nuevas == 1
    assert len(fichas) == 1
    assert (fichas[0].ingreso_id, fichas[0].folio, fichas[0].origen) == (ingreso.id, "F-SYNC-1", "SALUTEM")
    assert fichas[0].salutem_cita_id == 9001
    assert fichas[0].contenido["anamnesis"] == "hola"
    atencion = db_session.get(SalutemAtencion, 9001)
    assert atencion.hash_vinculado == atencion.hash_contenido
    assert db_session.scalars(select(AuditLog).where(AuditLog.actor == ACTOR)).first() is not None


def test_sin_paciente_cepa_queda_pendiente_hasta_que_exista(db_session):
    _copiar(db_session)

    assert vincular(db_session, AHORA).fichas_nuevas == 0
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is None

    _ingreso(db_session, _paciente(db_session))
    assert vincular(db_session, AHORA).fichas_nuevas == 1


def test_fuera_de_la_ventana_del_ingreso_no_crea_ficha(db_session):
    _ingreso(db_session, _paciente(db_session), desde=date(2026, 3, 1))
    _copiar(db_session, fecha=date(2026, 2, 10))

    r = vincular(db_session, AHORA)

    assert r.fichas_nuevas == 0
    assert r.atenciones_revisadas == 1


def test_vincular_dos_veces_no_duplica(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session)

    vincular(db_session, AHORA, todo=True)
    r = vincular(db_session, AHORA, todo=True)

    assert (r.fichas_nuevas, r.fichas_actualizadas) == (0, 0)
    assert len(_fichas(db_session)) == 1


def test_contenido_editado_en_salutem_actualiza_la_ficha(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session, anamnesis="inicial")
    vincular(db_session, AHORA)

    _copiar(db_session, anamnesis="editada")
    r = vincular(db_session, AHORA)

    assert r.fichas_actualizadas == 1
    assert _fichas(db_session)[0].contenido["anamnesis"] == "editada"


def test_atencion_desaparecida_marca_la_ficha_sin_borrarla(db_session):
    _ingreso(db_session, _paciente(db_session))
    _copiar(db_session)
    vincular(db_session, AHORA)

    copia.marcar_atencion_desaparecida(db_session, 9001, AHORA)
    r = vincular(db_session, AHORA)

    assert r.fichas_eliminadas == 1
    assert _fichas(db_session)[0].eliminada_en_origen is not None


def test_un_ingreso_nuevo_recibe_atenciones_ya_vinculadas(db_session):
    paciente = _paciente(db_session)
    _copiar(db_session)
    vincular(db_session, AHORA)  # el paciente existe pero no tiene ingreso: nada que crear
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is not None

    _ingreso(db_session, paciente)
    hace_un_rato = datetime.now(timezone.utc) - timedelta(minutes=5)
    r = vincular(db_session, AHORA, ingresos_desde=hace_un_rato)

    assert r.fichas_nuevas == 1
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_vinculacion.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync.vinculacion'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/vinculacion.py`:

```python
"""Paso 2 del sync: de la copia de SALUTEM a ficha_clinica. No habla con SALUTEM.

Una atención se vincula a los ingresos del paciente CEPA con el mismo RUT cuya
ventana contiene la fecha de la cita (misma regla que el pull manual). Las
atenciones de personas sin paciente CEPA quedan pendientes y se vinculan solas
cuando el paciente aparece.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.ficha_clinica import _en_ventana_del_ingreso

ACTOR = "sistema:salutem-sync"


@dataclass
class ResultadoVinculacion:
    atenciones_revisadas: int = 0
    fichas_nuevas: int = 0
    fichas_actualizadas: int = 0
    fichas_eliminadas: int = 0


def vincular(
    db: Session,
    ahora: datetime,
    *,
    todo: bool = False,
    ingresos_desde: datetime | None = None,
    lote: int = 200,
) -> ResultadoVinculacion:
    """Aplica a ficha_clinica las atenciones pendientes.

    `todo=True` revisa todas las atenciones con paciente CEPA (modo fría y backfill).
    `ingresos_desde` agrega las atenciones de pacientes con ingresos creados o
    editados desde ese momento, que pueden haber ganado atenciones antiguas.
    """
    resultado = ResultadoVinculacion()
    consulta = (
        select(SalutemAtencion.cita_id, Paciente.id)
        .join(SalutemPersona, SalutemPersona.salutem_id == SalutemAtencion.persona_id)
        .join(Paciente, Paciente.rut == SalutemPersona.rut)
        .order_by(SalutemAtencion.cita_id)
    )
    if not todo:
        condicion = or_(
            SalutemAtencion.hash_vinculado.is_(None),
            SalutemAtencion.hash_vinculado != SalutemAtencion.hash_contenido,
        )
        if ingresos_desde is not None:
            condicion = or_(
                condicion,
                Paciente.id.in_(
                    select(Ingreso.paciente_id).where(Ingreso.updated_at >= ingresos_desde)
                ),
            )
        consulta = consulta.where(condicion)

    for n, (cita_id, paciente_id) in enumerate(db.execute(consulta).all(), start=1):
        atencion = db.get(SalutemAtencion, cita_id)
        # Consulta explícita y no `paciente.ingresos`: con expire_on_commit=False la
        # colección cargada en una vinculación anterior no vería un ingreso nuevo.
        ingresos = db.scalars(select(Ingreso).where(Ingreso.paciente_id == paciente_id)).all()
        for ingreso in ingresos:
            if _en_ventana_del_ingreso(atencion.fecha_cita, ingreso):
                _aplicar(db, atencion, ingreso, ahora, resultado)
        atencion.hash_vinculado = atencion.hash_contenido
        resultado.atenciones_revisadas += 1
        if n % lote == 0:
            db.commit()
    db.commit()
    return resultado


def _aplicar(
    db: Session,
    atencion: SalutemAtencion,
    ingreso: Ingreso,
    ahora: datetime,
    resultado: ResultadoVinculacion,
) -> None:
    ficha = db.scalars(
        select(FichaClinica)
        .where(
            FichaClinica.ingreso_id == ingreso.id,
            FichaClinica.salutem_cita_id == atencion.cita_id,
        )
        .order_by(FichaClinica.id)
    ).first()

    if atencion.desaparecida_en is not None:
        if ficha is not None and ficha.eliminada_en_origen is None:
            ficha.eliminada_en_origen = ahora
            db.flush()
            _auditar(db, "UPDATE", ficha)
            resultado.fichas_eliminadas += 1
        return

    if ficha is None:
        ficha = FichaClinica(
            ingreso_id=ingreso.id,
            folio=ingreso.folio,
            origen="SALUTEM",
            contenido=atencion.contenido,
            salutem_cita_id=atencion.cita_id,
        )
        db.add(ficha)
        db.flush()
        _auditar(db, "CREATE", ficha)
        resultado.fichas_nuevas += 1
        return

    if ficha.contenido != atencion.contenido or ficha.eliminada_en_origen is not None:
        ficha.contenido = atencion.contenido
        ficha.eliminada_en_origen = None
        db.flush()
        _auditar(db, "UPDATE", ficha)
        resultado.fichas_actualizadas += 1


def _auditar(db: Session, accion: str, ficha: FichaClinica) -> None:
    record_audit(db, actor=ACTOR, action=accion, entity="ficha_clinica", entity_id=str(ficha.id))
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_vinculacion.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/vinculacion.py tests/salutem_sync/test_vinculacion.py
git commit -m "feat(salutem): vinculación de la copia con ficha_clinica por RUT y ventana del ingreso

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Pull manual y licencias sugeridas conviven con el sync

**Files:**
- Modify: `backend/app/services/ficha_clinica.py` (`crear_ficha`, `_cita_ids_ya_persistidos`, `_pull_desde_salutem`)
- Modify: `backend/app/schemas/ficha_clinica.py` (`FichaClinicaRead`)
- Modify: `backend/app/services/licencias_sugeridas.py` (consulta de fichas)
- Test: `backend/tests/salutem_sync/test_convivencia.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_convivencia.py`:

```python
"""El pull manual y las licencias sugeridas conviven con las fichas que crea el sync."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, PersonaSalutem
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente

EXTENSION = "Extiendo licencia médica tipo 6 total desde el 09/05/2024 por 21 días"


@pytest.fixture
def ingreso(db_session) -> Ingreso:
    p = Paciente(rut="8881112220", nombre="Convivencia Sync", sexo="M", edad=30, region="Maule")
    db_session.add(p)
    db_session.flush()
    ing = Ingreso(
        paciente_id=p.id, folio="F-2026-CONV", folio_manual=True, fecha_ingreso=date(2024, 1, 1),
        tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="convivencia", estado="activo",
    )
    db_session.add(ing)
    db_session.flush()
    return ing


class _SalutemUnaAtencion:
    def resolver_persona(self, rut):  # noqa: ARG002
        return PersonaSalutem(salutem_id=42, identificacion=rut)

    def listar_atenciones(self, salutem_id):  # noqa: ARG002
        return [CitaSalutem(persona_id=42, cita_id=777, fecha=date(2026, 1, 15))]

    def obtener_atencion(self, salutem_id, cita_id):  # noqa: ARG002
        return AtencionSalutem(
            cita=CitaSalutem(persona_id=42, cita_id=777, fecha=date(2026, 1, 15)),
            contenido={"citaId": 777},
        )


def test_el_pull_manual_guarda_salutem_cita_id(monkeypatch, as_admin, db_session, ingreso):
    monkeypatch.setattr("app.services.ficha_clinica.get_salutem_client", _SalutemUnaAtencion)

    r = as_admin.post("/api/v1/fichas-clinicas/pull-salutem", json={"folio": ingreso.folio})

    assert r.status_code == 200, r.text
    assert r.json()[0]["salutem_cita_id"] == 777


def test_el_pull_manual_no_duplica_una_ficha_creada_por_el_sync(monkeypatch, as_admin, db_session, ingreso):
    db_session.add(
        FichaClinica(
            ingreso_id=ingreso.id, folio=ingreso.folio, origen="SALUTEM",
            contenido={"sin": "citaId"}, salutem_cita_id=777,
        )
    )
    db_session.flush()
    monkeypatch.setattr("app.services.ficha_clinica.get_salutem_client", _SalutemUnaAtencion)

    r = as_admin.post("/api/v1/fichas-clinicas/pull-salutem", json={"folio": ingreso.folio})

    assert r.status_code == 200, r.text
    assert r.json() == []
    total = db_session.scalars(select(FichaClinica).where(FichaClinica.ingreso_id == ingreso.id)).all()
    assert len(total) == 1


def test_licencias_sugeridas_ignoran_fichas_eliminadas_en_salutem(as_admin, db_session, ingreso):
    db_session.add(
        FichaClinica(
            ingreso_id=ingreso.id, folio=ingreso.folio, origen="SALUTEM", salutem_cita_id=900,
            eliminada_en_origen=datetime.now(timezone.utc),
            contenido={
                "citaId": 900,
                "citaFecha": "2024-05-06",
                "indicaciones": [{"tipo": 1, "nombre": "Indicaciones", "registro": EXTENSION}],
            },
        )
    )
    db_session.flush()

    r = as_admin.get(f"/api/v1/fichas-clinicas/{ingreso.folio}/licencias-sugeridas")

    assert r.status_code == 200, r.text
    assert r.json() == []
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_convivencia.py -v`
Expected: FAIL: `KeyError: 'salutem_cita_id'` en el primero, 1 ficha nueva devuelta en el segundo, 1 sugerencia en el tercero.

- [ ] **Step 3: Implementar**

En `backend/app/schemas/ficha_clinica.py`, dentro de `FichaClinicaRead`, después de `created_at: datetime`:

```python
    salutem_cita_id: int | None = None
    eliminada_en_origen: datetime | None = None
```

En `backend/app/services/ficha_clinica.py`, reemplazar `crear_ficha` por:

```python
def crear_ficha(
    db: Session, data: FichaClinicaCreate, *, salutem_cita_id: int | None = None
) -> FichaClinica:
    """Push: persiste datos clínicos recibidos en el dominio CEPA (D12)."""
    ingreso = _obtener_ingreso_por_folio(db, data.folio)
    ficha = FichaClinica(
        ingreso_id=ingreso.id,
        folio=data.folio,
        origen=data.origen,
        contenido=data.contenido,
        salutem_cita_id=salutem_cita_id,
    )
    db.add(ficha)
    db.flush()
    return ficha
```

Reemplazar `_cita_ids_ya_persistidos` por:

```python
def _cita_ids_ya_persistidos(db: Session, folio: str) -> set[int]:
    """`salutem_cita_id` de las fichas ya guardadas para este folio.

    Hace idempotente el pull y evita duplicar las fichas que crea el sync. La
    migración 1250 rellenó la columna en las fichas anteriores a ella.
    """
    return set(
        db.scalars(
            select(FichaClinica.salutem_cita_id).where(
                FichaClinica.folio == folio,
                FichaClinica.salutem_cita_id.is_not(None),
            )
        ).all()
    )
```

En `_pull_desde_salutem`, reemplazar la llamada a `crear_ficha(...)` dentro del bucle por:

```python
        nuevas.append(
            crear_ficha(
                db,
                FichaClinicaCreate(
                    folio=folio, origen="SALUTEM", contenido=atencion.contenido
                ),
                salutem_cita_id=cita.cita_id,
            )
        )
```

En `backend/app/services/licencias_sugeridas.py`, reemplazar el `where` de la consulta de fichas:

```python
        .where(
            FichaClinica.folio == folio,
            FichaClinica.origen == "SALUTEM",
            # Una atención borrada en SALUTEM no debe seguir sugiriendo licencias.
            FichaClinica.eliminada_en_origen.is_(None),
        )
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_convivencia.py tests/test_fichas_clinicas_api.py tests/test_salutem_no_escribe.py tests/test_licencias_sugeridas_api.py -v`
Expected: PASS (incluidos los tests previos del pull y de licencias sugeridas).

- [ ] **Step 5: Commit**

```bash
git add app/services/ficha_clinica.py app/schemas/ficha_clinica.py app/services/licencias_sugeridas.py tests/salutem_sync/test_convivencia.py
git commit -m "feat(salutem): el pull manual deduplica por salutem_cita_id y las licencias ignoran fichas eliminadas

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: Orquestador de modos

**Files:**
- Create: `backend/app/services/salutem_sync/orquestador.py`
- Test: `backend/tests/salutem_sync/test_orquestador.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_orquestador.py`:

```python
from datetime import date, timedelta

from sqlalchemy import select

from app.integrations.salutem.client import SalutemStubClient
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_sync import SalutemSyncEjecucion, SalutemSyncLease
from app.services.salutem_sync.lease import tomar_lease
from app.services.salutem_sync.orquestador import Opciones, correr
from tests.salutem_sync.conftest import AHORA

HOY = date(2026, 9, 16)


def _ejecuciones(db, modo):
    return db.scalars(
        select(SalutemSyncEjecucion).where(SalutemSyncEjecucion.modo == modo).order_by(SalutemSyncEjecucion.id)
    ).all()


def _correr(db, salutem, ritmo, modo="caliente", **kw):
    return correr(modo, db, salutem, ritmo, ahora=lambda: AHORA, habilitado=kw.pop("habilitado", True), dueno="test", **kw)


def test_apagado_no_hace_nada(db_session, salutem, ritmo):
    assert _correr(db_session, salutem, ritmo, habilitado=False) == 0
    assert salutem.llamadas == []
    assert _ejecuciones(db_session, "caliente") == []


def test_sin_credenciales_termina_con_error(db_session, ritmo):
    assert correr("caliente", db_session, SalutemStubClient(), ritmo, ahora=lambda: AHORA, habilitado=True) == 2


def test_con_el_lease_ocupado_queda_omitida(db_session, salutem, ritmo):
    assert tomar_lease(db_session, "otro-proceso", AHORA)

    assert _correr(db_session, salutem, ritmo) == 0

    assert [e.estado for e in _ejecuciones(db_session, "caliente")] == ["omitida"]
    assert salutem.llamadas == []


def test_caliente_exitosa_registra_bitacora_y_suelta_el_lease(db_session, salutem, ritmo):
    assert _correr(db_session, salutem, ritmo) == 0

    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "ok"
    assert ejecucion.llamadas == 27  # 3 días × 9 estados
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None


def test_credencial_rechazada_deja_error_y_suelta_el_lease(db_session, salutem, ritmo):
    salutem.credencial_rechazada = True

    assert _correr(db_session, salutem, ritmo) == 1

    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "error"
    assert "SalutemAuthError" in ejecucion.error
    assert db_session.get(SalutemSyncLease, "salutem").dueno is None


def test_dias_con_error_quedan_como_con_errores(db_session, salutem, ritmo):
    salutem.dias_con_error.add((HOY, int(EstadoCitaSalutem.ATENDIDO)))
    assert _correr(db_session, salutem, ritmo) == 0
    (ejecucion,) = _ejecuciones(db_session, "caliente")
    assert ejecucion.estado == "con_errores"
    assert "ERROR_INTERVALO_SUPERADO" in ejecucion.error


def test_al_terminar_vincula_con_el_dominio_cepa(db_session, salutem, ritmo):
    p = Paciente(rut="123456785", nombre="Orquestador", sexo="F", edad=33, region="Maule")
    db_session.add(p)
    db_session.flush()
    db_session.add(
        Ingreso(
            paciente_id=p.id, folio="F-ORQ-1", folio_manual=True, fecha_ingreso=HOY - timedelta(days=30),
            tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
            diagnostico="orquestador", estado="activo",
        )
    )
    db_session.flush()
    salutem.agregar_persona(501, "12345678-5")
    salutem.agregar_cita(9001, 501, HOY)
    salutem.agregar_atencion(9001, anamnesis="de hoy")

    assert _correr(db_session, salutem, ritmo) == 0

    ficha = db_session.scalars(select(FichaClinica).where(FichaClinica.folio == "F-ORQ-1")).one()
    assert ficha.salutem_cita_id == 9001


def test_backfill_usa_las_opciones(db_session, salutem, ritmo):
    opciones = Opciones(desde=HOY - timedelta(days=1), verificar=False, dias_futuro=0)
    assert _correr(db_session, salutem, ritmo, modo="backfill", opciones=opciones) == 0
    assert _ejecuciones(db_session, "backfill")[0].llamadas == 18


def test_vincular_no_llama_a_salutem(db_session, salutem, ritmo):
    assert _correr(db_session, salutem, ritmo, modo="vincular", opciones=Opciones(vincular_todo=True)) == 0
    assert salutem.llamadas == []
    assert _ejecuciones(db_session, "vincular")[0].estado == "ok"
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_orquestador.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.salutem_sync.orquestador'`.

- [ ] **Step 3: Implementar**

`backend/app/services/salutem_sync/orquestador.py`:

```python
"""Ejecuta un modo del sync: bandera, credenciales, lease, bitácora y errores.

Códigos de salida (los usa el cron):
    0 = terminó (ok, con errores de días puntuales, apagado u omitido por lease)
    1 = error (la ejecución quedó registrada con estado `error`)
    2 = SALUTEM sin credenciales configuradas
"""

import logging
import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.salutem.client import SalutemStubClient
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync.backfill import DIAS_FUTURO, ejecutar_backfill
from app.services.salutem_sync.bitacora import abrir_ejecucion, cerrar_ejecucion, registrar_omitida
from app.services.salutem_sync.incremental import (
    hoy_en_santiago,
    ventana_caliente,
    ventana_fria,
    ventana_tibia,
)
from app.services.salutem_sync.lease import soltar_lease, tomar_lease
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import MODOS, Contadores
from app.services.salutem_sync.vinculacion import vincular

log = logging.getLogger("salutem_sync")

_VINCULAN_TODO = ("backfill", "fria")


class LeasePerdidoError(RuntimeError):
    """Otro proceso tomó el lease (este tardó más que su vigencia sin renovarlo)."""


@dataclass
class Opciones:
    desde: date | None = None
    verificar: bool = True
    dias_futuro: int = DIAS_FUTURO
    dias_vacios_para_parar: int = 365
    vincular_todo: bool = False


def correr(
    modo: str,
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    *,
    ahora: Callable[[], datetime],
    habilitado: bool,
    opciones: Opciones | None = None,
    dueno: str | None = None,
) -> int:
    if modo not in MODOS:
        raise ValueError(f"Modo desconocido: {modo!r}")
    opciones = opciones or Opciones()
    if not habilitado:
        log.info("Sync SALUTEM deshabilitado (SALUTEM_SYNC_HABILITADO=false); modo %s no se ejecuta", modo)
        return 0
    if modo != "vincular" and isinstance(cliente, SalutemStubClient):
        log.error("SALUTEM sin credenciales (SALUTEM_EMPRESA / SALUTEM_API_KEY): no se sincroniza")
        return 2

    dueno = dueno or f"{socket.gethostname()}:{os.getpid()}:{modo}"
    inicio = ahora()
    if not tomar_lease(db, dueno, inicio):
        log.info("Modo %s omitido: otro proceso tiene el lease", modo)
        registrar_omitida(db, modo, inicio)
        return 0

    ingresos_desde = _ultimo_inicio_exitoso(db)
    ejecucion = abrir_ejecucion(db, modo, inicio)

    def renovar() -> None:
        if not tomar_lease(db, dueno, ahora()):
            raise LeasePerdidoError(f"El lease dejó de pertenecer a {dueno}")

    try:
        contadores, errores = _ejecutar_modo(modo, db, cliente, ritmo, inicio, opciones, renovar)
        vinculacion = vincular(
            db,
            ahora(),
            todo=modo in _VINCULAN_TODO or (modo == "vincular" and opciones.vincular_todo),
            ingresos_desde=ingresos_desde,
        )
        log.info("Modo %s terminado: %s, vinculación %s", modo, contadores, vinculacion)
        cerrar_ejecucion(
            db,
            ejecucion,
            estado="con_errores" if errores else "ok",
            ahora=ahora(),
            llamadas=ritmo.llamadas,
            contadores=contadores,
            error="; ".join(errores) if errores else None,
        )
        return 0
    except Exception as e:  # noqa: BLE001 — cualquier falla debe quedar en la bitácora
        db.rollback()
        log.exception("Modo %s falló", modo)
        cerrar_ejecucion(
            db, ejecucion, estado="error", ahora=ahora(),
            llamadas=ritmo.llamadas, error=f"{type(e).__name__}: {e}",
        )
        return 1
    finally:
        soltar_lease(db, dueno)


def _ejecutar_modo(
    modo: str,
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    inicio: datetime,
    opciones: Opciones,
    renovar: Callable[[], None],
) -> tuple[Contadores, list[str]]:
    if modo == "vincular":
        return Contadores(), []
    if modo == "backfill":
        r = ejecutar_backfill(
            db, cliente, ritmo,
            hoy=hoy_en_santiago(inicio), ahora=inicio, desde=opciones.desde,
            dias_vacios_para_parar=opciones.dias_vacios_para_parar,
            dias_futuro=opciones.dias_futuro, verificar=opciones.verificar,
            al_terminar_dia=renovar,
        )
        log.info(
            "Backfill: %d días barridos, primer día con datos %s, %d atenciones recuperadas",
            r.dias_barridos, r.primer_dia_con_datos, r.atenciones_recuperadas,
        )
        if r.atenciones_anteriores:
            log.warning(
                "%d atenciones son anteriores al primer día con citas: re-ejecutar con --desde más antiguo",
                r.atenciones_anteriores,
            )
        return r.contadores, r.errores
    ventana = {"caliente": ventana_caliente, "tibia": ventana_tibia, "fria": ventana_fria}[modo]
    r = ventana(db, cliente, ritmo, inicio, al_terminar_dia=renovar)
    return r.contadores, r.errores


def _ultimo_inicio_exitoso(db: Session) -> datetime | None:
    return db.scalar(
        select(func.max(SalutemSyncEjecucion.inicio)).where(
            SalutemSyncEjecucion.estado.in_(("ok", "con_errores"))
        )
    )
```

Nota para el ejecutor: `_ultimo_inicio_exitoso` usa `inicio` (no `fin`) a propósito: un ingreso editado mientras corría la ejecución anterior debe entrar en la siguiente.

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_orquestador.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/salutem_sync/orquestador.py tests/salutem_sync/test_orquestador.py
git commit -m "feat(salutem): orquestador de modos con lease, bitácora y vinculación final

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: Estado del sync (servicio + endpoint)

**Files:**
- Create: `backend/app/schemas/salutem_sync.py`
- Create: `backend/app/services/salutem_sync/estado.py`
- Create: `backend/app/routers/salutem_sync.py`
- Modify: `backend/app/main.py` (import + `include_router`)
- Test: `backend/tests/salutem_sync/test_estado_api.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_estado_api.py`:

```python
from datetime import datetime, timedelta, timezone

from app.models.salutem_sync import SalutemSyncEjecucion

URL = "/api/v1/salutem/sync/estado"


def _ejecucion(db, modo, estado, hace_min):
    fin = datetime.now(timezone.utc) - timedelta(minutes=hace_min)
    db.add(
        SalutemSyncEjecucion(
            modo=modo, estado=estado, inicio=fin - timedelta(minutes=1), fin=fin,
            llamadas=10, nuevos=1, cambiados=0, desaparecidos=0,
        )
    )
    db.flush()


def test_sin_ejecuciones_esta_atrasado(as_coordinacion):
    r = as_coordinacion.get(URL)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["atrasado"] is True
    assert cuerpo["ultimas"] == {}
    assert cuerpo["atenciones"] == 0


def test_una_caliente_reciente_lo_deja_al_dia(as_coordinacion, db_session):
    _ejecucion(db_session, "caliente", "ok", hace_min=3)
    cuerpo = as_coordinacion.get(URL).json()
    assert cuerpo["atrasado"] is False
    assert cuerpo["ultimas"]["caliente"]["llamadas"] == 10


def test_una_caliente_vieja_esta_atrasada_y_las_omitidas_no_cuentan(as_coordinacion, db_session):
    _ejecucion(db_session, "caliente", "ok", hace_min=45)
    _ejecucion(db_session, "caliente", "omitida", hace_min=1)
    cuerpo = as_coordinacion.get(URL).json()
    assert cuerpo["atrasado"] is True
    assert cuerpo["ultimas"]["caliente"]["estado"] == "ok"


def test_otros_roles_no_acceden(as_auditor):
    assert as_auditor.get(URL).status_code == 403
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_estado_api.py -v`
Expected: FAIL con 404 en `r.status_code`.

- [ ] **Step 3: Implementar**

`backend/app/schemas/salutem_sync.py`:

```python
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EjecucionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modo: str
    estado: str
    inicio: datetime
    fin: datetime | None
    llamadas: int
    nuevos: int
    cambiados: int
    desaparecidos: int
    error: str | None


class EstadoSyncRead(BaseModel):
    ultimas: dict[str, EjecucionRead]
    primer_dia_con_datos: date | None
    personas: int
    citas: int
    atenciones: int
    # Atenciones de pacientes CEPA que aún no pasan a ficha_clinica.
    atenciones_pendientes: int
    # La última ejecución `caliente` exitosa terminó hace más de 20 minutos (o nunca).
    atrasado: bool
```

`backend/app/services/salutem_sync/estado.py`:

```python
"""Estado del sync para el endpoint y el CLI."""

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.models.salutem_sync import SalutemSyncEjecucion
from app.schemas.salutem_sync import EjecucionRead, EstadoSyncRead
from app.services.salutem_sync.tipos import MODOS

MAX_ATRASO = timedelta(minutes=20)
EXITOSAS = ("ok", "con_errores")


def estado_sync(db: Session, ahora: datetime) -> EstadoSyncRead:
    ultimas: dict[str, EjecucionRead] = {}
    for modo in MODOS:
        ejecucion = db.scalars(
            select(SalutemSyncEjecucion)
            .where(SalutemSyncEjecucion.modo == modo, SalutemSyncEjecucion.estado != "omitida")
            .order_by(SalutemSyncEjecucion.inicio.desc(), SalutemSyncEjecucion.id.desc())
            .limit(1)
        ).first()
        if ejecucion is not None:
            ultimas[modo] = EjecucionRead.model_validate(ejecucion)

    # Se compara en SQL: Oracle puede devolver los timestamps sin zona.
    calientes_recientes = db.scalar(
        select(func.count()).select_from(SalutemSyncEjecucion).where(
            SalutemSyncEjecucion.modo == "caliente",
            SalutemSyncEjecucion.estado.in_(EXITOSAS),
            SalutemSyncEjecucion.fin >= ahora - MAX_ATRASO,
        )
    )
    pendientes = db.scalar(
        select(func.count())
        .select_from(SalutemAtencion)
        .join(SalutemPersona, SalutemPersona.salutem_id == SalutemAtencion.persona_id)
        .join(Paciente, Paciente.rut == SalutemPersona.rut)
        .where(
            or_(
                SalutemAtencion.hash_vinculado.is_(None),
                SalutemAtencion.hash_vinculado != SalutemAtencion.hash_contenido,
            )
        )
    )
    return EstadoSyncRead(
        ultimas=ultimas,
        primer_dia_con_datos=db.scalar(select(func.min(SalutemCita.fecha_cita))),
        personas=db.scalar(select(func.count()).select_from(SalutemPersona)),
        citas=db.scalar(select(func.count()).select_from(SalutemCita)),
        atenciones=db.scalar(select(func.count()).select_from(SalutemAtencion)),
        atenciones_pendientes=pendientes,
        atrasado=calientes_recientes == 0,
    )
```

`backend/app/routers/salutem_sync.py`:

```python
"""Estado del sync SALUTEM (fase 1, solo lectura)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.salutem_sync import EstadoSyncRead
from app.services.salutem_sync.estado import estado_sync

router = APIRouter(prefix="/api/v1/salutem/sync", tags=["salutem-sync"])


@router.get(
    "/estado",
    response_model=EstadoSyncRead,
    dependencies=[Depends(require_role("Coordinacion"))],
)
def estado(db: Session = Depends(get_db)) -> EstadoSyncRead:
    return estado_sync(db, datetime.now(timezone.utc))
```

En `backend/app/main.py`, junto a los demás imports de routers:

```python
from app.routers import salutem_sync as salutem_sync_router
```

y después de `app.include_router(fichas_clinicas_router.router)`:

```python
app.include_router(salutem_sync_router.router)
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_estado_api.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add app/schemas/salutem_sync.py app/services/salutem_sync/estado.py app/routers/salutem_sync.py app/main.py tests/salutem_sync/test_estado_api.py
git commit -m "feat(salutem): endpoint de estado del sync con alerta de atraso

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: CLI

**Files:**
- Create: `backend/app/scripts/salutem_sync.py`
- Test: `backend/tests/salutem_sync/test_cli.py`

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/salutem_sync/test_cli.py`:

```python
import contextlib
import json
from datetime import date

import pytest

from app.config import Settings
from app.scripts import salutem_sync as cli


@pytest.fixture
def cli_con_bd(monkeypatch, db_session):
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db_session))
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    return cli


def test_parser_backfill_con_opciones():
    args = cli.construir_parser().parse_args(["backfill", "--desde", "2023-01-01", "--sin-verificar"])
    assert (args.modo, args.desde, args.sin_verificar) == ("backfill", date(2023, 1, 1), True)


def test_parser_rechaza_modos_desconocidos():
    with pytest.raises(SystemExit):
        cli.construir_parser().parse_args(["tempestad"])


def test_estado_imprime_json(cli_con_bd, capsys):
    assert cli_con_bd.main(["estado"]) == 0
    assert "atrasado" in json.loads(capsys.readouterr().out)


def test_con_el_sync_apagado_sale_en_cero_sin_red(cli_con_bd, monkeypatch):
    def no_debe_llamarse():
        raise AssertionError("no debe construir el cliente SALUTEM con el sync apagado")

    monkeypatch.setattr(cli, "get_salutem_client", no_debe_llamarse)
    assert cli_con_bd.main(["caliente"]) == 0
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/salutem_sync/test_cli.py -v`
Expected: FAIL con `ImportError: cannot import name 'salutem_sync' from 'app.scripts'`.

- [ ] **Step 3: Implementar**

`backend/app/scripts/salutem_sync.py`:

```python
"""Sync SALUTEM → CEPA (fase 1, solo lectura). Lo lanza el cron de la VM.

Uso (desde backend/):
    .venv/bin/python -m app.scripts.salutem_sync caliente | tibia | fria
    .venv/bin/python -m app.scripts.salutem_sync backfill [--desde AAAA-MM-DD] [--sin-verificar]
    .venv/bin/python -m app.scripts.salutem_sync vincular [--todo]
    .venv/bin/python -m app.scripts.salutem_sync estado
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from logging.handlers import RotatingFileHandler

from app.config import get_settings
from app.db.session import SessionLocal
from app.integrations.salutem.client import get_salutem_client
from app.services.salutem_sync.estado import estado_sync
from app.services.salutem_sync.orquestador import Opciones, correr
from app.services.salutem_sync.ritmo import Ritmo


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync SALUTEM → CEPA (solo lectura)")
    modos = parser.add_subparsers(dest="modo", required=True)
    backfill = modos.add_parser("backfill", help="Carga inicial completa")
    backfill.add_argument("--desde", type=date.fromisoformat, help="No barrer antes de esta fecha")
    backfill.add_argument("--sin-verificar", action="store_true", help="Omitir la verificación por persona")
    for modo in ("caliente", "tibia", "fria"):
        modos.add_parser(modo)
    vincular = modos.add_parser("vincular", help="Solo el paso copia → ficha_clinica")
    vincular.add_argument("--todo", action="store_true", help="Revisar todas las atenciones")
    modos.add_parser("estado", help="Mostrar el estado del sync")
    return parser


def _configurar_log(ruta: str) -> None:
    if ruta:
        handler: logging.Handler = RotatingFileHandler(
            ruta, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(handler)


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    settings = get_settings()
    _configurar_log(settings.salutem_sync_log)

    with SessionLocal() as db:
        if args.modo == "estado":
            estado = estado_sync(db, datetime.now(timezone.utc))
            print(json.dumps(estado.model_dump(mode="json"), indent=2, ensure_ascii=False))
            return 0
        if not settings.salutem_sync_habilitado:
            logging.getLogger("salutem_sync").info(
                "Sync SALUTEM deshabilitado (SALUTEM_SYNC_HABILITADO=false)"
            )
            return 0
        return correr(
            args.modo,
            db,
            get_salutem_client(),
            Ritmo(settings.salutem_sync_llamadas_por_seg),
            ahora=lambda: datetime.now(timezone.utc),
            habilitado=True,
            opciones=Opciones(
                desde=getattr(args, "desde", None),
                verificar=not getattr(args, "sin_verificar", False),
                dias_vacios_para_parar=settings.salutem_backfill_dias_vacios,
                vincular_todo=getattr(args, "todo", False),
            ),
        )


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/salutem_sync/test_cli.py -v`
Expected: PASS (4 tests).

Prueba de humo real (sin red, con el sync apagado):
Run: `uv run python -m app.scripts.salutem_sync caliente; echo "salida=$?"`
Expected: una línea de log `Sync SALUTEM deshabilitado` y `salida=0`.

- [ ] **Step 5: Commit**

```bash
git add app/scripts/salutem_sync.py tests/salutem_sync/test_cli.py
git commit -m "feat(salutem): CLI del sync para cron (backfill, ventanas, vincular, estado)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: Operación en la VM (script, crontab, runbook)

**Files:**
- Create: `ops/vm/run-salutem-sync.sh` (raíz del repo, no `backend/`)
- Create: `ops/vm/crontab-salutem-sync.txt`
- Create: `docs/operacion/salutem-sync.md`

- [ ] **Step 1: Crear el script de arranque**

`ops/vm/run-salutem-sync.sh`:

```bash
#!/usr/bin/env bash
# Lanza un modo del sync SALUTEM en la VM UTalca. Lo usa el crontab de segicepa.
# Uso: run-salutem-sync.sh <caliente|tibia|fria|backfill|vincular|estado> [opciones]
# Mismo entorno Oracle que run-api.sh: sin LD_LIBRARY_PATH y TNS_ADMIN el modo Thick falla.
set -euo pipefail

export LD_LIBRARY_PATH="$HOME/opt/instantclient_19_26${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TNS_ADMIN="$HOME/opt/tns"

mkdir -p "$HOME/sige-cepa/logs"
cd "$HOME/sige-cepa/backend"
# El log estructurado va a SALUTEM_SYNC_LOG (ver .env); acá solo cae lo que muera antes de configurarlo.
exec .venv/bin/python -m app.scripts.salutem_sync "$@" >> "$HOME/sige-cepa/logs/salutem-sync-cron.log" 2>&1
```

Run: `chmod +x ../ops/vm/run-salutem-sync.sh && bash -n ../ops/vm/run-salutem-sync.sh && echo sintaxis-ok`
Expected: `sintaxis-ok`

- [ ] **Step 2: Crear el fragmento de crontab**

`ops/vm/crontab-salutem-sync.txt`:

```
# Sync SALUTEM (fase 1). Agregar al crontab de segicepa SIN borrar las entradas @reboot ni el watchdog.
# El lease en BD evita que dos modos se pisen: si uno está corriendo, el otro queda "omitida".
*/5 * * * * $HOME/sige-cepa/run-salutem-sync.sh caliente
7 * * * * $HOME/sige-cepa/run-salutem-sync.sh tibia
30 3 * * * $HOME/sige-cepa/run-salutem-sync.sh fria
```

- [ ] **Step 3: Escribir el runbook**

`docs/operacion/salutem-sync.md`:

````markdown
# Runbook — Sync SALUTEM (fase 1, solo lectura)

Diseño: `docs/superpowers/specs/2026-09-16-salutem-sync-fase1-design.md`.

## Qué hace
- Copia todo SALUTEM (empresa 96) a las tablas `salutem_persona`, `salutem_cita`, `salutem_atencion`.
- Vincula las atenciones con `ficha_clinica` por RUT y ventana del ingreso.
- Nunca escribe en SALUTEM (D12).

## Variables (`~/sige-cepa/backend/.env`)

| Variable | Valor en la VM | Nota |
|---|---|---|
| `SALUTEM_BASE_URL` | `https://api.salutem.cl/api/integraciones/salutem` (PROD) | QA: `https://qa.salutem.cl/...` |
| `SALUTEM_EMPRESA` | `96` | |
| `SALUTEM_API_KEY` | (clave de producción) | no versionar |
| `SALUTEM_SYNC_HABILITADO` | `true` | `false` apaga todo sin tocar el cron |
| `SALUTEM_SYNC_LLAMADAS_POR_SEG` | `2` | ajustar con el límite que confirme FabricApp |
| `SALUTEM_BACKFILL_DIAS_VACIOS` | `365` | |
| `SALUTEM_SYNC_LOG` | `/home/segicepa/sige-cepa/logs/salutem-sync.log` | rota a 5 × 10 MB |

## Puesta en marcha (una vez)
Requiere aprobación explícita de Darío, la clave de producción y el aviso a DTI.

1. Desplegar el backend con el procedimiento habitual (memoria `despliegue-vm-utalca`) y aplicar migraciones:
   `cd ~/sige-cepa/backend && LD_LIBRARY_PATH=$HOME/opt/instantclient_19_26 TNS_ADMIN=$HOME/opt/tns .venv/bin/alembic upgrade head`
2. Copiar `ops/vm/run-salutem-sync.sh` a `~/sige-cepa/run-salutem-sync.sh` y `chmod +x`.
   Comparar sus `export` con los de `~/sige-cepa/run-api.sh`; deben coincidir.
3. Configurar las variables del `.env` con `SALUTEM_SYNC_HABILITADO=true`.
4. Probar: `~/sige-cepa/run-salutem-sync.sh estado` → JSON con `"atrasado": true`.
5. Carga inicial fuera de horario:
   `nohup ~/sige-cepa/run-salutem-sync.sh backfill > /dev/null 2>&1 &`
   Seguir con `tail -f ~/sige-cepa/logs/salutem-sync.log`. Se puede cortar y relanzar: retoma.
6. Al terminar, revisar el log: primer día con datos, días con error y la advertencia de
   "atenciones anteriores" (si aparece, relanzar con `--desde` más antiguo).
7. Instalar el cron: `crontab -l > ~/crontab-backup-$(date +%F).txt`, luego
   `(crontab -l; cat ops/vm/crontab-salutem-sync.txt) | crontab -` y verificar con `crontab -l`.

## Operación diaria
- Estado: `~/sige-cepa/run-salutem-sync.sh estado` o `GET /api/v1/salutem/sync/estado` (Coordinación).
- `atrasado: true` → revisar `~/sige-cepa/logs/salutem-sync.log` y la última ejecución con `estado = error`.
- `con_errores` → algún día fue rechazado por SALUTEM; la ventana siguiente lo reintenta.
- Revincular todo tras cambiar la regla de ventana: `run-salutem-sync.sh vincular --todo`.

## Apagar
`SALUTEM_SYNC_HABILITADO=false` en el `.env`. El cron sigue corriendo pero cada ejecución sale sin hacer nada.
Para retirar del todo: quitar las tres líneas del crontab.

## Validación en QA (antes de producción)
Registrar aquí los resultados de la Task 15 del plan.
````

- [ ] **Step 4: Commit**

```bash
git add ../ops/vm/run-salutem-sync.sh ../ops/vm/crontab-salutem-sync.txt ../docs/operacion/salutem-sync.md
git commit -m "docs(salutem): script de cron, crontab y runbook del sync en la VM

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 15: Validación manual contra SALUTEM QA

Solo lectura contra QA; no toca la VM. Necesita la clave de QA (está en `~/sige-cepa/backend/.env` de la VM como `SALUTEM_API_KEY`, o pedírsela a Darío). **No commitear la clave.**

**Files:**
- Modify (si corresponde): `backend/app/services/salutem_sync/hash.py` (`CAMPOS_VOLATILES`)
- Modify (si corresponde): `backend/app/services/salutem_sync/barrido.py` (`ESTADOS_CON_ATENCION`)
- Modify: `docs/operacion/salutem-sync.md` (sección "Validación en QA")

- [ ] **Step 1: Preparar una BD local limpia**

Run: `docker compose exec -T db psql -U cepa -c "DROP DATABASE IF EXISTS cepa_salutem_qa" -c "CREATE DATABASE cepa_salutem_qa"`
(Si el servicio de compose tiene otro nombre, usar `docker compose ps` para verlo.)

Run: `export DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_salutem_qa SALUTEM_EMPRESA=96 SALUTEM_API_KEY='<clave QA>' && uv run alembic upgrade head`
Expected: migraciones hasta `1250` sin error.

- [ ] **Step 2: `obtener_persona` responde con `persona_id`**

Run (con las variables del Step 1 exportadas):

```bash
uv run python - <<'EOF'
from datetime import date
from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.models import EstadoCitaSalutem
c = get_salutem_client()
citas = c.listar_citas(date(2025, 1, 22), EstadoCitaSalutem.ATENDIDO)
print("citas atendidas:", len(citas))
p = c.obtener_persona(citas[0].persona_id)
print("persona:", p and (p.salutem_id, p.identificacion))
EOF
```

Expected: `citas atendidas: 44` (o cercano) y una persona con su id. Si `persona: None`, SALUTEM no acepta `persona_id` en `/personas`: detener y reportar, porque el barrido depende de esto.

- [ ] **Step 3: Estabilidad del hash (dos barridos seguidos)**

```bash
uv run python - <<'EOF'
from datetime import date, datetime, timezone
from app.db.session import SessionLocal
from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.models import TipoFechaCita
from app.services.salutem_sync.barrido import barrer_dia
from app.services.salutem_sync.ritmo import Ritmo
cliente, ritmo = get_salutem_client(), Ritmo(2)
with SessionLocal() as db:
    for vuelta in (1, 2):
        r = barrer_dia(db, cliente, ritmo, date(2025, 1, 22), TipoFechaCita.FECHA_CITA, datetime.now(timezone.utc))
        print(vuelta, "citas", r.citas, "completo", r.completo, r.contadores, r.errores)
EOF
```

Expected: vuelta 1 con ~52 citas y `nuevos` > 0; vuelta 2 con `nuevos=0, cambiados=0, desaparecidos=0`.
Si la vuelta 2 muestra `cambiados > 0`: comparar dos respuestas crudas de `obtener_atencion` / `listar_citas` para la misma cita, identificar las claves que cambian solas, agregarlas a `CAMPOS_VOLATILES` en `hash.py` con un comentario de qué son, agregar un test en `tests/salutem_sync/test_hash_ritmo.py` con esa clave, y repetir.

- [ ] **Step 4: ¿Hay atenciones fuera del estado Atendido?**

```bash
uv run python - <<'EOF'
from datetime import date
from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.models import EstadoCitaSalutem
c = get_salutem_client()
for estado in EstadoCitaSalutem:
    if estado == EstadoCitaSalutem.ATENDIDO:
        continue
    citas = c.listar_citas(date(2025, 1, 22), estado)[:5]
    con_atencion = sum(1 for x in citas if c.obtener_atencion(x.persona_id, x.cita_id))
    print(estado.name, "revisadas", len(citas), "con atención", con_atencion)
EOF
```

Expected: `con atención 0` en todos. Si algún estado tiene atenciones: agregarlo a `ESTADOS_CON_ATENCION` en `barrido.py`, ajustar el test `test_primer_barrido_trae_citas_persona_y_atencion` si cambia el conteo, y correr `uv run pytest tests/salutem_sync -v`.

- [ ] **Step 5: Backfill acotado y ventana caliente end-to-end**

Run: `SALUTEM_SYNC_HABILITADO=true uv run python -m app.scripts.salutem_sync backfill --desde 2026-09-01; echo "salida=$?"`
Expected: `salida=0`; en el log, días barridos ≈ 16 + 180 futuros.

Run: `SALUTEM_SYNC_HABILITADO=true uv run python -m app.scripts.salutem_sync caliente; echo "salida=$?" && uv run python -m app.scripts.salutem_sync estado`
Expected: `salida=0` y JSON con `ultimas.caliente.estado` = `ok` y `atrasado: false`.

- [ ] **Step 6: Registrar resultados y commitear**

Completar la sección "Validación en QA" de `docs/operacion/salutem-sync.md` con: fecha, conteos de cada paso, campos volátiles encontrados (o "ninguno"), estados con atención (o "solo Atendido"), duración real del backfill acotado y llamadas por minuto observadas.

```bash
git add ../docs/operacion/salutem-sync.md app/services/salutem_sync/hash.py app/services/salutem_sync/barrido.py tests/salutem_sync/
git commit -m "docs(salutem): resultados de la validación del sync contra QA

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16: Verificación final y PR

- [ ] **Step 1: Suite completa y lint**

Run: `uv run pytest -q && uv run ruff check app tests`
Expected: todos los tests en verde (baseline previo + los nuevos de `tests/salutem_sync/`) y ruff sin errores.

- [ ] **Step 2: Revisión contra la spec**

Recorrer `docs/superpowers/specs/2026-09-16-salutem-sync-fase1-design.md` sección por sección y confirmar que cada punto tiene implementación o está explícitamente fuera de alcance. Actualizar la memoria del proyecto (`engram`, topic `cepa-preview/salutem-sync-fase1`) con el estado.

- [ ] **Step 3: Push y PR (confirmar con Darío antes)**

Pushear con la cuenta gh `dario-kreante` (con `Kreante` da 403):

```bash
gh auth switch --user dario-kreante
git push -u origin claude/salutem-realtime-sync-0315fd
gh pr create --base main --title "feat(salutem): sync fase 1 — copia completa de SALUTEM y sync cada 5 minutos" --body-file <archivo con resumen, validación QA y pendientes externos>
```

El cuerpo del PR termina con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Revisar el CI (job Oracle incluido). El workflow `vercel-deploy` falla por token caducado: es ruido conocido.

- [ ] **Step 4: Despliegue**

No desplegar sin aprobación explícita. El despliegue a la VM y la carga inicial en producción siguen `docs/operacion/salutem-sync.md` y requieren la clave de producción y el aviso a DTI.
