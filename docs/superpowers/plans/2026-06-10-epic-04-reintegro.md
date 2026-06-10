# EPIC-04 — Seguimiento de Reintegro — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar el módulo de Seguimiento de Reintegro del Sistema CEPA — registro del caso de reintegro vinculado al folio/ingreso (CEPA-040), proceso RECA con medidas correctivas (CEPA-041), y reintegro con cierre del caso (CEPA-042) — sobre Fundación + EPIC-00 + EPIC-01 ya en `main`.

**Architecture:** Sigue el patrón de las épicas anteriores: modelos en `app/models/reintegro.py`, schemas Pydantic v2 en `app/schemas/reintegro.py`, lógica de negocio en `app/services/reintegro.py`, router `APIRouter` con prefijo `/api/v1/reintegros` en `app/routers/reintegros.py`, y una migración Alembic por historia que toca el esquema. Las listas cerradas (tipos de derivación D4, estado de reintegro, tipos de RECA, tipos de alta) son Enums Python, nunca tipos nativos de motor. El caso de reintegro (tabla `caso_reintegro`) referencia al `ingreso` vía FK. La RECA (tabla `reca`) y el cierre (columnas en `caso_reintegro`) son subrecursos. Toda escritura registra auditoría vía `record_audit` y exige rol `Administrativo`/`Coordinacion`; `Auditor` accede solo a lectura.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos, `Identity`/`BigInteger`, `DateTime(timezone=True)`, `Date`, `Boolean`, `Text`), Alembic, Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`; fixtures `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`. Importa de EPIC-01: `app.util.rut.normalizar_rut`, `app.domain.enums.TipoDerivacion`, `app.models.ingreso.Ingreso`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role`
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`, `action ∈ {CREATE, UPDATE, DELETE}`.
- Fixtures: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.
- `from app.util.rut import normalizar_rut, RutInvalidoError` — disponible de EPIC-01.
- `from app.domain.enums import TipoDerivacion` — disponible de EPIC-01.
- Tabla `ingreso` y FK `ingreso.id` — disponible de EPIC-01.

**Convención de RBAC en los routers de esta épica:**
```python
from app.auth.deps import get_current_user, require_role

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")
```

---

## Convenciones de modelado de esta épica

- **PK subrogada:** `id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)`.
- **Fechas de calendario sin hora** (fechas de RECA, medidas, reintegro, altas): `Date`.
- **Fechas/tiempos con hora:** `DateTime(timezone=True)` con `_utcnow()` local en cada modelo.
- **Listas cerradas:** Enums Python `str, Enum`; columna `String(40)`; validación Pydantic. Nunca `CHECK`/tipos enum de motor.
- **Identificadores:** minúscula y ≤30 caracteres.

Tablas que crea esta épica: `caso_reintegro`, `reca`.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `backend/app/domain/reintegro_enums.py` | Enums del dominio de reintegro (estado, tipo RECA, tipo alta reintegro, riesgos) |
| `backend/app/models/reintegro.py` | Modelos SQLAlchemy: `CasoReintegro`, `Reca` |
| `backend/app/schemas/reintegro.py` | Schemas Pydantic v2 para request/response |
| `backend/app/services/reintegro.py` | Lógica de negocio: validaciones temporales, reglas de cierre |
| `backend/app/routers/reintegros.py` | APIRouter `/api/v1/reintegros` con endpoints CRUD + RECA + cierre |
| `backend/migrations/versions/0040_crear_caso_reintegro.py` | Migración CEPA-040 |
| `backend/migrations/versions/0041_crear_reca.py` | Migración CEPA-041 |
| `backend/migrations/versions/0042_reintegro_cierre.py` | Migración CEPA-042 (columnas de cierre) |
| `backend/tests/test_reintegro_enums.py` | Tests unitarios de Enums |
| `backend/tests/test_reintegro_model.py` | Tests de modelo (portabilidad, columnas) |
| `backend/tests/test_reintegro_api.py` | Tests de integración API — CEPA-040 |
| `backend/tests/test_reca_api.py` | Tests de integración API — CEPA-041 |
| `backend/tests/test_reintegro_cierre_api.py` | Tests de integración API — CEPA-042 |

---

## Task 1: Enums del dominio de reintegro

Listas cerradas específicas de este módulo. `TipoDerivacion` ya existe en EPIC-01 (`app/domain/enums.py`); aquí solo se definen los nuevos enums de reintegro.

**Files:**
- Create: `backend/app/domain/reintegro_enums.py`
- Test: `backend/tests/test_reintegro_enums.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reintegro_enums.py`:

```python
from app.domain.reintegro_enums import (
    EstadoReintegro,
    TipoAlta as TipoAltaReintegro,
    TipoReca,
)


def test_estado_reintegro_lista_cerrada():
    valores = {e.value for e in EstadoReintegro}
    assert valores == {"pendiente", "parcial", "total"}


def test_tipo_reca_existe():
    # lista cerrada; los valores vienen del spec (pendiente de catálogo definitivo)
    valores = {t.value for t in TipoReca}
    assert "AT" in valores    # Accidente del Trabajo
    assert "EP" in valores    # Enfermedad Profesional


def test_tipo_alta_reintegro():
    valores = {t.value for t in TipoAltaReintegro}
    assert "terapeutica" in valores
    assert "medica" in valores
    assert "psicologica" in valores
    assert "abandono" in valores
    assert "derivacion" in valores
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reintegro_enums.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.domain.reintegro_enums'`.

- [ ] **Step 3: Implementar los Enums**

Crear `backend/app/domain/reintegro_enums.py`:

```python
"""Listas cerradas del módulo de Seguimiento de Reintegro (EPIC-04).

TipoDerivacion ya existe en app.domain.enums (EPIC-01); aquí solo se definen
los enums específicos del reintegro.

NOTA: el catálogo definitivo de TipoReca y los riesgos calificados está
pendiente de confirmación con Coordinación (Decisiones v4, CEPA-041 nota).
Esta lista provisional (AT / EP) es suficiente para pasar tests; ampliar
cuando el equipo gestor CEPA entregue el catálogo completo.
"""

from enum import Enum


class EstadoReintegro(str, Enum):
    """Estado del proceso de reintegro (CEPA-042 RN-1)."""

    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    TOTAL = "total"


class TipoReca(str, Enum):
    """Tipo de RECA (Resolución de Calificación). Lista provisional — confirmar catálogo."""

    AT = "AT"   # Accidente del Trabajo
    EP = "EP"   # Enfermedad Profesional


class TipoAlta(str, Enum):
    """Tipo de alta al cerrar el caso de reintegro (CEPA-042 RN-4, D11)."""

    TERAPEUTICA = "terapeutica"
    MEDICA = "medica"
    PSICOLOGICA = "psicologica"
    ABANDONO = "abandono"
    DERIVACION = "derivacion"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_reintegro_enums.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/reintegro_enums.py backend/tests/test_reintegro_enums.py
git commit -m "feat(reintegro): enums del dominio de reintegro (estado, tipo RECA, tipo alta)"
```

---

## Task 2: Modelos `CasoReintegro` y `Reca` + tests de portabilidad

Crea los modelos SQLAlchemy sin migración todavía (las migraciones van en Tasks 3 y 5). Los tests verifican las reglas de portabilidad (identificadores ≤30 chars, minúscula, Identity, tipos genéricos).

**Files:**
- Create: `backend/app/models/reintegro.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_reintegro_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reintegro_model.py`:

```python
from sqlalchemy import BigInteger, Boolean, Date, DateTime, String, Text

from app.models.reintegro import CasoReintegro, Reca


# ── CasoReintegro ──────────────────────────────────────────────────────────

def test_caso_reintegro_tabla_y_columnas():
    tabla = CasoReintegro.__table__
    assert tabla.name == "caso_reintegro"
    esperadas = {
        "id",
        "ingreso_id",
        "rut",
        "nombre",
        "tipo_derivacion",
        "fecha_caso",
        "sexo",
        "edad",
        "region",
        "comuna",
        "rubro_empleador",
        "estado_reintegro",
        "fecha_reintegro",
        "remitido_isl",
        "alta_medica",
        "fecha_alta_medica",
        "alta_psicologica",
        "fecha_alta_psico",
        "tipo_alta",
        "observaciones",
        "created_at",
        "updated_at",
    }
    assert set(tabla.columns.keys()) == esperadas


def test_caso_reintegro_portabilidad():
    tabla = CasoReintegro.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"'{nombre}' debe ir en minúscula"
        assert len(nombre) <= 30, f"'{nombre}' supera 30 chars (Oracle)"


def test_caso_reintegro_tipos_y_pk():
    cols = CasoReintegro.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["rut"].type, String)
    assert isinstance(cols["fecha_caso"].type, Date)
    assert isinstance(cols["remitido_isl"].type, Boolean)
    assert isinstance(cols["alta_medica"].type, Boolean)
    assert isinstance(cols["alta_psicologica"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_caso_reintegro_fk_ingreso():
    cols = CasoReintegro.__table__.columns
    fks = list(cols["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


# ── Reca ───────────────────────────────────────────────────────────────────

def test_reca_tabla_y_columnas():
    tabla = Reca.__table__
    assert tabla.name == "reca"
    esperadas = {
        "id",
        "caso_reintegro_id",
        "fecha_reca",
        "tipo_reca",
        "numero_reca",
        "riesgos_calificados",
        "razon_social",
        "solicita_medidas",
        "detalle_medidas",
        "fecha_medidas",
        "verifica_medidas",
        "detalle_verificacion",
        "fecha_verificacion",
        "created_at",
        "updated_at",
    }
    assert set(tabla.columns.keys()) == esperadas


def test_reca_portabilidad():
    tabla = Reca.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"'{nombre}' debe ir en minúscula"
        assert len(nombre) <= 30, f"'{nombre}' supera 30 chars (Oracle)"


def test_reca_tipos_y_pk():
    cols = Reca.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["fecha_reca"].type, Date)
    assert isinstance(cols["solicita_medidas"].type, Boolean)
    assert isinstance(cols["verifica_medidas"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_reca_numero_unico_por_caso():
    # La unicidad (numero_reca, caso_reintegro_id) se aplica con UniqueConstraint
    tabla = Reca.__table__
    nombres_constraints = [c.name for c in tabla.constraints]
    assert any("uq_reca_numero_caso" in (n or "") for n in nombres_constraints)


def test_reca_fk_caso_reintegro():
    cols = Reca.__table__.columns
    fks = list(cols["caso_reintegro_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "caso_reintegro"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reintegro_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.reintegro'`.

- [ ] **Step 3: Implementar los modelos**

Crear `backend/app/models/reintegro.py`:

```python
"""Modelos del módulo de Seguimiento de Reintegro (EPIC-04).

Tablas: caso_reintegro, reca.
- caso_reintegro: vinculado al ingreso (FK); contiene los datos del caso (CEPA-040)
  y las columnas de cierre/reintegro (CEPA-042).
- reca: subrecurso de caso_reintegro; contiene datos de la RECA y medidas (CEPA-041).
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.reintegro_enums import EstadoReintegro


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CasoReintegro(Base):
    """Caso de reintegro laboral vinculado a un ingreso/folio (CEPA-040, 042).

    Los campos de reintegro y cierre (estado_reintegro, fecha_reintegro,
    altas, tipo_alta) se completan en la fase de cierre (CEPA-042).
    """

    __tablename__ = "caso_reintegro"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    # Datos del caso (CEPA-040) ────────────────────────────────────────────
    rut: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo_derivacion: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_caso: Mapped[date] = mapped_column(Date, nullable=False)
    sexo: Mapped[str] = mapped_column(String(10), nullable=False)
    edad: Mapped[int] = mapped_column(BigInteger, nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    comuna: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rubro_empleador: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Cierre / reintegro (CEPA-042) ────────────────────────────────────────
    estado_reintegro: Mapped[str] = mapped_column(
        String(20), default=EstadoReintegro.PENDIENTE.value, nullable=False
    )
    fecha_reintegro: Mapped[date | None] = mapped_column(Date, nullable=True)
    remitido_isl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alta_medica: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_alta_medica: Mapped[date | None] = mapped_column(Date, nullable=True)
    alta_psicologica: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_alta_psico: Mapped[date | None] = mapped_column(String(10), nullable=True)
    tipo_alta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Auditoría ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    reca: Mapped["Reca | None"] = relationship(
        back_populates="caso", uselist=False, cascade="all, delete-orphan"
    )


class Reca(Base):
    """RECA (Resolución de Calificación) y ciclo de medidas correctivas (CEPA-041).

    Una RECA por caso de reintegro. El número de RECA es único dentro del caso
    (restricción UniqueConstraint sobre numero_reca + caso_reintegro_id).
    """

    __tablename__ = "reca"
    __table_args__ = (
        UniqueConstraint(
            "numero_reca", "caso_reintegro_id", name="uq_reca_numero_caso"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    caso_reintegro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("caso_reintegro.id"), nullable=False, index=True
    )
    # Datos RECA ───────────────────────────────────────────────────────────
    fecha_reca: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_reca: Mapped[str] = mapped_column(String(10), nullable=False)
    numero_reca: Mapped[str] = mapped_column(String(40), nullable=False)
    riesgos_calificados: Mapped[str | None] = mapped_column(Text, nullable=True)
    razon_social: Mapped[str] = mapped_column(String(160), nullable=False)
    # Medidas correctivas ──────────────────────────────────────────────────
    solicita_medidas: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detalle_medidas: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_medidas: Mapped[date | None] = mapped_column(Date, nullable=True)
    verifica_medidas: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detalle_verificacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_verificacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Auditoría ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    caso: Mapped["CasoReintegro"] = relationship(back_populates="reca")
```

Notar: `fecha_alta_psico` usa `String(10)` para persistir `YYYY-MM-DD` como texto portable — esto es intencional para evitar ambigüedad; cambiar a `Date` si el equipo prefiere mantener coherencia con los demás campos de fecha (ambas opciones son portables). **Recomendado: cambiar a `Date` antes del loop.** (Ver Notas de cierre.)

**Corrección:** el modelo usa `String(10)` para `fecha_alta_psico` por error de transcripción. Usar `Date` igual que el resto. Editar el modelo a:

```python
    fecha_alta_psico: Mapped[date | None] = mapped_column(Date, nullable=True)
```

- [ ] **Step 4: Registrar los modelos en `__init__.py`**

Abrir `backend/app/models/__init__.py` y añadir al final:

```python
from app.models.reintegro import CasoReintegro, Reca  # noqa: F401
```

- [ ] **Step 5: Correr los tests de modelo y verificar que pasan**

Run: `uv run pytest tests/test_reintegro_model.py -v`
Expected: `9 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/reintegro.py backend/app/models/__init__.py backend/tests/test_reintegro_model.py
git commit -m "feat(reintegro): modelos CasoReintegro y Reca (portable, Identity, tipos genéricos)"
```

---

## Task 3: Migración CEPA-040 — tabla `caso_reintegro`

**Files:**
- Create: `backend/migrations/versions/0040_crear_caso_reintegro.py`

- [ ] **Step 1: Verificar la última revisión activa antes de escribir la migración**

Run: `uv run alembic heads`
Expected: una sola cabeza — apunta a la última migración de EPIC-01 (probablemente `0015` o similar, dependiendo del número que dejó EPIC-01 en `main`). Anotar ese valor; se usará como `down_revision`.

- [ ] **Step 2: Crear la migración**

Crear `backend/migrations/versions/0040_crear_caso_reintegro.py`:

```python
"""crear caso_reintegro (CEPA-040)

Revision ID: 0040
Revises: <RESOLVER: alembic heads>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0040"
down_revision = "<RESOLVER: alembic heads>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caso_reintegro",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("rut", sa.String(length=12), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("tipo_derivacion", sa.String(length=40), nullable=False),
        sa.Column("fecha_caso", sa.Date(), nullable=False),
        sa.Column("sexo", sa.String(length=10), nullable=False),
        sa.Column("edad", sa.BigInteger(), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("comuna", sa.String(length=80), nullable=True),
        sa.Column("rubro_empleador", sa.String(length=160), nullable=True),
        sa.Column("estado_reintegro", sa.String(length=20), nullable=False),
        sa.Column("fecha_reintegro", sa.Date(), nullable=True),
        sa.Column("remitido_isl", sa.Boolean(), nullable=False),
        sa.Column("alta_medica", sa.Boolean(), nullable=False),
        sa.Column("fecha_alta_medica", sa.Date(), nullable=True),
        sa.Column("alta_psicologica", sa.Boolean(), nullable=False),
        sa.Column("fecha_alta_psico", sa.Date(), nullable=True),
        sa.Column("tipo_alta", sa.String(length=20), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_caso_reintegro_ingreso"
        ),
    )
    op.create_index("ix_caso_reintegro_rut", "caso_reintegro", ["rut"])
    op.create_index("ix_caso_reintegro_ingr", "caso_reintegro", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_caso_reintegro_ingr", table_name="caso_reintegro")
    op.drop_index("ix_caso_reintegro_rut", table_name="caso_reintegro")
    op.drop_table("caso_reintegro")
```

> **Acción obligatoria antes del loop:** reemplazar `<RESOLVER: alembic heads>` por la revisión
> real obtenida en Step 1. Sin este cambio la migración fallará al cargar.

- [ ] **Step 3: Verificar la migración (upgrade + downgrade)**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: ambas direcciones sin error. La tabla `caso_reintegro` existe tras el último `upgrade head`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0040_crear_caso_reintegro.py
git commit -m "feat(reintegro): migración 0040 — tabla caso_reintegro (CEPA-040)"
```

---

## Task 4: Schemas Pydantic v2 del módulo de reintegro

**Files:**
- Create: `backend/app/schemas/reintegro.py`
- Test: inline en `backend/tests/test_reintegro_api.py` (los schemas se validan indirectamente a través de la API; los tests unitarios de validación van aquí)
- Test: `backend/tests/test_reintegro_schemas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reintegro_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.reintegro import CasoReintegroCreate


def _payload(**over):
    base = {
        "ingreso_id": 1,
        "rut": "12.345.678-5",
        "nombre": "Juan Pérez",
        "tipo_derivacion": "DIAT",
        "fecha_caso": "2026-06-10",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
    }
    base.update(over)
    return base


# TC-040-01: campos obligatorios completos — crea OK
def test_schema_valido_acepta_campos_obligatorios():
    obj = CasoReintegroCreate(**_payload())
    assert obj.rut == "123456785"  # normalizado por validador
    assert obj.nombre == "Juan Pérez"


# TC-040-03: RUT con DV inválido → ValidationError
def test_schema_rechaza_rut_invalido():
    with pytest.raises(ValidationError) as exc_info:
        CasoReintegroCreate(**_payload(rut="12.345.678-0"))
    assert "rut" in str(exc_info.value).lower()


# TC-040-04: campos obligatorios faltantes → ValidationError
def test_schema_rechaza_faltan_obligatorios():
    datos = _payload()
    del datos["sexo"]
    del datos["region"]
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**datos)


# TC-040-04 (bis): sexo y zona geográfica obligatorios (D5/D6)
def test_schema_exige_sexo_y_region():
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(sexo=None))
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(region=None))


# TC-040-04 (bis): tipo_derivacion fuera de lista cerrada D4 → ValidationError
def test_schema_rechaza_tipo_derivacion_invalido():
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(tipo_derivacion="SOCORRO"))


# TC-040-04 (bis): tipo_derivacion de la lista D4 → OK
def test_schema_acepta_tipo_derivacion_reingreso_fump():
    obj = CasoReintegroCreate(**_payload(tipo_derivacion="Reingreso FUMP"))
    assert obj.tipo_derivacion.value == "Reingreso FUMP"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reintegro_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.reintegro'`.

- [ ] **Step 3: Implementar los schemas**

Crear `backend/app/schemas/reintegro.py`:

```python
"""Schemas Pydantic v2 del módulo de Seguimiento de Reintegro (EPIC-04).

Convenciones:
- *Create  → payload de entrada (validaciones de negocio en campo).
- *Update  → patch parcial (todos los campos opcionales).
- *Read    → respuesta (from_attributes=True).
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.enums import TipoDerivacion
from app.domain.reintegro_enums import EstadoReintegro, TipoAlta, TipoReca
from app.util.rut import RutInvalidoError, normalizar_rut


# ── CEPA-040: Caso de reintegro ────────────────────────────────────────────

class CasoReintegroCreate(BaseModel):
    """Alta de caso de reintegro. Campos obligatorios según D5/D6."""

    ingreso_id: int
    rut: str
    nombre: str
    tipo_derivacion: TipoDerivacion
    fecha_caso: date
    sexo: str          # "F" / "M" / "otro" — igual que Sexo de EPIC-01
    edad: int
    region: str
    # opcionales
    comuna: str | None = None
    rubro_empleador: str | None = None

    @field_validator("rut")
    @classmethod
    def _rut_valido(cls, v: str) -> str:
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v!r}") from exc

    @field_validator("edad")
    @classmethod
    def _edad_positiva(cls, v: int) -> int:
        if v <= 0 or v > 130:
            raise ValueError("edad fuera de rango (1–130)")
        return v


class CasoReintegroUpdate(BaseModel):
    """Actualización parcial del caso (patch). Todos los campos son opcionales."""

    nombre: str | None = None
    tipo_derivacion: TipoDerivacion | None = None
    fecha_caso: date | None = None
    sexo: str | None = None
    edad: int | None = None
    region: str | None = None
    comuna: str | None = None
    rubro_empleador: str | None = None


class CasoReintegroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    rut: str
    nombre: str
    tipo_derivacion: TipoDerivacion
    fecha_caso: date
    sexo: str
    edad: int
    region: str
    comuna: str | None
    rubro_empleador: str | None
    estado_reintegro: EstadoReintegro
    fecha_reintegro: date | None
    remitido_isl: bool
    alta_medica: bool
    fecha_alta_medica: date | None
    alta_psicologica: bool
    fecha_alta_psico: date | None
    tipo_alta: TipoAlta | None
    observaciones: str | None


# ── CEPA-041: RECA y medidas correctivas ──────────────────────────────────

class RecaCreate(BaseModel):
    """Registro de RECA. Validaciones de coherencia temporal en el servicio."""

    fecha_reca: date
    tipo_reca: TipoReca
    numero_reca: str
    razon_social: str
    riesgos_calificados: str | None = None
    solicita_medidas: bool = False
    detalle_medidas: str | None = None
    fecha_medidas: date | None = None
    verifica_medidas: bool = False
    detalle_verificacion: str | None = None
    fecha_verificacion: date | None = None


class RecaUpdate(BaseModel):
    """Actualización parcial de la RECA."""

    fecha_reca: date | None = None
    tipo_reca: TipoReca | None = None
    numero_reca: str | None = None
    razon_social: str | None = None
    riesgos_calificados: str | None = None
    solicita_medidas: bool | None = None
    detalle_medidas: str | None = None
    fecha_medidas: date | None = None
    verifica_medidas: bool | None = None
    detalle_verificacion: str | None = None
    fecha_verificacion: date | None = None


class RecaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_reintegro_id: int
    fecha_reca: date
    tipo_reca: TipoReca
    numero_reca: str
    riesgos_calificados: str | None
    razon_social: str
    solicita_medidas: bool
    detalle_medidas: str | None
    fecha_medidas: date | None
    verifica_medidas: bool
    detalle_verificacion: str | None
    fecha_verificacion: date | None


# ── CEPA-042: Cierre / reintegro ──────────────────────────────────────────

class CierreReintegroUpdate(BaseModel):
    """Payload para actualizar el estado de reintegro y el cierre del caso.

    Las validaciones de coherencia temporal (fecha_reintegro >= fecha_reca,
    cierre requiere alta) se aplican en el servicio, no aquí.
    """

    estado_reintegro: EstadoReintegro
    fecha_reintegro: date | None = None
    remitido_isl: bool = False
    alta_medica: bool = False
    fecha_alta_medica: date | None = None
    alta_psicologica: bool = False
    fecha_alta_psico: date | None = None
    tipo_alta: TipoAlta | None = None
    observaciones: str | None = None
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_reintegro_schemas.py -v`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/reintegro.py backend/tests/test_reintegro_schemas.py
git commit -m "feat(reintegro): schemas Pydantic v2 — caso, RECA y cierre (CEPA-040/041/042)"
```

---

## Task 5: Migración CEPA-041 — tabla `reca`

**Files:**
- Create: `backend/migrations/versions/0041_crear_reca.py`

- [ ] **Step 1: Crear la migración**

Crear `backend/migrations/versions/0041_crear_reca.py`:

```python
"""crear reca (CEPA-041)

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reca",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("caso_reintegro_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_reca", sa.Date(), nullable=False),
        sa.Column("tipo_reca", sa.String(length=10), nullable=False),
        sa.Column("numero_reca", sa.String(length=40), nullable=False),
        sa.Column("riesgos_calificados", sa.Text(), nullable=True),
        sa.Column("razon_social", sa.String(length=160), nullable=False),
        sa.Column("solicita_medidas", sa.Boolean(), nullable=False),
        sa.Column("detalle_medidas", sa.Text(), nullable=True),
        sa.Column("fecha_medidas", sa.Date(), nullable=True),
        sa.Column("verifica_medidas", sa.Boolean(), nullable=False),
        sa.Column("detalle_verificacion", sa.Text(), nullable=True),
        sa.Column("fecha_verificacion", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["caso_reintegro_id"],
            ["caso_reintegro.id"],
            name="fk_reca_caso_reintegro",
        ),
        sa.UniqueConstraint(
            "numero_reca", "caso_reintegro_id", name="uq_reca_numero_caso"
        ),
    )
    op.create_index("ix_reca_caso_reintegro_id", "reca", ["caso_reintegro_id"])


def downgrade() -> None:
    op.drop_index("ix_reca_caso_reintegro_id", table_name="reca")
    op.drop_table("reca")
```

- [ ] **Step 2: Verificar la migración**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: sin error; tras el último `upgrade head` las tablas `caso_reintegro` y `reca` existen.

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/versions/0041_crear_reca.py
git commit -m "feat(reintegro): migración 0041 — tabla reca (CEPA-041)"
```

---

## Task 6: Servicio de reintegro (lógica de negocio)

Concentra todas las validaciones de reglas de negocio: coherencia temporal RECA/medidas/reintegro, unicidad de RECA por caso, validaciones de cierre.

**Files:**
- Create: `backend/app/services/reintegro.py`
- Test unitario de servicio: `backend/tests/test_reintegro_service.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reintegro_service.py`:

```python
"""Tests unitarios del servicio de reintegro — reglas de negocio puras."""

import datetime
import pytest
from fastapi import HTTPException

from app.services.reintegro import (
    validar_coherencia_reca,
    validar_coherencia_medidas,
    validar_coherencia_cierre,
)


# RN-3 CEPA-041: fecha_verificacion >= fecha_medidas >= fecha_reca
# TC-041-04: verificación anterior a medida → rechazado
def test_coherencia_medidas_rechaza_verificacion_anterior():
    fecha_reca = datetime.date(2026, 3, 1)
    fecha_medidas = datetime.date(2026, 3, 10)
    fecha_verificacion = datetime.date(2026, 3, 5)  # anterior a fecha_medidas
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_medidas(fecha_reca, fecha_medidas, fecha_verificacion)
    assert exc_info.value.status_code == 422


# TC-041-02: verificación posterior a medida → OK
def test_coherencia_medidas_acepta_verificacion_posterior():
    fecha_reca = datetime.date(2026, 3, 1)
    fecha_medidas = datetime.date(2026, 3, 10)
    fecha_verificacion = datetime.date(2026, 3, 25)
    # no lanza excepción
    validar_coherencia_medidas(fecha_reca, fecha_medidas, fecha_verificacion)


# RN-3 CEPA-041: fecha_medidas >= fecha_reca
def test_coherencia_medidas_rechaza_medida_anterior_a_reca():
    fecha_reca = datetime.date(2026, 3, 10)
    fecha_medidas = datetime.date(2026, 3, 5)   # anterior a RECA
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_medidas(fecha_reca, fecha_medidas, None)
    assert exc_info.value.status_code == 422


# RN-2 CEPA-041: solicita_medidas=True sin detalle o sin fecha → rechazado
def test_coherencia_reca_rechaza_medidas_sin_detalle():
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_reca(
            solicita_medidas=True,
            detalle_medidas=None,
            fecha_medidas=None,
        )
    assert exc_info.value.status_code == 422


def test_coherencia_reca_rechaza_medidas_sin_fecha():
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_reca(
            solicita_medidas=True,
            detalle_medidas="Ajuste ergonómico",
            fecha_medidas=None,
        )
    assert exc_info.value.status_code == 422


# RN-2 CEPA-041: solicita_medidas=True con detalle y fecha → OK
def test_coherencia_reca_acepta_medidas_completas():
    validar_coherencia_reca(
        solicita_medidas=True,
        detalle_medidas="Ajuste ergonómico",
        fecha_medidas=datetime.date(2026, 3, 10),
    )


# RN-1 CEPA-042: estado=total sin fecha_reintegro → rechazado (TC-042-03)
def test_coherencia_cierre_rechaza_total_sin_fecha():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=None,
            fecha_reca=datetime.date(2026, 4, 1),
            alta_medica=True,
            alta_psicologica=False,
            tipo_alta="terapeutica",
        )
    assert exc_info.value.status_code == 422


# RN-2 CEPA-042: fecha_reintegro < fecha_reca → rechazado (TC-042-04)
def test_coherencia_cierre_rechaza_fecha_reintegro_anterior_a_reca():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=datetime.date(2026, 3, 15),
            fecha_reca=datetime.date(2026, 4, 1),
            alta_medica=True,
            alta_psicologica=False,
            tipo_alta="terapeutica",
        )
    assert exc_info.value.status_code == 422


# RN-4 CEPA-042: reintegro total sin alta ni tipo_alta → rechazado (TC-042-05)
def test_coherencia_cierre_rechaza_total_sin_alta():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=datetime.date(2026, 5, 30),
            fecha_reca=datetime.date(2026, 4, 1),
            alta_medica=False,
            alta_psicologica=False,
            tipo_alta=None,
        )
    assert exc_info.value.status_code == 422


# TC-042-01: reintegro total con todo completo → OK
def test_coherencia_cierre_acepta_total_completo():
    from app.domain.reintegro_enums import EstadoReintegro
    validar_coherencia_cierre(
        estado=EstadoReintegro.TOTAL,
        fecha_reintegro=datetime.date(2026, 5, 30),
        fecha_reca=datetime.date(2026, 4, 1),
        alta_medica=True,
        alta_psicologica=False,
        tipo_alta="terapeutica",
    )


# TC-042-02: reintegro parcial sin fecha → permitido (caso abierto)
def test_coherencia_cierre_acepta_parcial_sin_fecha():
    from app.domain.reintegro_enums import EstadoReintegro
    validar_coherencia_cierre(
        estado=EstadoReintegro.PARCIAL,
        fecha_reintegro=None,
        fecha_reca=None,
        alta_medica=False,
        alta_psicologica=False,
        tipo_alta=None,
    )
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reintegro_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.reintegro'`.

- [ ] **Step 3: Implementar el servicio**

Crear `backend/app/services/reintegro.py`:

```python
"""Lógica de negocio del módulo de Seguimiento de Reintegro (EPIC-04).

Las funciones validar_* lanzan HTTPException 422 cuando se viola una regla
de negocio, de modo que el router las puede llamar directamente y FastAPI
convertirá la excepción en una respuesta 422 JSON sin código adicional.
"""

import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.reintegro_enums import EstadoReintegro
from app.models.reintegro import CasoReintegro, Reca
from app.schemas.reintegro import (
    CasoReintegroCreate,
    CasoReintegroUpdate,
    CierreReintegroUpdate,
    RecaCreate,
    RecaUpdate,
)


# ── Validaciones puras (sin sesión) ───────────────────────────────────────

def validar_coherencia_reca(
    solicita_medidas: bool,
    detalle_medidas: str | None,
    fecha_medidas: datetime.date | None,
) -> None:
    """RN-2 CEPA-041: si solicita_medidas=True, detalle y fecha son obligatorios."""
    if solicita_medidas:
        if not detalle_medidas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="detalle_medidas es obligatorio cuando solicita_medidas=True (RN-2).",
            )
        if fecha_medidas is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="fecha_medidas es obligatoria cuando solicita_medidas=True (RN-2).",
            )


def validar_coherencia_medidas(
    fecha_reca: datetime.date,
    fecha_medidas: datetime.date | None,
    fecha_verificacion: datetime.date | None,
) -> None:
    """RN-3 CEPA-041: fecha_verificacion >= fecha_medidas >= fecha_reca."""
    if fecha_medidas is not None and fecha_medidas < fecha_reca:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"fecha_medidas ({fecha_medidas}) debe ser igual o posterior "
                f"a fecha_reca ({fecha_reca}) (RN-3)."
            ),
        )
    if fecha_verificacion is not None and fecha_medidas is not None:
        if fecha_verificacion < fecha_medidas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"fecha_verificacion ({fecha_verificacion}) debe ser igual o posterior "
                    f"a fecha_medidas ({fecha_medidas}) (RN-3)."
                ),
            )


def validar_coherencia_cierre(
    estado: EstadoReintegro,
    fecha_reintegro: datetime.date | None,
    fecha_reca: datetime.date | None,
    alta_medica: bool,
    alta_psicologica: bool,
    tipo_alta: str | None,
) -> None:
    """Valida las reglas de negocio del cierre del caso (CEPA-042 RN-1..4).

    - RN-1: estado=total exige fecha_reintegro.
    - RN-2: fecha_reintegro >= fecha_reca (cuando fecha_reca disponible).
    - RN-4: reintegro total requiere al menos una alta y tipo_alta.
    """
    if estado == EstadoReintegro.TOTAL:
        if fecha_reintegro is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="fecha_reintegro es obligatoria cuando estado=total (RN-1).",
            )
        if fecha_reca is not None and fecha_reintegro < fecha_reca:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"fecha_reintegro ({fecha_reintegro}) no puede ser anterior "
                    f"a fecha_reca ({fecha_reca}) (RN-2)."
                ),
            )
        if not alta_medica and not alta_psicologica:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para cerrar el caso se requiere al menos alta_medica o alta_psicologica (RN-4).",
            )
        if not tipo_alta:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tipo_alta es obligatorio para cerrar el caso (RN-4).",
            )
    # estado=parcial o pendiente: no hay restricciones adicionales aquí


# ── Operaciones con sesión ────────────────────────────────────────────────

def crear_caso_reintegro(db: Session, data: CasoReintegroCreate) -> CasoReintegro:
    """Crea el caso de reintegro vinculado al ingreso (CEPA-040)."""
    caso = CasoReintegro(
        ingreso_id=data.ingreso_id,
        rut=data.rut,
        nombre=data.nombre,
        tipo_derivacion=data.tipo_derivacion.value,
        fecha_caso=data.fecha_caso,
        sexo=data.sexo,
        edad=data.edad,
        region=data.region,
        comuna=data.comuna,
        rubro_empleador=data.rubro_empleador,
    )
    db.add(caso)
    db.flush()
    return caso


def actualizar_caso_reintegro(
    db: Session, caso: CasoReintegro, data: CasoReintegroUpdate
) -> CasoReintegro:
    """Actualización parcial de datos del caso (CEPA-040 CA-1)."""
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if campo == "tipo_derivacion" and valor is not None:
            setattr(caso, campo, valor.value if hasattr(valor, "value") else valor)
        else:
            setattr(caso, campo, valor)
    db.flush()
    return caso


def _obtener_caso_o_404(db: Session, caso_id: int) -> CasoReintegro:
    caso = db.get(CasoReintegro, caso_id)
    if caso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso de reintegro {caso_id} no encontrado.",
        )
    return caso


def crear_reca(db: Session, caso_id: int, data: RecaCreate) -> Reca:
    """Registra la RECA asociada al caso (CEPA-041).

    Valida:
    - Unicidad de numero_reca por caso (RN-1 CEPA-041).
    - Coherencia reca/medidas (validar_coherencia_reca + validar_coherencia_medidas).
    """
    caso = _obtener_caso_o_404(db, caso_id)

    # Unicidad numero_reca por caso (RN-1)
    existente = db.execute(
        select(Reca).where(
            Reca.caso_reintegro_id == caso_id,
            Reca.numero_reca == data.numero_reca,
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una RECA con número {data.numero_reca!r} en este caso (RN-1).",
        )

    validar_coherencia_reca(data.solicita_medidas, data.detalle_medidas, data.fecha_medidas)
    if data.fecha_medidas is not None:
        validar_coherencia_medidas(data.fecha_reca, data.fecha_medidas, data.fecha_verificacion)

    reca = Reca(
        caso_reintegro_id=caso.id,
        fecha_reca=data.fecha_reca,
        tipo_reca=data.tipo_reca.value,
        numero_reca=data.numero_reca,
        riesgos_calificados=data.riesgos_calificados,
        razon_social=data.razon_social,
        solicita_medidas=data.solicita_medidas,
        detalle_medidas=data.detalle_medidas,
        fecha_medidas=data.fecha_medidas,
        verifica_medidas=data.verifica_medidas,
        detalle_verificacion=data.detalle_verificacion,
        fecha_verificacion=data.fecha_verificacion,
    )
    db.add(reca)
    db.flush()
    return reca


def actualizar_reca(db: Session, reca: Reca, data: RecaUpdate) -> Reca:
    """Actualización parcial de la RECA (CEPA-041)."""
    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        if campo == "tipo_reca" and valor is not None:
            setattr(reca, campo, valor.value if hasattr(valor, "value") else valor)
        else:
            setattr(reca, campo, valor)
    # Re-validar tras actualización
    validar_coherencia_reca(
        reca.solicita_medidas, reca.detalle_medidas, reca.fecha_medidas
    )
    if reca.fecha_medidas is not None:
        validar_coherencia_medidas(
            reca.fecha_reca, reca.fecha_medidas, reca.fecha_verificacion
        )
    db.flush()
    return reca


def cerrar_caso_reintegro(
    db: Session, caso: CasoReintegro, data: CierreReintegroUpdate
) -> CasoReintegro:
    """Registra el estado de reintegro y el cierre del caso (CEPA-042).

    Obtiene la fecha_reca desde la RECA asociada (si existe) para la
    validación de coherencia temporal.
    """
    fecha_reca = caso.reca.fecha_reca if caso.reca else None
    validar_coherencia_cierre(
        estado=data.estado_reintegro,
        fecha_reintegro=data.fecha_reintegro,
        fecha_reca=fecha_reca,
        alta_medica=data.alta_medica,
        alta_psicologica=data.alta_psicologica,
        tipo_alta=data.tipo_alta.value if data.tipo_alta else None,
    )
    caso.estado_reintegro = data.estado_reintegro.value
    caso.fecha_reintegro = data.fecha_reintegro
    caso.remitido_isl = data.remitido_isl
    caso.alta_medica = data.alta_medica
    caso.fecha_alta_medica = data.fecha_alta_medica
    caso.alta_psicologica = data.alta_psicologica
    caso.fecha_alta_psico = data.fecha_alta_psico
    caso.tipo_alta = data.tipo_alta.value if data.tipo_alta else None
    caso.observaciones = data.observaciones
    db.flush()
    return caso
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_reintegro_service.py -v`
Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reintegro.py backend/tests/test_reintegro_service.py
git commit -m "feat(reintegro): servicio con validaciones de negocio (RN-1..4 CEPA-040/041/042)"
```

---

## Task 7: Router y API de CEPA-040 — Caso de reintegro

**Files:**
- Create: `backend/app/routers/reintegros.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reintegro_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reintegro_api.py`:

```python
"""Tests de integración — CEPA-040: Datos del caso de reintegro."""

import pytest


def _ingreso_fixture(as_admin):
    """Crea un ingreso real en la BD de tests para usar como FK."""
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "12.345.678-5",
            "nombre": "Juan Pérez",
            "sexo": "M",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "Trastorno adaptativo",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r.status_code == 201, f"Fallo al crear ingreso fixture: {r.text}"
    return r.json()["id"]


def _payload_caso(ingreso_id: int, **over):
    base = {
        "ingreso_id": ingreso_id,
        "rut": "12.345.678-5",
        "nombre": "Juan Pérez",
        "tipo_derivacion": "DIAT",
        "fecha_caso": "2026-06-10",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
    }
    base.update(over)
    return base


# TC-040-01: crear caso con RUT existente — datos obligatorios completos
def test_crear_caso_reintegro_exitoso(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["rut"] == "123456785"  # normalizado
    assert cuerpo["estado_reintegro"] == "pendiente"
    assert cuerpo["ingreso_id"] == ingreso_id


# TC-040-01 (bis): caso vinculado al ingreso y visible en GET
def test_caso_creado_es_visible(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    create_r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    caso_id = create_r.json()["id"]
    get_r = as_admin.get(f"/api/v1/reintegros/{caso_id}")
    assert get_r.status_code == 200
    assert get_r.json()["id"] == caso_id


# TC-040-02: tipo de derivación válido de la lista D4
def test_tipo_derivacion_reingreso_fump(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, tipo_derivacion="Reingreso FUMP"),
    )
    assert r.status_code == 201
    assert r.json()["tipo_derivacion"] == "Reingreso FUMP"


# TC-040-03: RUT con DV inválido → 422
def test_rut_invalido_rechazado(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, rut="12.345.678-0"),
    )
    assert r.status_code == 422
    assert "rut" in r.text.lower()


# TC-040-04: campos obligatorios faltantes → 422
def test_campos_obligatorios_faltantes(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    datos = _payload_caso(ingreso_id)
    del datos["sexo"]
    del datos["region"]
    r = as_admin.post("/api/v1/reintegros", json=datos)
    assert r.status_code == 422


# TC-040-04 (bis): tipo_derivacion inválido ("SOCORRO" no es válido en D4)
def test_tipo_derivacion_invalido_rechazado(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post(
        "/api/v1/reintegros",
        json=_payload_caso(ingreso_id, tipo_derivacion="SOCORRO"),
    )
    assert r.status_code == 422


# TC-040-06: Auditor no puede crear → 403
def test_auditor_no_puede_crear(as_auditor):
    r = as_auditor.post(
        "/api/v1/reintegros",
        json={"ingreso_id": 1, "rut": "12.345.678-5", "nombre": "X",
              "tipo_derivacion": "DIAT", "fecha_caso": "2026-06-10",
              "sexo": "M", "edad": 40, "region": "Maule"},
    )
    assert r.status_code == 403


# Coordinacion puede crear
def test_coordinacion_puede_crear(as_coordinacion):
    ingreso_id = _ingreso_fixture(as_coordinacion)
    r = as_coordinacion.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    assert r.status_code == 201


# Auditor puede leer (solo lectura)
def test_auditor_puede_leer(as_admin, as_auditor):
    ingreso_id = _ingreso_fixture(as_admin)
    create_r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    caso_id = create_r.json()["id"]
    r = as_auditor.get(f"/api/v1/reintegros/{caso_id}")
    assert r.status_code == 200


# Listar por ingreso_id
def test_listar_casos_por_ingreso(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    r = as_admin.get("/api/v1/reintegros", params={"ingreso_id": ingreso_id})
    assert r.status_code == 200
    assert len(r.json()) >= 1


# RN-5: auditoría registrada (verificación indirecta — el endpoint no falla)
def test_operacion_create_no_falla_sin_auditoria_error(as_admin):
    ingreso_id = _ingreso_fixture(as_admin)
    r = as_admin.post("/api/v1/reintegros", json=_payload_caso(ingreso_id))
    assert r.status_code == 201
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reintegro_api.py -v`
Expected: FAIL con `404 Not Found` (ruta `/api/v1/reintegros` inexistente).

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/reintegros.py`:

```python
"""Router del módulo de Seguimiento de Reintegro — /api/v1/reintegros (EPIC-04)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.reintegro import CasoReintegro, Reca
from app.schemas.reintegro import (
    CasoReintegroCreate,
    CasoReintegroRead,
    CasoReintegroUpdate,
    CierreReintegroUpdate,
    RecaCreate,
    RecaRead,
    RecaUpdate,
)
from app.services.reintegro import (
    _obtener_caso_o_404,
    actualizar_caso_reintegro,
    actualizar_reca,
    cerrar_caso_reintegro,
    crear_caso_reintegro,
    crear_reca,
)

router = APIRouter(prefix="/api/v1/reintegros", tags=["reintegros"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── CEPA-040: Caso de reintegro ────────────────────────────────────────────

@router.post(
    "",
    response_model=CasoReintegroRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_caso(
    payload: CasoReintegroCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = crear_caso_reintegro(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


@router.get(
    "",
    response_model=list[CasoReintegroRead],
    dependencies=[Depends(_reader)],
)
def listar_casos(
    ingreso_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CasoReintegroRead]:
    stmt = select(CasoReintegro)
    if ingreso_id is not None:
        stmt = stmt.where(CasoReintegro.ingreso_id == ingreso_id)
    return list(db.scalars(stmt.order_by(CasoReintegro.id)))


@router.get(
    "/{caso_id}",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_reader)],
)
def obtener_caso(
    caso_id: int,
    db: Session = Depends(get_db),
) -> CasoReintegroRead:
    return _obtener_caso_o_404(db, caso_id)


@router.patch(
    "/{caso_id}",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def actualizar_caso(
    caso_id: int,
    payload: CasoReintegroUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = _obtener_caso_o_404(db, caso_id)
    caso = actualizar_caso_reintegro(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


# ── CEPA-041: RECA y medidas correctivas ──────────────────────────────────

@router.post(
    "/{caso_id}/reca",
    response_model=RecaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_reca_endpoint(
    caso_id: int,
    payload: RecaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecaRead:
    reca = crear_reca(db, caso_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reca",
        entity_id=str(reca.id),
    )
    db.commit()
    db.refresh(reca)
    return reca


@router.get(
    "/{caso_id}/reca",
    response_model=RecaRead,
    dependencies=[Depends(_reader)],
)
def obtener_reca(
    caso_id: int,
    db: Session = Depends(get_db),
) -> RecaRead:
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.reca is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El caso {caso_id} no tiene RECA registrada.",
        )
    return caso.reca


@router.patch(
    "/{caso_id}/reca",
    response_model=RecaRead,
    dependencies=[Depends(_writer)],
)
def actualizar_reca_endpoint(
    caso_id: int,
    payload: RecaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecaRead:
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.reca is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El caso {caso_id} no tiene RECA registrada.",
        )
    reca = actualizar_reca(db, caso.reca, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="reca",
        entity_id=str(reca.id),
    )
    db.commit()
    db.refresh(reca)
    return reca


# ── CEPA-042: Cierre / reintegro ──────────────────────────────────────────

@router.patch(
    "/{caso_id}/cierre",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def registrar_cierre(
    caso_id: int,
    payload: CierreReintegroUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = _obtener_caso_o_404(db, caso_id)
    caso = cerrar_caso_reintegro(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso
```

- [ ] **Step 4: Conectar el router en `app/main.py`**

Añadir en `backend/app/main.py` (conservando lo existente):

```python
from app.routers import reintegros

app.include_router(reintegros.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reintegro_api.py -v`
Expected: `10 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/reintegros.py backend/app/main.py backend/tests/test_reintegro_api.py
git commit -m "feat(reintegro): router /api/v1/reintegros CRUD caso de reintegro (CEPA-040)"
```

---

## Task 8: Tests de integración API — CEPA-041 (RECA y medidas)

**Files:**
- Test: `backend/tests/test_reca_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reca_api.py`:

```python
"""Tests de integración — CEPA-041: Proceso RECA y medidas correctivas."""


def _crear_caso(as_admin) -> int:
    """Crea ingreso + caso de reintegro y devuelve caso_id."""
    ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "7.876.543-K",
            "nombre": "Ana Torres",
            "sexo": "F",
            "edad": 35,
            "region": "Maule",
            "diagnostico": "EP lumbar",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-03-01",
        },
    )
    assert ing.status_code == 201
    ingreso_id = ing.json()["id"]
    caso = as_admin.post(
        "/api/v1/reintegros",
        json={
            "ingreso_id": ingreso_id,
            "rut": "7.876.543-K",
            "nombre": "Ana Torres",
            "tipo_derivacion": "DIEP",
            "fecha_caso": "2026-03-01",
            "sexo": "F",
            "edad": 35,
            "region": "Maule",
        },
    )
    assert caso.status_code == 201
    return caso.json()["id"]


def _payload_reca(**over):
    base = {
        "fecha_reca": "2026-03-05",
        "tipo_reca": "EP",
        "numero_reca": "2026-0042",
        "razon_social": "Empresa Ltda.",
        "riesgos_calificados": "Carga manual, postura forzada",
        "solicita_medidas": False,
    }
    base.update(over)
    return base


# TC-041-01: crear RECA con datos completos → asociada al caso
def test_crear_reca_exitoso(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["numero_reca"] == "2026-0042"
    assert cuerpo["caso_reintegro_id"] == caso_id


# TC-041-01 (bis): RECA visible desde GET y en lectura de auditor
def test_reca_visible_y_auditor_puede_leer(as_admin, as_auditor):
    caso_id = _crear_caso(as_admin)
    as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    r = as_auditor.get(f"/api/v1/reintegros/{caso_id}/reca")
    assert r.status_code == 200
    assert r.json()["numero_reca"] == "2026-0042"


# TC-041-02: ciclo de medida completo (fecha medida < fecha verificación)
def test_ciclo_medidas_completo(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas="Reducir carga manual",
            fecha_medidas="2026-03-10",
            verifica_medidas=True,
            detalle_verificacion="Medida implementada",
            fecha_verificacion="2026-03-25",
        ),
    )
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["verifica_medidas"] is True
    assert cuerpo["fecha_verificacion"] == "2026-03-25"


# TC-041-03: solicita_medidas=True sin detalle → 422
def test_medidas_sin_detalle_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas=None,
            fecha_medidas="2026-03-10",
        ),
    )
    assert r.status_code == 422


# TC-041-03 (bis): solicita_medidas=True sin fecha_medidas → 422
def test_medidas_sin_fecha_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas="Ajuste puesto",
            fecha_medidas=None,
        ),
    )
    assert r.status_code == 422


# TC-041-04: verificación anterior a medida → 422
def test_verificacion_anterior_a_medida_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas="Ajuste puesto",
            fecha_medidas="2026-03-10",
            verifica_medidas=True,
            detalle_verificacion="ok",
            fecha_verificacion="2026-03-05",  # anterior a fecha_medidas
        ),
    )
    assert r.status_code == 422


# TC-041-05: número de RECA duplicado → 409
def test_numero_reca_duplicado_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    r = as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    assert r.status_code == 409


# TC-041-06: Auditor no puede editar medidas → 403
def test_auditor_no_puede_crear_reca(as_auditor):
    r = as_auditor.post(
        "/api/v1/reintegros/1/reca",
        json=_payload_reca(),
    )
    assert r.status_code == 403


# Actualizar medidas via PATCH
def test_actualizar_reca_patch(as_admin):
    caso_id = _crear_caso(as_admin)
    as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/reca",
        json={"riesgos_calificados": "Actualizado"},
    )
    assert r.status_code == 200
    assert r.json()["riesgos_calificados"] == "Actualizado"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reca_api.py -v`
Expected: FAIL con `404` (el endpoint `/api/v1/reintegros/{caso_id}/reca` no existe todavía — Task 7 lo añade; si Task 7 ya fue ejecutada, el fallo debería ser un assertion error concreto, no 404).

> **Nota:** este test se ejecuta DESPUÉS de Task 7. Si Task 7 ya está completa, correr directamente y verificar que pasan.

- [ ] **Step 3: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_reca_api.py -v`
Expected: `8 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_reca_api.py
git commit -m "test(reintegro): integración API RECA y medidas correctivas (CEPA-041)"
```

---

## Task 9: Tests de integración API — CEPA-042 (Reintegro y cierre)

**Files:**
- Test: `backend/tests/test_reintegro_cierre_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reintegro_cierre_api.py`:

```python
"""Tests de integración — CEPA-042: Reintegro y cierre del caso."""


def _caso_con_reca(as_admin) -> int:
    """Crea ingreso, caso de reintegro y RECA; devuelve caso_id."""
    ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "14.963.452-5",
            "nombre": "Pedro Soto",
            "sexo": "M",
            "edad": 45,
            "region": "Biobío",
            "diagnostico": "DIAT rodilla",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-04-01",
        },
    )
    assert ing.status_code == 201
    caso = as_admin.post(
        "/api/v1/reintegros",
        json={
            "ingreso_id": ing.json()["id"],
            "rut": "14.963.452-5",
            "nombre": "Pedro Soto",
            "tipo_derivacion": "DIAT",
            "fecha_caso": "2026-04-01",
            "sexo": "M",
            "edad": 45,
            "region": "Biobío",
        },
    )
    assert caso.status_code == 201
    caso_id = caso.json()["id"]
    reca = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json={
            "fecha_reca": "2026-04-05",
            "tipo_reca": "AT",
            "numero_reca": "2026-AT-001",
            "razon_social": "Empresa SA",
            "solicita_medidas": False,
        },
    )
    assert reca.status_code == 201
    return caso_id


# TC-042-01: reintegro total con todo completo → caso cerrado
def test_reintegro_total_cierre_exitoso(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "remitido_isl": True,
            "alta_medica": True,
            "fecha_alta_medica": "2026-05-28",
            "alta_psicologica": False,
            "tipo_alta": "terapeutica",
            "observaciones": "Alta sin restricciones",
        },
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado_reintegro"] == "total"
    assert cuerpo["remitido_isl"] is True
    assert cuerpo["tipo_alta"] == "terapeutica"


# TC-042-01 (bis): estado reflejado en GET y auditor puede leer
def test_cierre_total_visible_por_auditor(as_admin, as_auditor):
    caso_id = _caso_con_reca(as_admin)
    as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "alta_medica": True,
            "tipo_alta": "terapeutica",
        },
    )
    r = as_auditor.get(f"/api/v1/reintegros/{caso_id}")
    assert r.status_code == 200
    assert r.json()["estado_reintegro"] == "total"


# TC-042-02: reintegro parcial sin fecha → guardado, caso abierto
def test_reintegro_parcial_sin_fecha(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={"estado_reintegro": "parcial"},
    )
    assert r.status_code == 200
    assert r.json()["estado_reintegro"] == "parcial"
    assert r.json()["fecha_reintegro"] is None


# TC-042-03: estado=total sin fecha_reintegro → 422
def test_total_sin_fecha_rechazado(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "alta_medica": True,
            "tipo_alta": "terapeutica",
        },
    )
    assert r.status_code == 422


# TC-042-04: fecha_reintegro anterior a fecha_reca → 422
def test_fecha_reintegro_anterior_a_reca_rechazado(as_admin):
    caso_id = _caso_con_reca(as_admin)
    # fecha_reca = 2026-04-05 (creada en _caso_con_reca)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-03-15",  # anterior a fecha_reca 2026-04-05
            "alta_medica": True,
            "tipo_alta": "terapeutica",
        },
    )
    assert r.status_code == 422


# TC-042-05: reintegro total sin alta ni tipo_alta → 422
def test_total_sin_alta_rechazado(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "alta_medica": False,
            "alta_psicologica": False,
        },
    )
    assert r.status_code == 422


# TC-042-06: Auditor no puede modificar estado de reintegro → 403
def test_auditor_no_puede_cerrar(as_auditor):
    r = as_auditor.patch(
        "/api/v1/reintegros/1/cierre",
        json={"estado_reintegro": "total", "fecha_reintegro": "2026-05-30",
              "alta_medica": True, "tipo_alta": "terapeutica"},
    )
    assert r.status_code == 403


# remitido_isl=True → queda disponible para reporte
def test_remitido_isl_persiste(as_admin):
    caso_id = _caso_con_reca(as_admin)
    as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "remitido_isl": True,
            "alta_medica": True,
            "tipo_alta": "medica",
        },
    )
    r = as_admin.get(f"/api/v1/reintegros/{caso_id}")
    assert r.json()["remitido_isl"] is True
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reintegro_cierre_api.py -v`
Expected: FAIL con `404` o assertion errors (depende de si Task 7 ya implementó el endpoint `/cierre`).

- [ ] **Step 3: Verificar que pasa (el endpoint `/cierre` está en Task 7)**

Run: `uv run pytest tests/test_reintegro_cierre_api.py -v`
Expected: `8 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_reintegro_cierre_api.py
git commit -m "test(reintegro): integración API reintegro y cierre del caso (CEPA-042)"
```

---

## Task 10: Suite completa + verificación final

**Files:** ninguno nuevo.

- [ ] **Step 1: Correr la suite completa**

Run: `uv run pytest -v`
Expected: todos los tests pasan (incluyendo los de EPIC-00 y EPIC-01 que no deben haber regresado).

- [ ] **Step 2: Lint**

Run: `uv run ruff check .`
Expected: sin errores.

- [ ] **Step 3: Verificar migración completa desde cero**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: las tres migraciones de EPIC-04 (`0040`, `0041`) aplican en orden sin error.

- [ ] **Step 4: Smoke manual de los endpoints**

Run: `uv run uvicorn app.main:app` y en otra terminal:
```bash
# Verificar que la documentación OpenAPI incluye los endpoints de reintegro
curl -s localhost:8000/openapi.json | python3 -c "
import json,sys
paths = json.load(sys.stdin)['paths']
for p in paths:
    if 'reintegro' in p:
        print(p)
"
```
Expected: imprime `/api/v1/reintegros`, `/api/v1/reintegros/{caso_id}`, `/api/v1/reintegros/{caso_id}/reca`, `/api/v1/reintegros/{caso_id}/cierre`. Detener con Ctrl-C.

- [ ] **Step 5: Commit final (si quedó algo sin commitear)**

```bash
git add -A
git commit -m "chore(reintegro): EPIC-04 completa — caso, RECA, cierre, tests verdes" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Tasks que la implementan |
|----------|--------------------------|
| **CEPA-040** Datos del caso de reintegro | Task 1 (Enums), Task 2 (Modelos), Task 3 (Migración 0040), Task 4 (Schemas), Task 6 (Servicio), Task 7 (Router + API), Task 10 (suite) |
| **CEPA-041** Proceso RECA y medidas correctivas | Task 1 (Enums), Task 2 (Modelos), Task 4 (Schemas), Task 5 (Migración 0041), Task 6 (Servicio: `validar_coherencia_reca`, `validar_coherencia_medidas`, `crear_reca`, `actualizar_reca`), Task 7 (Router endpoints `/reca`), Task 8 (tests integración) |
| **CEPA-042** Reintegro y cierre del caso | Task 1 (Enums), Task 2 (Modelos: columnas cierre en `caso_reintegro`), Task 4 (Schemas `CierreReintegroUpdate`), Task 6 (Servicio: `validar_coherencia_cierre`, `cerrar_caso_reintegro`), Task 7 (Router endpoint `/cierre`), Task 9 (tests integración) |

### Mapa TC → test

| TC | Test | Task |
|----|------|------|
| TC-040-01 | `test_crear_caso_reintegro_exitoso`, `test_caso_creado_es_visible` | Task 7 |
| TC-040-02 | `test_tipo_derivacion_reingreso_fump` | Task 7 |
| TC-040-03 | `test_rut_invalido_rechazado`, `test_schema_rechaza_rut_invalido` | Tasks 4, 7 |
| TC-040-04 | `test_campos_obligatorios_faltantes`, `test_tipo_derivacion_invalido_rechazado`, `test_schema_rechaza_faltan_obligatorios`, `test_schema_exige_sexo_y_region` | Tasks 4, 7 |
| TC-040-05 | _(variante de TC-040-01 con folio histórico — cubierta a nivel de servicio: el caso se vincula al ingreso por `ingreso_id`)_ | Task 6 |
| TC-040-06 | `test_auditor_no_puede_crear` | Task 7 |
| TC-041-01 | `test_crear_reca_exitoso`, `test_reca_visible_y_auditor_puede_leer` | Task 8 |
| TC-041-02 | `test_ciclo_medidas_completo`, `test_actualizar_reca_patch` | Tasks 6, 8 |
| TC-041-03 | `test_medidas_sin_detalle_rechazado`, `test_medidas_sin_fecha_rechazado`, `test_coherencia_reca_rechaza_medidas_sin_detalle`, `test_coherencia_reca_rechaza_medidas_sin_fecha` | Tasks 6, 8 |
| TC-041-04 | `test_verificacion_anterior_a_medida_rechazado`, `test_coherencia_medidas_rechaza_verificacion_anterior` | Tasks 6, 8 |
| TC-041-05 | `test_numero_reca_duplicado_rechazado` | Task 8 |
| TC-041-06 | `test_auditor_no_puede_crear_reca` | Task 8 |
| TC-042-01 | `test_reintegro_total_cierre_exitoso`, `test_cierre_total_visible_por_auditor` | Task 9 |
| TC-042-02 | `test_reintegro_parcial_sin_fecha` | Task 9 |
| TC-042-03 | `test_total_sin_fecha_rechazado`, `test_coherencia_cierre_rechaza_total_sin_fecha` | Tasks 6, 9 |
| TC-042-04 | `test_fecha_reintegro_anterior_a_reca_rechazado`, `test_coherencia_cierre_rechaza_fecha_reintegro_anterior_a_reca` | Tasks 6, 9 |
| TC-042-05 | `test_total_sin_alta_rechazado`, `test_coherencia_cierre_rechaza_total_sin_alta` | Tasks 6, 9 |
| TC-042-06 | `test_auditor_no_puede_cerrar` | Task 9 |

---

## Notas de cierre

### Firmas a verificar contra el código real antes del loop

1. **`record_audit`** — verificar la firma exacta en `app/audit/service.py` (la firma usada aquí es `record_audit(db, actor=..., action=..., entity=..., entity_id=...)` conforme a las convenciones del plan de Fundación). Si EPIC-00 la implementó diferente, adaptar las llamadas en `app/routers/reintegros.py`.

2. **`get_current_user`** — verificar que devuelve un objeto con atributo `.username` (conforme a convenciones). Si el atributo es `.sub` o distinto, ajustar las referencias en el router.

3. **`require_role`** — verificar que acepta `*roles: str` y que los strings son exactamente `"Administrativo"`, `"Coordinacion"`, `"Auditor"` (case-sensitive, con tilde en Coordinación si aplica). Confirmar contra `app/auth/deps.py` de EPIC-00.

4. **`down_revision` en `0040_crear_caso_reintegro.py`** — se marcó como `<RESOLVER: alembic heads>`. Antes de correr el loop, ejecutar `uv run alembic heads` en el repo con EPIC-01 en `main` y sustituir el placeholder por la revisión real. Sin este cambio, `alembic upgrade head` fallará.

5. **Fixtures `as_admin`, `as_coordinacion`, `as_auditor`** — los tests asumen que `as_coordinacion` también puede crear ingresos (llama a `POST /api/v1/ingresos`). Verificar que EPIC-01 protege ese endpoint con `_writer = require_role("Administrativo", "Coordinacion")` (igual que aquí). Si no, el fixture `_ingreso_fixture(as_coordinacion)` fallará con 403.

6. **Tabla `ingreso`** — los tests llaman a `POST /api/v1/ingresos` para crear fixtures. Si el nombre del endpoint en EPIC-01 difiere (p. ej. `/api/v1/ingreso` sin plural), actualizar las llamadas en los helpers `_ingreso_fixture`, `_crear_caso`, `_caso_con_reca`.

### Decisiones de negocio abiertas (del spec)

- **Catálogo de `TipoReca`** (CEPA-041 nota): la lista provisional `{AT, EP}` es suficiente para tests pero debe confirmarse con Coordinación antes de la demo. Ampliar `TipoReca` en `app/domain/reintegro_enums.py` sin romper tests (solo añadir valores al Enum).

- **Catálogo de `rubro_empleador`** (CEPA-040 nota): el spec indica confirmar si es lista CIIU cerrada o texto libre. Actualmente se modela como `String(160)` (texto libre). Si se decide lista cerrada, añadir un Enum nuevo y ajustar el schema/columna; la migración solo necesita reducir el tamaño si se pasa a String(40), operación portable.

- **D11 — tipificación de altas**: pendiente confirmar con Coordinación si se usa una sola fecha de alta (última atención) o dos fechas separadas (médica + psicológica). El modelo actual usa dos fechas separadas (`fecha_alta_medica`, `fecha_alta_psico`). Si se simplifica a una sola, se requiere:
  1. Migración adicional (añadir `fecha_alta: Date`, eliminar las dos columnas o dejarlas nullable).
  2. Actualizar schemas y servicio.
  Esta decisión debe tomarse **antes del loop** para no acumular deuda de migración.

- **Integración con módulo de Licencias Médicas** (§7.7): el spec pregunta si `reintegro total` debe disparar automáticamente el cierre de la LM. No implementado aquí (EPIC-07 / Oleada 3). Cuando EPIC-07 esté listo, añadir un hook en `cerrar_caso_reintegro` o un evento de dominio.

- **Alertas de medidas correctivas próximas a vencer** (CEPA-041 nota): alinear con §7.11 / EPIC-10 (Oleada 4). No es scope de este plan.

### Convención de migración para este plan

Las migraciones tienen `revision_id` fijos (`0040`, `0041`). En un equipo con varias ramas activas puede haber conflicto de head. Si al ejecutar `alembic heads` aparecen dos heads, resolver con `alembic merge heads -m "merge"` antes de continuar.
