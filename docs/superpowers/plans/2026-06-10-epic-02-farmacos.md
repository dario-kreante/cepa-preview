# EPIC-02 — Gestión de Fármacos — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar el módulo de Gestión de Fármacos del CEPA — registro farmacológico vinculado al folio, esquema e historial clínico (incl. fármacos extra-sistema), gestión de recetas con alerta de revisión próxima, y seguimiento de tratamiento (disminución/cambio de esquema) — sobre la Fundación + EPIC-00 (auth/RBAC/auditoría) + EPIC-01 (paciente/ingreso/folio) ya en `main`. Cubre historias CEPA-020 a CEPA-023 con todos sus Criterios de Aceptación (Gherkin) y Test Cases (TC-020-XX … TC-023-XX).

**Architecture:** Se sigue el patrón de EPIC-01: modelos en `app/models/farmacos.py`, Enums de dominio extendiendo `app/domain/enums.py`, schemas Pydantic v2 en `app/schemas/farmacos.py`, lógica de negocio en `app/services/farmacos.py`, router `APIRouter` con prefijo `/api/v1/registro-farmacologico` en `app/routers/farmacos.py`, y una migración Alembic por historia que cree tablas. El sub-dominio de alertas de receta se implementa como endpoint utilitario (`POST /api/v1/recetas/alertas/generar`) que evalúa la ventana de 5 días y escribe en una tabla `alerta`; la entrega del canal in-app queda en EPIC-10. Los Enums de estado farmacológico se añaden al módulo compartido `app/domain/enums.py`. Toda escritura registra auditoría vía `record_audit`; escrituras exigen rol `Administrativo`/`Coordinacion`; `Auditor` solo lectura.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos, `Identity`/`BigInteger`, `DateTime(timezone=True)`), Alembic, Pydantic v2, pytest contra **Postgres real** (`cepa_test`). Importa de EPIC-00: `app.auth.deps.{get_current_user,require_role}`, `app.audit.service.record_audit`. Importa de EPIC-01: modelos `Ingreso` (FK), enum `EstadoCaso`. Fixtures de conftest: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`, `action ∈ {CREATE, UPDATE, DELETE}`.
- `from app.models.ingreso import Ingreso` — FK a la tabla `ingreso` de EPIC-01.
- Fixtures de EPIC-00: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención RBAC usada en todos los routers de esta épica:**
```python
from app.auth.deps import get_current_user, require_role

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")
```

---

## Convenciones de modelado de esta épica

- **PK subrogada:** `id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)`.
- **Fechas/tiempos:** `DateTime(timezone=True)` con helper `_utcnow()` declarado localmente en cada modelo.
- **Fechas de calendario sin hora** (emisión, revisión, envío de receta): `Date`.
- **Listas cerradas** (estados, banderas como texto): Enums Python `str, Enum`; columna `String(40)`; validación en Pydantic. Nunca tipos enum del motor.
- **Booleanos** (bandera disminución, bandera cambio de esquema, fármaco extra-sistema): `Boolean`.
- **Identificadores tabla/columna:** minúscula y ≤30 caracteres (obligatorio portabilidad D15).
- **Fármacos extra-sistema (D7):** campo `Boolean` `extra_sistema` en la tabla de indicaciones de esquema.

Tablas nuevas que crea esta épica: `reg_farmacologico`, `esquema_indicacion`, `receta`, `seguim_tratamiento`, `alerta`.

---

## Task 1: Enums de dominio farmacológico

Extiende `app/domain/enums.py` con los estados de caso farmacológico que necesitan los modelos de esta épica. No se crean archivos nuevos: se añaden al módulo compartido que ya existe desde EPIC-01.

**Files:**
- Modify: `backend/app/domain/enums.py`
- Test: `backend/tests/test_farmacos_enums.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_enums.py`:

```python
from app.domain.enums import EstadoFarmacologico, FrecuenciaFarmaco


def test_estados_farmacologicos():
    valores = {e.value for e in EstadoFarmacologico}
    assert valores == {"activo", "suspendido", "completado", "pendiente"}


def test_frecuencias_farmaco():
    valores = {f.value for f in FrecuenciaFarmaco}
    assert "c/24h" in valores
    assert "c/12h" in valores
    assert "c/8h" in valores
    assert "c/6h" in valores
    assert "semanal" in valores
    assert "otro" in valores
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_enums.py -v`
Expected: FAIL con `ImportError: cannot import name 'EstadoFarmacologico' from 'app.domain.enums'`.

- [ ] **Step 3: Añadir los Enums en `app/domain/enums.py`**

Abrir `backend/app/domain/enums.py` y **agregar al final** del archivo (sin modificar los Enums existentes):

```python


class EstadoFarmacologico(str, Enum):
    """Estado del caso farmacológico del paciente (CEPA-020 RN-3).

    Pendiente confirmar catálogo final con Coordinación (ver Notas de cierre).
    """

    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    COMPLETADO = "completado"
    PENDIENTE = "pendiente"


class FrecuenciaFarmaco(str, Enum):
    """Frecuencias de administración habituales para el esquema farmacológico (CEPA-021 RN-1).

    'otro' contempla frecuencias no listadas (se registra junto al campo texto).
    """

    C24H = "c/24h"
    C12H = "c/12h"
    C8H = "c/8h"
    C6H = "c/6h"
    SEMANAL = "semanal"
    BISEMANAL = "bisemanal"
    MENSUAL = "mensual"
    OTRO = "otro"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_farmacos_enums.py -v`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/enums.py backend/tests/test_farmacos_enums.py
git commit -m "feat(farmacos): enums de dominio farmacológico (estado, frecuencia)"
```

---

## Task 2: Modelo `RegistroFarmacologico` + migración (CEPA-020)

Tabla raíz de la épica. Una fila por folio (folio único en esta tabla: RN-4 de CEPA-020). Vincula al ingreso y guarda médico tratante, estado farmacológico y campos heredados del folio que se confirman aquí como referencia.

**Files:**
- Create: `backend/app/models/farmacos.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0020_crear_reg_farmacologico.py`
- Test: `backend/tests/test_farmacos_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_model.py`:

```python
from sqlalchemy import BigInteger, Boolean, DateTime, String

from app.models.farmacos import RegistroFarmacologico


def test_tabla_y_columnas_reg_farmacologico():
    tabla = RegistroFarmacologico.__table__
    assert tabla.name == "reg_farmacologico"
    assert set(tabla.columns.keys()) == {
        "id",
        "ingreso_id",
        "medico_tratante",
        "estado_farmacologico",
        "antecedentes_previos",
        "tratamiento_previo",
        "activo",
        "created_at",
        "updated_at",
    }


def test_portabilidad_identificadores_reg():
    tabla = RegistroFarmacologico.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pk_identity_y_tipos_reg():
    cols = RegistroFarmacologico.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["medico_tratante"].type, String)
    assert isinstance(cols["estado_farmacologico"].type, String)
    assert isinstance(cols["activo"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_ingreso_id_es_unique_en_reg():
    """Un folio puede tener a lo sumo un registro farmacológico activo (CEPA-020 RN-4)."""
    tabla = RegistroFarmacologico.__table__
    assert tabla.columns["ingreso_id"].unique is True


def test_fk_a_ingreso():
    cols = RegistroFarmacologico.__table__.columns
    fks = list(cols["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.farmacos'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/farmacos.py`:

```python
"""Modelos del dominio de Gestión de Fármacos (EPIC-02).

Tablas: reg_farmacologico, esquema_indicacion, receta, seguim_tratamiento, alerta.
Todas siguen las reglas de portabilidad D15: tipos genéricos SQLAlchemy, Identity,
identificadores ≤30 chars en minúscula, fechas UTC.
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RegistroFarmacologico(Base):
    """Registro farmacológico de un paciente, vinculado 1:1 al ingreso (CEPA-020).

    El campo `activo` permite reutilizar/reactivar el registro en un reingreso
    (CEPA-020 RN-4) sin duplicar la fila — se conserva el historial completo.
    """

    __tablename__ = "reg_farmacologico"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), unique=True, nullable=False, index=True
    )
    medico_tratante: Mapped[str] = mapped_column(String(160), nullable=False)
    estado_farmacologico: Mapped[str] = mapped_column(String(40), nullable=False)
    antecedentes_previos: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento_previo: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    indicaciones: Mapped[list["EsquemaIndicacion"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )
    recetas: Mapped[list["Receta"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )
    seguimientos: Mapped[list["SeguimTratamiento"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )


class EsquemaIndicacion(Base):
    """Indicación farmacológica individual del esquema del paciente (CEPA-021).

    El esquema es versionable: una nueva indicación no reemplaza la anterior,
    se agrega como nueva fila (CEPA-021 RN-2). `vigente=True` marca la actual.
    `extra_sistema=True` identifica fármacos fuera del catálogo institucional (D7).
    """

    __tablename__ = "esquema_indicacion"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    registro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reg_farmacologico.id"), nullable=False, index=True
    )
    medicamento: Mapped[str] = mapped_column(String(200), nullable=False)
    dosis: Mapped[str] = mapped_column(String(80), nullable=False)
    frecuencia: Mapped[str] = mapped_column(String(40), nullable=False)
    extra_sistema: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    registro: Mapped["RegistroFarmacologico"] = relationship(back_populates="indicaciones")


class Receta(Base):
    """Receta vinculada a un registro farmacológico (CEPA-022).

    Contiene las tres fechas del ciclo: emisión, revisión y envío.
    El proceso de alertas revisa `fecha_revision` contra la fecha actual (RN-3).
    """

    __tablename__ = "receta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    registro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reg_farmacologico.id"), nullable=False, index=True
    )
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_revision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_envio: Mapped[date | None] = mapped_column(Date, nullable=True)
    marca_medicamento: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    registro: Mapped["RegistroFarmacologico"] = relationship(back_populates="recetas")


class SeguimTratamiento(Base):
    """Seguimiento de tratamiento farmacológico de un paciente (CEPA-023).

    Si `disminucion_farmacos=True` → `plan_disminucion` obligatorio (validado en servicio).
    Si `cambio_esquema=True` → `detalle_cambio` obligatorio (validado en servicio).
    """

    __tablename__ = "seguim_tratamiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    registro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reg_farmacologico.id"), nullable=False, index=True
    )
    disminucion_farmacos: Mapped[bool] = mapped_column(Boolean, nullable=False)
    plan_disminucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cambio_esquema: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detalle_cambio: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    registro: Mapped["RegistroFarmacologico"] = relationship(back_populates="seguimientos")


class Alerta(Base):
    """Alerta generada por el proceso de revisión de recetas (CEPA-022 RN-3).

    Se escribe cuando `fecha_revision` de una receta está dentro de los próximos
    5 días (límite inclusivo). La entrega in-app la gestiona EPIC-10.
    """

    __tablename__ = "alerta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    receta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receta.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(300), nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    receta: Mapped["Receta"] = relationship()
```

- [ ] **Step 4: Registrar los modelos en `app/models/__init__.py`**

Abrir `backend/app/models/__init__.py` y **añadir al final** (sin tocar las líneas de EPIC-01):

```python
from app.models.farmacos import (  # noqa: F401
    Alerta,
    EsquemaIndicacion,
    RecetaFarmaco,
    RegistroFarmacologico,
    SeguimTratamiento,
)
```

> **Nota:** SQLAlchemy necesita que todos los modelos estén importados aquí para que Alembic los detecte en `Base.metadata`. Si al correr `alembic upgrade head` aparece un error `target_metadata no incluye la tabla`, verificar que el import llegó bien.

> **Corrección de nombre:** la clase se llama `Receta` en `farmacos.py`; el import en `__init__.py` debe usar `Receta`, no `RecetaFarmaco`. Reemplazar el fragmento anterior por:

```python
from app.models.farmacos import (  # noqa: F401
    Alerta,
    EsquemaIndicacion,
    Receta,
    RegistroFarmacologico,
    SeguimTratamiento,
)
```

- [ ] **Step 5: Crear la migración `backend/migrations/versions/0020_crear_reg_farmacologico.py`**

```python
"""crear reg_farmacologico

Revision ID: 0020
Revises: <RESOLVER: alembic heads>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "<RESOLVER: alembic heads>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reg_farmacologico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("medico_tratante", sa.String(length=160), nullable=False),
        sa.Column("estado_farmacologico", sa.String(length=40), nullable=False),
        sa.Column("antecedentes_previos", sa.Text(), nullable=True),
        sa.Column("tratamiento_previo", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_reg_farm_ingreso"
        ),
    )
    op.create_unique_constraint("uq_reg_farm_ingreso_id", "reg_farmacologico", ["ingreso_id"])
    op.create_index("ix_reg_farm_ingreso_id", "reg_farmacologico", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_reg_farm_ingreso_id", table_name="reg_farmacologico")
    op.drop_constraint("uq_reg_farm_ingreso_id", "reg_farmacologico", type_="unique")
    op.drop_table("reg_farmacologico")
```

> **`<RESOLVER: alembic heads>`**: antes de correr, ejecutar `uv run alembic heads` desde `backend/` y reemplazar este marcador por la última revisión de EPIC-01 que aparezca (p. ej. `"001x"`). Ver Notas de cierre.

- [ ] **Step 6: Correr los tests de modelo y verificar que pasan**

Run: `uv run pytest tests/test_farmacos_model.py -v`
Expected: `5 passed`.

- [ ] **Step 7: Aplicar la migración y verificar up/down**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: crea, baja y vuelve a crear `reg_farmacologico` sin error.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/farmacos.py backend/app/models/__init__.py \
        backend/migrations/versions/0020_crear_reg_farmacologico.py \
        backend/tests/test_farmacos_model.py
git commit -m "feat(farmacos): modelo RegistroFarmacologico + migración (CEPA-020)"
```

---

## Task 3: Migraciones para las tablas restantes de la épica

Las cuatro tablas adicionales (esquema_indicacion, receta, seguim_tratamiento, alerta) se crean en migraciones independientes, una por historia, para mantener el linaje trazable.

**Files:**
- Create: `backend/migrations/versions/0021_crear_esquema_indicacion.py`
- Create: `backend/migrations/versions/0022_crear_receta.py`
- Create: `backend/migrations/versions/0023_crear_seguim_tratamiento.py`
- Create: `backend/migrations/versions/0022b_crear_alerta.py`
- Test: `backend/tests/test_farmacos_migrations.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_migrations.py`:

```python
from sqlalchemy import inspect

from app.db.session import engine


def test_tablas_de_farmacos_existen():
    tablas = inspect(engine).get_table_names()
    for nombre in [
        "reg_farmacologico",
        "esquema_indicacion",
        "receta",
        "seguim_tratamiento",
        "alerta",
    ]:
        assert nombre in tablas, f"Tabla {nombre!r} no encontrada tras upgrade head"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_migrations.py -v`
Expected: FAIL — solo `reg_farmacologico` existe, las demás aún no.

- [ ] **Step 3: Crear migración `0021_crear_esquema_indicacion.py`**

Crear `backend/migrations/versions/0021_crear_esquema_indicacion.py`:

```python
"""crear esquema_indicacion

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "esquema_indicacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("registro_id", sa.BigInteger(), nullable=False),
        sa.Column("medicamento", sa.String(length=200), nullable=False),
        sa.Column("dosis", sa.String(length=80), nullable=False),
        sa.Column("frecuencia", sa.String(length=40), nullable=False),
        sa.Column("extra_sistema", sa.Boolean(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["reg_farmacologico.id"], name="fk_esq_ind_registro"
        ),
    )
    op.create_index("ix_esq_ind_registro_id", "esquema_indicacion", ["registro_id"])


def downgrade() -> None:
    op.drop_index("ix_esq_ind_registro_id", table_name="esquema_indicacion")
    op.drop_table("esquema_indicacion")
```

- [ ] **Step 4: Crear migración `0022_crear_receta.py`**

Crear `backend/migrations/versions/0022_crear_receta.py`:

```python
"""crear receta

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("registro_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_revision", sa.Date(), nullable=False),
        sa.Column("fecha_envio", sa.Date(), nullable=True),
        sa.Column("marca_medicamento", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["reg_farmacologico.id"], name="fk_receta_registro"
        ),
    )
    op.create_index("ix_receta_registro_id", "receta", ["registro_id"])
    op.create_index("ix_receta_fecha_revision", "receta", ["fecha_revision"])


def downgrade() -> None:
    op.drop_index("ix_receta_fecha_revision", table_name="receta")
    op.drop_index("ix_receta_registro_id", table_name="receta")
    op.drop_table("receta")
```

- [ ] **Step 5: Crear migración `0023_crear_seguim_tratamiento.py`**

Crear `backend/migrations/versions/0023_crear_seguim_tratamiento.py`:

```python
"""crear seguim_tratamiento

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seguim_tratamiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("registro_id", sa.BigInteger(), nullable=False),
        sa.Column("disminucion_farmacos", sa.Boolean(), nullable=False),
        sa.Column("plan_disminucion", sa.Text(), nullable=True),
        sa.Column("cambio_esquema", sa.Boolean(), nullable=False),
        sa.Column("detalle_cambio", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["reg_farmacologico.id"], name="fk_seguim_registro"
        ),
    )
    op.create_index("ix_seguim_registro_id", "seguim_tratamiento", ["registro_id"])


def downgrade() -> None:
    op.drop_index("ix_seguim_registro_id", table_name="seguim_tratamiento")
    op.drop_table("seguim_tratamiento")
```

- [ ] **Step 6: Crear migración `0024_crear_alerta.py`**

Crear `backend/migrations/versions/0024_crear_alerta.py`:

```python
"""crear alerta

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("receta_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("mensaje", sa.String(length=300), nullable=False),
        sa.Column("leida", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["receta_id"], ["receta.id"], name="fk_alerta_receta"),
    )
    op.create_index("ix_alerta_receta_id", "alerta", ["receta_id"])
    op.create_index("ix_alerta_leida", "alerta", ["leida"])


def downgrade() -> None:
    op.drop_index("ix_alerta_leida", table_name="alerta")
    op.drop_index("ix_alerta_receta_id", table_name="alerta")
    op.drop_table("alerta")
```

- [ ] **Step 7: Aplicar todas las migraciones y correr el test**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_farmacos_migrations.py -v
```
Expected: `1 passed` (las 5 tablas existen).

- [ ] **Step 8: Verificar downgrade completo del bloque**

Run:
```bash
uv run alembic downgrade -4
uv run alembic upgrade head
```
Expected: baja las 4 migraciones nuevas y vuelve a crear todas sin error.

- [ ] **Step 9: Commit**

```bash
git add backend/migrations/versions/0021_crear_esquema_indicacion.py \
        backend/migrations/versions/0022_crear_receta.py \
        backend/migrations/versions/0023_crear_seguim_tratamiento.py \
        backend/migrations/versions/0024_crear_alerta.py \
        backend/tests/test_farmacos_migrations.py
git commit -m "feat(farmacos): migraciones esquema_indicacion, receta, seguim_tratamiento, alerta"
```

---

## Task 4: Schemas Pydantic de la épica

Todos los schemas de request/response para los cuatro módulos farmacológicos.

**Files:**
- Create: `backend/app/schemas/farmacos.py`
- Test: `backend/tests/test_farmacos_schemas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.farmacos import (
    EsquemaIndicacionCreate,
    RecetaCreate,
    RegistroFarmacologicoCreate,
    SeguimTratamientoCreate,
)


# ── RegistroFarmacologicoCreate ──────────────────────────────────────────────

def test_reg_farm_requiere_ingreso_id_medico_y_estado():
    with pytest.raises(ValidationError) as exc:
        RegistroFarmacologicoCreate(medico_tratante="Dr. X", estado_farmacologico="activo")
    errors = {e["loc"][0] for e in exc.value.errors()}
    assert "ingreso_id" in errors


def test_reg_farm_estado_invalido_rechazado():
    with pytest.raises(ValidationError):
        RegistroFarmacologicoCreate(
            ingreso_id=1,
            medico_tratante="Dr. X",
            estado_farmacologico="inventado",
        )


def test_reg_farm_valido():
    obj = RegistroFarmacologicoCreate(
        ingreso_id=1,
        medico_tratante="Dr. González",
        estado_farmacologico="activo",
    )
    assert obj.ingreso_id == 1
    assert obj.estado_farmacologico == "activo"


# ── EsquemaIndicacionCreate ──────────────────────────────────────────────────

def test_indicacion_requiere_medicamento_dosis_frecuencia():
    with pytest.raises(ValidationError) as exc:
        EsquemaIndicacionCreate(registro_id=1, medicamento="Sertralina")
    errors = {e["loc"][0] for e in exc.value.errors()}
    assert "dosis" in errors
    assert "frecuencia" in errors


def test_indicacion_frecuencia_invalida_rechazada():
    with pytest.raises(ValidationError):
        EsquemaIndicacionCreate(
            registro_id=1,
            medicamento="Sertralina",
            dosis="50 mg",
            frecuencia="cada luna llena",
        )


def test_indicacion_extra_sistema_por_defecto_false():
    obj = EsquemaIndicacionCreate(
        registro_id=1,
        medicamento="Sertralina",
        dosis="50 mg",
        frecuencia="c/24h",
    )
    assert obj.extra_sistema is False


def test_indicacion_extra_sistema_true():
    obj = EsquemaIndicacionCreate(
        registro_id=1,
        medicamento="MedicamentoExtranjero X",
        dosis="10 mg",
        frecuencia="c/12h",
        extra_sistema=True,
    )
    assert obj.extra_sistema is True


# ── RecetaCreate ─────────────────────────────────────────────────────────────

def test_receta_revision_no_puede_ser_anterior_a_emision():
    """CEPA-022 RN-5: fecha_revision no puede ser anterior a fecha_emision."""
    with pytest.raises(ValidationError) as exc:
        RecetaCreate(
            registro_id=1,
            fecha_emision="2026-06-10",
            fecha_revision="2026-06-05",
            marca_medicamento="Fluoxetina",
        )
    errores = str(exc.value)
    assert "revision" in errores.lower() or "emision" in errores.lower()


def test_receta_envio_no_puede_ser_anterior_a_emision():
    """CEPA-022 RN-5: fecha_envio no puede ser anterior a fecha_emision."""
    with pytest.raises(ValidationError) as exc:
        RecetaCreate(
            registro_id=1,
            fecha_emision="2026-06-10",
            fecha_revision="2026-06-20",
            fecha_envio="2026-06-09",
            marca_medicamento="Fluoxetina",
        )
    errores = str(exc.value)
    assert "envio" in errores.lower() or "emision" in errores.lower()


def test_receta_valida():
    obj = RecetaCreate(
        registro_id=1,
        fecha_emision="2026-06-01",
        fecha_revision="2026-06-20",
        fecha_envio="2026-06-05",
        marca_medicamento="Fluoxetina genérico",
    )
    assert obj.marca_medicamento == "Fluoxetina genérico"


# ── SeguimTratamientoCreate ──────────────────────────────────────────────────

def test_seguim_disminucion_true_requiere_plan():
    """CEPA-023 RN-1: plan obligatorio si disminucion_farmacos=True."""
    with pytest.raises(ValidationError) as exc:
        SeguimTratamientoCreate(
            registro_id=1,
            disminucion_farmacos=True,
            cambio_esquema=False,
        )
    errores = str(exc.value)
    assert "plan_disminucion" in errores


def test_seguim_cambio_true_requiere_detalle():
    """CEPA-023 RN-2: detalle obligatorio si cambio_esquema=True."""
    with pytest.raises(ValidationError) as exc:
        SeguimTratamientoCreate(
            registro_id=1,
            disminucion_farmacos=False,
            cambio_esquema=True,
        )
    errores = str(exc.value)
    assert "detalle_cambio" in errores


def test_seguim_ambos_false_sin_detalles_valido():
    obj = SeguimTratamientoCreate(
        registro_id=1,
        disminucion_farmacos=False,
        cambio_esquema=False,
        observaciones="Sin cambios esta semana.",
    )
    assert obj.observaciones == "Sin cambios esta semana."
    assert obj.plan_disminucion is None
    assert obj.detalle_cambio is None


def test_seguim_disminucion_true_con_plan_valido():
    obj = SeguimTratamientoCreate(
        registro_id=1,
        disminucion_farmacos=True,
        plan_disminucion="Reducir 25 mg/semana.",
        cambio_esquema=False,
    )
    assert obj.plan_disminucion == "Reducir 25 mg/semana."


def test_seguim_cambio_true_con_detalle_valido():
    obj = SeguimTratamientoCreate(
        registro_id=1,
        disminucion_farmacos=False,
        cambio_esquema=True,
        detalle_cambio="Agregar Clonazepam 0.5 mg c/24h.",
    )
    assert obj.detalle_cambio == "Agregar Clonazepam 0.5 mg c/24h."
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.farmacos'`.

- [ ] **Step 3: Implementar `app/schemas/farmacos.py`**

Crear `backend/app/schemas/farmacos.py`:

```python
"""Schemas Pydantic v2 para EPIC-02 — Gestión de Fármacos.

Incluye validaciones de negocio:
- Estado farmacológico como Enum (CEPA-020 RN-3).
- Frecuencia de fármaco como Enum (CEPA-021 RN-1).
- Fechas de receta: revisión y envío no anteriores a emisión (CEPA-022 RN-5).
- Seguimiento: plan/detalle obligatorio cuando la bandera es True (CEPA-023 RN-1/RN-2).
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.enums import EstadoFarmacologico, FrecuenciaFarmaco


# ── RegistroFarmacologico ─────────────────────────────────────────────────────

class RegistroFarmacologicoCreate(BaseModel):
    ingreso_id: int
    medico_tratante: str
    estado_farmacologico: EstadoFarmacologico
    antecedentes_previos: str | None = None
    tratamiento_previo: str | None = None


class RegistroFarmacologicoUpdate(BaseModel):
    medico_tratante: str | None = None
    estado_farmacologico: EstadoFarmacologico | None = None
    antecedentes_previos: str | None = None
    tratamiento_previo: str | None = None
    activo: bool | None = None


class RegistroFarmacologicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    medico_tratante: str
    estado_farmacologico: EstadoFarmacologico
    antecedentes_previos: str | None
    tratamiento_previo: str | None
    activo: bool
    created_at: datetime
    updated_at: datetime


# ── EsquemaIndicacion ─────────────────────────────────────────────────────────

class EsquemaIndicacionCreate(BaseModel):
    registro_id: int
    medicamento: str
    dosis: str
    frecuencia: FrecuenciaFarmaco
    extra_sistema: bool = False


class EsquemaIndicacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registro_id: int
    medicamento: str
    dosis: str
    frecuencia: FrecuenciaFarmaco
    extra_sistema: bool
    vigente: bool
    created_at: datetime


# ── Receta ────────────────────────────────────────────────────────────────────

class RecetaCreate(BaseModel):
    registro_id: int
    fecha_emision: date
    fecha_revision: date
    fecha_envio: date | None = None
    marca_medicamento: str

    @model_validator(mode="after")
    def _validar_orden_fechas(self) -> "RecetaCreate":
        if self.fecha_revision < self.fecha_emision:
            raise ValueError(
                "fecha_revision no puede ser anterior a fecha_emision (CEPA-022 RN-5)"
            )
        if self.fecha_envio is not None and self.fecha_envio < self.fecha_emision:
            raise ValueError(
                "fecha_envio no puede ser anterior a fecha_emision (CEPA-022 RN-5)"
            )
        return self


class RecetaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registro_id: int
    fecha_emision: date
    fecha_revision: date
    fecha_envio: date | None
    marca_medicamento: str
    created_at: datetime
    updated_at: datetime


# ── SeguimTratamiento ─────────────────────────────────────────────────────────

class SeguimTratamientoCreate(BaseModel):
    registro_id: int
    disminucion_farmacos: bool
    plan_disminucion: str | None = None
    cambio_esquema: bool
    detalle_cambio: str | None = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def _validar_detalles_obligatorios(self) -> "SeguimTratamientoCreate":
        if self.disminucion_farmacos and not self.plan_disminucion:
            raise ValueError(
                "plan_disminucion es obligatorio cuando disminucion_farmacos=True (CEPA-023 RN-1)"
            )
        if self.cambio_esquema and not self.detalle_cambio:
            raise ValueError(
                "detalle_cambio es obligatorio cuando cambio_esquema=True (CEPA-023 RN-2)"
            )
        return self


class SeguimTratamientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registro_id: int
    disminucion_farmacos: bool
    plan_disminucion: str | None
    cambio_esquema: bool
    detalle_cambio: str | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime


# ── Alerta ────────────────────────────────────────────────────────────────────

class AlertaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receta_id: int
    tipo: str
    mensaje: str
    leida: bool
    created_at: datetime
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_farmacos_schemas.py -v`
Expected: `14 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/farmacos.py backend/tests/test_farmacos_schemas.py
git commit -m "feat(farmacos): schemas Pydantic v2 con validaciones de negocio (CEPA-020..023)"
```

---

## Task 5: Servicio de registro farmacológico + API (CEPA-020)

Endpoint `POST /api/v1/registro-farmacologico` (crear) y `GET /api/v1/registro-farmacologico/{ingreso_id}` (leer). Valida que el ingreso existe, aplica la unicidad del folio (RN-4: si ya existe un registro activo, lo reactiva en vez de duplicar), registra auditoría.

**Files:**
- Create: `backend/app/services/farmacos.py`
- Create: `backend/app/routers/farmacos.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_farmacos_020_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_020_api.py`:

```python
"""Tests de CEPA-020: registro farmacológico vinculado al folio.

Fixtures as_admin / as_coordinacion / as_auditor provienen de EPIC-00 conftest.
Se necesita un ingreso previo: helper _crear_ingreso() lo hace vía API de EPIC-01.
"""
import pytest


def _crear_ingreso(client) -> int:
    """Crea un ingreso via API y devuelve su id."""
    payload = {
        "rut": "12.345.678-5",
        "nombre": "Paciente Test",
        "sexo": "F",
        "edad": 35,
        "region": "Maule",
        "diagnostico": "Trastorno adaptativo",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-10",
    }
    r = client.post("/api/v1/ingresos", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _payload_reg(ingreso_id: int, **over) -> dict:
    base = {
        "ingreso_id": ingreso_id,
        "medico_tratante": "Dr. González",
        "estado_farmacologico": "activo",
    }
    base.update(over)
    return base


# TC-020-01
def test_crear_registro_farmacologico_vinculado_al_folio(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["ingreso_id"] == ingreso_id
    assert cuerpo["medico_tratante"] == "Dr. González"
    assert cuerpo["estado_farmacologico"] == "activo"
    assert cuerpo["activo"] is True


# TC-020-02: lectura devuelve el registro
def test_obtener_registro_por_ingreso_id(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}")
    assert r.status_code == 200
    assert r.json()["ingreso_id"] == ingreso_id


# TC-020-03: campos obligatorios ausentes -> 422 (sin folio es error de Pydantic)
def test_crear_sin_medico_tratante_rechazado(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json={"ingreso_id": ingreso_id, "estado_farmacologico": "activo"},
    )
    assert r.status_code == 422
    assert "medico_tratante" in r.text


def test_crear_sin_estado_rechazado(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json={"ingreso_id": ingreso_id, "medico_tratante": "Dr. X"},
    )
    assert r.status_code == 422
    assert "estado_farmacologico" in r.text


# TC-020-03b: estado inválido -> 422
def test_estado_invalido_rechazado(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json=_payload_reg(ingreso_id, estado_farmacologico="inventado"),
    )
    assert r.status_code == 422


# TC-020-04: folio ya tiene registro activo → se reactiva (no duplica)
def test_reingreso_mismo_folio_reactiva_registro(as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r1 = as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r1.status_code == 201
    id1 = r1.json()["id"]
    # segundo intento para el mismo ingreso → debe devolver el mismo registro reactivado
    r2 = as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r2.status_code == 200  # reactivación, no 201
    assert r2.json()["id"] == id1
    assert r2.json()["activo"] is True


# TC-020-05: Auditor no puede crear → 403
def test_auditor_no_puede_crear_registro(as_auditor, as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    r = as_auditor.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    assert r.status_code == 403


# TC-020-05b: Auditor sí puede leer → 200
def test_auditor_puede_leer_registro(as_auditor, as_admin):
    ingreso_id = _crear_ingreso(as_admin)
    as_admin.post("/api/v1/registro-farmacologico", json=_payload_reg(ingreso_id))
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}")
    assert r.status_code == 200


# Ingreso inexistente → 404
def test_ingreso_inexistente_devuelve_404(as_admin):
    r = as_admin.post(
        "/api/v1/registro-farmacologico",
        json=_payload_reg(999999),
    )
    assert r.status_code == 404
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_020_api.py -v`
Expected: FAIL con `404 Not Found` (la ruta no existe todavía).

- [ ] **Step 3: Implementar el servicio `app/services/farmacos.py`**

Crear `backend/app/services/farmacos.py`:

```python
"""Servicios de dominio para EPIC-02 — Gestión de Fármacos.

Cubre: RegistroFarmacologico (CEPA-020), EsquemaIndicacion (CEPA-021),
Receta y alertas de revisión (CEPA-022), SeguimTratamiento (CEPA-023).
"""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.farmacos import (
    Alerta,
    EsquemaIndicacion,
    Receta,
    RegistroFarmacologico,
    SeguimTratamiento,
)
from app.models.ingreso import Ingreso
from app.schemas.farmacos import (
    EsquemaIndicacionCreate,
    RecetaCreate,
    RegistroFarmacologicoCreate,
    RegistroFarmacologicoUpdate,
    SeguimTratamientoCreate,
)

_VENTANA_ALERTA_DIAS = 5


# ── RegistroFarmacologico ─────────────────────────────────────────────────────

def _exigir_ingreso(db, ingreso_id: int) -> Ingreso:
    """Devuelve el ingreso o lanza 404 si no existe."""
    ingreso = db.execute(
        select(Ingreso).where(Ingreso.id == ingreso_id)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingreso {ingreso_id} no encontrado.",
        )
    return ingreso


def crear_o_reactivar_registro(
    db, data: RegistroFarmacologicoCreate
) -> tuple[RegistroFarmacologico, bool]:
    """Crea un registro farmacológico o reactiva el existente (CEPA-020 RN-4).

    Devuelve (registro, creado): creado=True si es nuevo, False si fue reactivado.
    """
    _exigir_ingreso(db, data.ingreso_id)
    existente = db.execute(
        select(RegistroFarmacologico).where(
            RegistroFarmacologico.ingreso_id == data.ingreso_id
        )
    ).scalar_one_or_none()

    if existente is not None:
        # Reactivar: actualizar campos y marcar activo (RN-4)
        existente.medico_tratante = data.medico_tratante
        existente.estado_farmacologico = data.estado_farmacologico.value
        if data.antecedentes_previos is not None:
            existente.antecedentes_previos = data.antecedentes_previos
        if data.tratamiento_previo is not None:
            existente.tratamiento_previo = data.tratamiento_previo
        existente.activo = True
        db.flush()
        return existente, False

    registro = RegistroFarmacologico(
        ingreso_id=data.ingreso_id,
        medico_tratante=data.medico_tratante,
        estado_farmacologico=data.estado_farmacologico.value,
        antecedentes_previos=data.antecedentes_previos,
        tratamiento_previo=data.tratamiento_previo,
        activo=True,
    )
    db.add(registro)
    db.flush()
    return registro, True


def obtener_registro_por_ingreso(db, ingreso_id: int) -> RegistroFarmacologico:
    """Devuelve el registro farmacológico de un ingreso o lanza 404."""
    registro = db.execute(
        select(RegistroFarmacologico).where(
            RegistroFarmacologico.ingreso_id == ingreso_id
        )
    ).scalar_one_or_none()
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe registro farmacológico para el ingreso {ingreso_id}.",
        )
    return registro


def actualizar_registro(
    db, ingreso_id: int, data: RegistroFarmacologicoUpdate
) -> RegistroFarmacologico:
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(registro, campo, valor if not hasattr(valor, "value") else valor.value)
    db.flush()
    return registro


# ── EsquemaIndicacion ─────────────────────────────────────────────────────────

def _exigir_registro(db, registro_id: int) -> RegistroFarmacologico:
    reg = db.execute(
        select(RegistroFarmacologico).where(RegistroFarmacologico.id == registro_id)
    ).scalar_one_or_none()
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro farmacológico {registro_id} no encontrado.",
        )
    return reg


def agregar_indicacion(db, data: EsquemaIndicacionCreate) -> EsquemaIndicacion:
    """Agrega nueva indicación al esquema. Las previas conservan su estado (RN-2 CEPA-021)."""
    _exigir_registro(db, data.registro_id)
    indicacion = EsquemaIndicacion(
        registro_id=data.registro_id,
        medicamento=data.medicamento,
        dosis=data.dosis,
        frecuencia=data.frecuencia.value,
        extra_sistema=data.extra_sistema,
        vigente=True,
    )
    db.add(indicacion)
    db.flush()
    return indicacion


def listar_indicaciones(db, registro_id: int) -> list[EsquemaIndicacion]:
    _exigir_registro(db, registro_id)
    return list(
        db.scalars(
            select(EsquemaIndicacion)
            .where(EsquemaIndicacion.registro_id == registro_id)
            .order_by(EsquemaIndicacion.id)
        )
    )


# ── Receta ────────────────────────────────────────────────────────────────────

def crear_receta(db, data: RecetaCreate) -> Receta:
    """Crea una receta vinculada al registro farmacológico (CEPA-022 RN-1)."""
    _exigir_registro(db, data.registro_id)
    receta = Receta(
        registro_id=data.registro_id,
        fecha_emision=data.fecha_emision,
        fecha_revision=data.fecha_revision,
        fecha_envio=data.fecha_envio,
        marca_medicamento=data.marca_medicamento,
    )
    db.add(receta)
    db.flush()
    return receta


def listar_recetas(db, registro_id: int) -> list[Receta]:
    _exigir_registro(db, registro_id)
    return list(
        db.scalars(
            select(Receta)
            .where(Receta.registro_id == registro_id)
            .order_by(Receta.id)
        )
    )


def generar_alertas_revision(db, hoy: date | None = None) -> list[Alerta]:
    """Genera alertas para recetas cuya fecha_revision cae dentro de los próximos
    _VENTANA_ALERTA_DIAS días (límite inclusivo). Omite recetas que ya tienen alerta
    del mismo tipo generada el mismo día (idempotente). CEPA-022 RN-3/CA-2/CA-3.
    """
    from datetime import datetime, timezone as tz

    hoy = hoy or date.today()
    limite = hoy + timedelta(days=_VENTANA_ALERTA_DIAS)

    recetas_proximas = db.scalars(
        select(Receta).where(
            Receta.fecha_revision >= hoy,
            Receta.fecha_revision <= limite,
        )
    ).all()

    nuevas: list[Alerta] = []
    for receta in recetas_proximas:
        # Idempotencia: no duplicar alerta si ya existe para esta receta+tipo+día
        ya_existe = db.execute(
            select(Alerta).where(
                Alerta.receta_id == receta.id,
                Alerta.tipo == "revision_proxima",
            )
        ).scalar_one_or_none()
        if ya_existe is not None:
            continue
        dias_restantes = (receta.fecha_revision - hoy).days
        alerta = Alerta(
            receta_id=receta.id,
            tipo="revision_proxima",
            mensaje=(
                f"La receta #{receta.id} vence el {receta.fecha_revision.isoformat()} "
                f"({dias_restantes} día(s)). Revisar con el administrativo asignado."
            ),
            leida=False,
        )
        db.add(alerta)
        nuevas.append(alerta)
    db.flush()
    return nuevas


# ── SeguimTratamiento ─────────────────────────────────────────────────────────

def crear_seguimiento(db, data: SeguimTratamientoCreate) -> SeguimTratamiento:
    """Crea un registro de seguimiento de tratamiento (CEPA-023)."""
    _exigir_registro(db, data.registro_id)
    seguim = SeguimTratamiento(
        registro_id=data.registro_id,
        disminucion_farmacos=data.disminucion_farmacos,
        plan_disminucion=data.plan_disminucion,
        cambio_esquema=data.cambio_esquema,
        detalle_cambio=data.detalle_cambio,
        observaciones=data.observaciones,
    )
    db.add(seguim)
    db.flush()
    return seguim


def listar_seguimientos(db, registro_id: int) -> list[SeguimTratamiento]:
    _exigir_registro(db, registro_id)
    return list(
        db.scalars(
            select(SeguimTratamiento)
            .where(SeguimTratamiento.registro_id == registro_id)
            .order_by(SeguimTratamiento.id)
        )
    )
```

- [ ] **Step 4: Implementar el router `app/routers/farmacos.py` (solo endpoints de CEPA-020 por ahora)**

Crear `backend/app/routers/farmacos.py`:

```python
"""Router de Gestión de Fármacos (EPIC-02).

Prefijo: /api/v1/registro-farmacologico
Sub-recursos: /esquema, /recetas, /seguimiento, /recetas/alertas/generar
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.farmacos import (
    AlertaRead,
    EsquemaIndicacionCreate,
    EsquemaIndicacionRead,
    RecetaCreate,
    RecetaRead,
    RegistroFarmacologicoCreate,
    RegistroFarmacologicoRead,
    RegistroFarmacologicoUpdate,
    SeguimTratamientoCreate,
    SeguimTratamientoRead,
)
from app.services.farmacos import (
    agregar_indicacion,
    actualizar_registro,
    crear_o_reactivar_registro,
    crear_receta,
    crear_seguimiento,
    generar_alertas_revision,
    listar_indicaciones,
    listar_recetas,
    listar_seguimientos,
    obtener_registro_por_ingreso,
)

router = APIRouter(prefix="/api/v1/registro-farmacologico", tags=["farmacos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── RegistroFarmacologico (CEPA-020) ──────────────────────────────────────────

@router.post(
    "",
    response_model=RegistroFarmacologicoRead,
    dependencies=[Depends(_writer)],
)
def crear_registro(
    payload: RegistroFarmacologicoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro, creado = crear_o_reactivar_registro(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE" if creado else "UPDATE",
        entity="reg_farmacologico",
        entity_id=str(registro.id),
    )
    db.commit()
    db.refresh(registro)
    # HTTP 201 si nuevo, 200 si reactivado
    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder

    if creado:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder(RegistroFarmacologicoRead.model_validate(registro)),
        )
    return registro


@router.get(
    "/{ingreso_id}",
    response_model=RegistroFarmacologicoRead,
    dependencies=[Depends(_reader)],
)
def obtener_registro(ingreso_id: int, db: Session = Depends(get_db)):
    return obtener_registro_por_ingreso(db, ingreso_id)


@router.patch(
    "/{ingreso_id}",
    response_model=RegistroFarmacologicoRead,
    dependencies=[Depends(_writer)],
)
def actualizar(
    ingreso_id: int,
    payload: RegistroFarmacologicoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = actualizar_registro(db, ingreso_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="reg_farmacologico",
        entity_id=str(registro.id),
    )
    db.commit()
    db.refresh(registro)
    return registro


# ── EsquemaIndicacion (CEPA-021) ──────────────────────────────────────────────

@router.post(
    "/{ingreso_id}/esquema",
    response_model=EsquemaIndicacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def agregar_indicacion_endpoint(
    ingreso_id: int,
    payload: EsquemaIndicacionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    # El payload trae registro_id; lo forzamos a que coincida con la URL
    from app.schemas.farmacos import EsquemaIndicacionCreate as _EIC

    data = _EIC(
        registro_id=registro.id,
        medicamento=payload.medicamento,
        dosis=payload.dosis,
        frecuencia=payload.frecuencia,
        extra_sistema=payload.extra_sistema,
    )
    indicacion = agregar_indicacion(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="esquema_indicacion",
        entity_id=str(indicacion.id),
    )
    db.commit()
    db.refresh(indicacion)
    return indicacion


@router.get(
    "/{ingreso_id}/esquema",
    response_model=list[EsquemaIndicacionRead],
    dependencies=[Depends(_reader)],
)
def listar_indicaciones_endpoint(ingreso_id: int, db: Session = Depends(get_db)):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    return listar_indicaciones(db, registro.id)


# ── Receta (CEPA-022) ─────────────────────────────────────────────────────────

@router.post(
    "/{ingreso_id}/recetas",
    response_model=RecetaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_receta_endpoint(
    ingreso_id: int,
    payload: RecetaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    from app.schemas.farmacos import RecetaCreate as _RC

    data = _RC(
        registro_id=registro.id,
        fecha_emision=payload.fecha_emision,
        fecha_revision=payload.fecha_revision,
        fecha_envio=payload.fecha_envio,
        marca_medicamento=payload.marca_medicamento,
    )
    receta = crear_receta(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="receta",
        entity_id=str(receta.id),
    )
    db.commit()
    db.refresh(receta)
    return receta


@router.get(
    "/{ingreso_id}/recetas",
    response_model=list[RecetaRead],
    dependencies=[Depends(_reader)],
)
def listar_recetas_endpoint(ingreso_id: int, db: Session = Depends(get_db)):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    return listar_recetas(db, registro.id)


# ── Alertas de revisión (CEPA-022 RN-3) ──────────────────────────────────────

@router.post(
    "/recetas/alertas/generar",
    response_model=list[AlertaRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def generar_alertas_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Ejecuta el proceso de alertas de revisión próxima (ventana 5 días)."""
    alertas = generar_alertas_revision(db)
    for alerta in alertas:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="alerta",
            entity_id=str(alerta.id),
        )
    db.commit()
    for alerta in alertas:
        db.refresh(alerta)
    return alertas


# ── SeguimTratamiento (CEPA-023) ──────────────────────────────────────────────

@router.post(
    "/{ingreso_id}/seguimiento",
    response_model=SeguimTratamientoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_seguimiento_endpoint(
    ingreso_id: int,
    payload: SeguimTratamientoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    from app.schemas.farmacos import SeguimTratamientoCreate as _STC

    data = _STC(
        registro_id=registro.id,
        disminucion_farmacos=payload.disminucion_farmacos,
        plan_disminucion=payload.plan_disminucion,
        cambio_esquema=payload.cambio_esquema,
        detalle_cambio=payload.detalle_cambio,
        observaciones=payload.observaciones,
    )
    seguim = crear_seguimiento(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="seguim_tratamiento",
        entity_id=str(seguim.id),
    )
    db.commit()
    db.refresh(seguim)
    return seguim


@router.get(
    "/{ingreso_id}/seguimiento",
    response_model=list[SeguimTratamientoRead],
    dependencies=[Depends(_reader)],
)
def listar_seguimientos_endpoint(ingreso_id: int, db: Session = Depends(get_db)):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    return listar_seguimientos(db, registro.id)
```

- [ ] **Step 5: Registrar el router en `app/main.py`**

Abrir `backend/app/main.py` y **añadir** las líneas de import y `include_router` (conservando todo lo existente):

```python
from app.routers import farmacos

app.include_router(farmacos.router)
```

- [ ] **Step 6: Correr los tests de CEPA-020 y verificar que pasan**

Run: `uv run pytest tests/test_farmacos_020_api.py -v`
Expected: `8 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/farmacos.py backend/app/routers/farmacos.py \
        backend/app/main.py backend/tests/test_farmacos_020_api.py
git commit -m "feat(farmacos): API registro farmacológico CEPA-020 (crear/leer/reactivar)"
```

---

## Task 6: API de esquema farmacológico (CEPA-021)

Tests de integración end-to-end para los endpoints de indicaciones del esquema.

**Files:**
- Test: `backend/tests/test_farmacos_021_api.py`

> El router ya está implementado en Task 5; esta Task solo añade los tests de integración que cubren los TC y CA de CEPA-021.

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_021_api.py`:

```python
"""Tests de CEPA-021: historial clínico farmacológico y esquema."""


def _setup(client) -> tuple[int, int]:
    """Crea un ingreso y un registro farmacológico; devuelve (ingreso_id, registro_id)."""
    ingreso_r = client.post(
        "/api/v1/ingresos",
        json={
            "rut": "11.111.111-1",
            "nombre": "Paciente CEPA-021",
            "sexo": "F",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "F32",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert ingreso_r.status_code == 201, ingreso_r.text
    ingreso_id = ingreso_r.json()["id"]

    reg_r = client.post(
        "/api/v1/registro-farmacologico",
        json={
            "ingreso_id": ingreso_id,
            "medico_tratante": "Dr. Pérez",
            "estado_farmacologico": "activo",
            "antecedentes_previos": "Depresión 2018",
            "tratamiento_previo": "Fluoxetina 20 mg (2018-2020)",
        },
    )
    assert ingreso_r.status_code == 201, reg_r.text
    return ingreso_id, reg_r.json()["id"]


# TC-021-01: CA-1 — antecedentes y tratamiento previo se guardan
def test_antecedentes_guardados_vinculados_al_folio(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}")
    assert r.status_code == 200
    body = r.json()
    assert "Depresión 2018" in body["antecedentes_previos"]
    assert "Fluoxetina" in body["tratamiento_previo"]


# TC-021-01: CA-2 — indicación actual con medicamento/dosis/frecuencia
def test_agregar_indicacion_actual(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["medicamento"] == "Sertralina"
    assert body["dosis"] == "50 mg"
    assert body["frecuencia"] == "c/24h"
    assert body["extra_sistema"] is False
    assert body["vigente"] is True


# TC-021-02: sin dosis ni frecuencia → 422
def test_indicacion_sin_dosis_rechazada(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina"},
    )
    assert r.status_code == 422
    errores = r.text.lower()
    assert "dosis" in errores or "frecuencia" in errores


# TC-021-03: CA-3 — fármaco extra-sistema aceptado y etiquetado
def test_farmaco_extra_sistema_aceptado(as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={
            "medicamento": "Vortioxetina (importado)",
            "dosis": "10 mg",
            "frecuencia": "c/24h",
            "extra_sistema": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["extra_sistema"] is True


# TC-021-04: historial conserva indicaciones previas (versioning)
def test_nueva_indicacion_no_borra_la_previa(as_admin):
    ingreso_id, _ = _setup(as_admin)
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Clonazepam", "dosis": "0.5 mg", "frecuencia": "c/24h"},
    )
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/esquema")
    assert r.status_code == 200
    medicamentos = [i["medicamento"] for i in r.json()]
    assert "Sertralina" in medicamentos
    assert "Clonazepam" in medicamentos


# TC-021-05: Auditor no puede agregar indicación → 403
def test_auditor_no_puede_agregar_indicacion(as_auditor, as_admin):
    ingreso_id, _ = _setup(as_admin)
    r = as_auditor.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    assert r.status_code == 403


# TC-021-05: Auditor puede leer el esquema → 200
def test_auditor_puede_leer_esquema(as_auditor, as_admin):
    ingreso_id, _ = _setup(as_admin)
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/esquema",
        json={"medicamento": "Sertralina", "dosis": "50 mg", "frecuencia": "c/24h"},
    )
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}/esquema")
    assert r.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla (la ruta existe pero puede faltar algún detalle)**

Run: `uv run pytest tests/test_farmacos_021_api.py -v`
Expected: pueden fallar algunos tests por comportamiento pendiente. Corregir el servicio hasta verde.

- [ ] **Step 3: Correr y verificar que pasan todos**

Run: `uv run pytest tests/test_farmacos_021_api.py -v`
Expected: `8 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_farmacos_021_api.py
git commit -m "test(farmacos): integración CEPA-021 esquema farmacológico (CA y TC cubiertos)"
```

---

## Task 7: API de recetas y alertas de revisión (CEPA-022)

Tests de integración para recetas y el proceso de alertas de 5 días.

**Files:**
- Test: `backend/tests/test_farmacos_022_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_022_api.py`:

```python
"""Tests de CEPA-022: gestión de recetas y alertas de revisión próxima."""

from datetime import date, timedelta


def _setup_registro(client, rut: str = "22.222.222-2") -> tuple[int, int]:
    """Crea ingreso + registro farmacológico; devuelve (ingreso_id, registro_id)."""
    ingreso_r = client.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente Receta",
            "sexo": "M",
            "edad": 50,
            "region": "Maule",
            "diagnostico": "F41",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert ingreso_r.status_code == 201, ingreso_r.text
    ingreso_id = ingreso_r.json()["id"]
    reg_r = client.post(
        "/api/v1/registro-farmacologico",
        json={
            "ingreso_id": ingreso_id,
            "medico_tratante": "Dr. López",
            "estado_farmacologico": "activo",
        },
    )
    assert reg_r.status_code == 201, reg_r.text
    return ingreso_id, reg_r.json()["id"]


# TC-022-01: CA-1 — receta vinculada al folio y visible
def test_crear_receta_vinculada_al_folio(as_admin):
    ingreso_id, _ = _setup_registro(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-06-20",
            "fecha_envio": "2026-06-05",
            "marca_medicamento": "Fluoxetina genérico",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["fecha_emision"] == "2026-06-01"
    assert body["fecha_revision"] == "2026-06-20"
    assert body["marca_medicamento"] == "Fluoxetina genérico"


# TC-022-01: Listar recetas del folio
def test_listar_recetas_del_folio(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="33.333.333-3")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-06-20",
            "marca_medicamento": "Fluoxetina",
        },
    )
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/recetas")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# TC-022-04: revisión anterior a emisión → 422
def test_receta_revision_anterior_a_emision_rechazada(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="44.444.444-4")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-10",
            "fecha_revision": "2026-06-05",
            "marca_medicamento": "Clonazepam",
        },
    )
    assert r.status_code == 422


# TC-022-02: CA-2 — alerta generada cuando revisión en próximos 5 días
def test_alerta_generada_para_revision_proxima(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="55.555.555-5")
    hoy = date.today()
    revision_en_1_dia = (hoy + timedelta(days=1)).isoformat()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": hoy.isoformat(),
            "fecha_revision": revision_en_1_dia,
            "marca_medicamento": "Sertralina",
        },
    )
    r = as_admin.post("/api/v1/registro-farmacologico/recetas/alertas/generar")
    assert r.status_code == 201, r.text
    alertas = r.json()
    assert len(alertas) >= 1
    tipos = [a["tipo"] for a in alertas]
    assert "revision_proxima" in tipos


# TC-022-03: CA-3 — alerta generada para revisión exactamente a 5 días (límite inclusivo)
def test_alerta_limite_inclusivo_5_dias(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="66.666.666-6")
    hoy = date.today()
    revision_en_5_dias = (hoy + timedelta(days=5)).isoformat()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": hoy.isoformat(),
            "fecha_revision": revision_en_5_dias,
            "marca_medicamento": "Litio",
        },
    )
    r = as_admin.post("/api/v1/registro-farmacologico/recetas/alertas/generar")
    assert r.status_code == 201
    ids_recetas_alertadas = [a["receta_id"] for a in r.json()]
    # debe haber al menos una alerta para esta receta
    assert len(ids_recetas_alertadas) >= 1


# TC-022-05: NO se genera alerta para revisión a 6 días
def test_no_alerta_para_revision_a_6_dias(as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="77.777.777-7")
    hoy = date.today()
    revision_en_6_dias = (hoy + timedelta(days=6)).isoformat()
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": hoy.isoformat(),
            "fecha_revision": revision_en_6_dias,
            "marca_medicamento": "Aripiprazol",
        },
    )
    r = as_admin.post("/api/v1/registro-farmacologico/recetas/alertas/generar")
    assert r.status_code == 201
    # La receta con revisión a 6 días NO debe aparecer en alertas
    for alerta in r.json():
        r_receta = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/recetas")
        receta_ids = [rec["id"] for rec in r_receta.json()]
        # ninguna alerta debe corresponder a una receta de este ingreso
        assert alerta["receta_id"] not in receta_ids


# TC-022-06: Auditor no puede crear ni generar alertas → 403
def test_auditor_no_puede_crear_receta(as_auditor, as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="88.888.888-8")
    r = as_auditor.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-06-20",
            "marca_medicamento": "X",
        },
    )
    assert r.status_code == 403


# TC-022-06: Auditor puede listar recetas → 200
def test_auditor_puede_listar_recetas(as_auditor, as_admin):
    ingreso_id, _ = _setup_registro(as_admin, rut="99.999.999-9")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/recetas",
        json={
            "fecha_emision": "2026-06-01",
            "fecha_revision": "2026-07-01",
            "marca_medicamento": "Quetiapina",
        },
    )
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}/recetas")
    assert r.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_022_api.py -v`
Expected: algunos tests pueden fallar por conflicto de ruta con el endpoint `/{ingreso_id}` vs `/recetas/alertas/generar` (FastAPI evalúa rutas en orden de registro). Ver Notas de cierre.

- [ ] **Step 3: Corregir el orden de rutas en el router si hay conflicto**

En `backend/app/routers/farmacos.py`, mover el endpoint `POST /recetas/alertas/generar` **antes** del endpoint `GET /{ingreso_id}` para evitar que FastAPI intente parsear `"recetas"` como un `ingreso_id` entero:

```python
# ── Alertas de revisión (CEPA-022 RN-3) ──────────────────────────────────────
# IMPORTANTE: este endpoint debe registrarse ANTES de /{ingreso_id}/* para que
# FastAPI no intente resolver "recetas" como un entero de ingreso_id.

@router.post(
    "/recetas/alertas/generar",
    response_model=list[AlertaRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def generar_alertas_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Ejecuta el proceso de alertas de revisión próxima (ventana 5 días)."""
    alertas = generar_alertas_revision(db)
    for alerta in alertas:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="alerta",
            entity_id=str(alerta.id),
        )
    db.commit()
    for alerta in alertas:
        db.refresh(alerta)
    return alertas
```

Reubicar este bloque antes del primer `@router.get("/{ingreso_id}", ...)` en el archivo. El resto del router no cambia.

- [ ] **Step 4: Correr el test y verificar que pasan todos**

Run: `uv run pytest tests/test_farmacos_022_api.py -v`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/farmacos.py backend/tests/test_farmacos_022_api.py
git commit -m "test(farmacos): integración CEPA-022 recetas y alertas de revisión (CA y TC cubiertos)"
```

---

## Task 8: API de seguimiento de tratamiento (CEPA-023)

Tests de integración end-to-end para los endpoints de seguimiento.

**Files:**
- Test: `backend/tests/test_farmacos_023_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_farmacos_023_api.py`:

```python
"""Tests de CEPA-023: seguimiento de tratamiento (disminución / cambio de esquema)."""


def _setup_registro(client, rut: str = "12.121.212-1") -> int:
    ingreso_r = client.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente Seguimiento",
            "sexo": "M",
            "edad": 45,
            "region": "Maule",
            "diagnostico": "F33",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert ingreso_r.status_code == 201, ingreso_r.text
    ingreso_id = ingreso_r.json()["id"]
    reg_r = client.post(
        "/api/v1/registro-farmacologico",
        json={
            "ingreso_id": ingreso_id,
            "medico_tratante": "Dr. Ramos",
            "estado_farmacologico": "activo",
        },
    )
    assert reg_r.status_code == 201, reg_r.text
    return ingreso_id


# TC-023-01: CA-3 — disminución=No, cambio=No, solo observaciones → OK
def test_seguimiento_solo_observaciones(as_admin):
    ingreso_id = _setup_registro(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={
            "disminucion_farmacos": False,
            "cambio_esquema": False,
            "observaciones": "Paciente estable.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["disminucion_farmacos"] is False
    assert body["cambio_esquema"] is False
    assert body["observaciones"] == "Paciente estable."
    assert body["plan_disminucion"] is None
    assert body["detalle_cambio"] is None


# TC-023-01: disminución=Sí con plan → OK
def test_seguimiento_disminucion_con_plan(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="13.131.313-2")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={
            "disminucion_farmacos": True,
            "plan_disminucion": "Bajar 25 mg/semana hasta suspender.",
            "cambio_esquema": False,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["plan_disminucion"] == "Bajar 25 mg/semana hasta suspender."


# TC-023-02: CA-1 — disminución=Sí sin plan → 422
def test_disminucion_sin_plan_rechazada(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="14.141.414-3")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": True, "cambio_esquema": False},
    )
    assert r.status_code == 422
    assert "plan_disminucion" in r.text


# TC-023-03: CA-2 — cambio de esquema=Sí sin detalle → 422
def test_cambio_esquema_sin_detalle_rechazado(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="15.151.515-4")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": True},
    )
    assert r.status_code == 422
    assert "detalle_cambio" in r.text


# TC-023-01 completo: disminución=Sí + cambio=No + observaciones
def test_seguimiento_completo_disminucion(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="16.161.616-5")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={
            "disminucion_farmacos": True,
            "plan_disminucion": "Bajar 25 mg/semana.",
            "cambio_esquema": False,
            "observaciones": "Revisión semanal.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["plan_disminucion"] == "Bajar 25 mg/semana."
    assert body["observaciones"] == "Revisión semanal."


# Listar seguimientos del folio
def test_listar_seguimientos(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="17.171.717-6")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": False},
    )
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# TC-023-05: Auditor no puede crear seguimiento → 403
def test_auditor_no_puede_crear_seguimiento(as_auditor, as_admin):
    ingreso_id = _setup_registro(as_admin, rut="18.181.818-7")
    r = as_auditor.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": False},
    )
    assert r.status_code == 403


# TC-023-05: Auditor puede leer seguimiento → 200
def test_auditor_puede_leer_seguimiento(as_auditor, as_admin):
    ingreso_id = _setup_registro(as_admin, rut="19.191.919-8")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": False},
    )
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento")
    assert r.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_farmacos_023_api.py -v`
Expected: FAIL — la ruta de seguimiento puede no estar registrada correctamente aún.

- [ ] **Step 3: Correr y verificar que pasan todos**

Run: `uv run pytest tests/test_farmacos_023_api.py -v`
Expected: `8 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_farmacos_023_api.py
git commit -m "test(farmacos): integración CEPA-023 seguimiento de tratamiento (CA y TC cubiertos)"
```

---

## Task 9: Verificación integral de la épica

Suite completa + lint + verificación de migración y auditoría.

**Files:** ninguno nuevo.

- [ ] **Step 1: Correr toda la suite de EPIC-02**

Run: `uv run pytest tests/test_farmacos_enums.py tests/test_farmacos_model.py tests/test_farmacos_migrations.py tests/test_farmacos_schemas.py tests/test_farmacos_020_api.py tests/test_farmacos_021_api.py tests/test_farmacos_022_api.py tests/test_farmacos_023_api.py -v`
Expected: todos los tests en verde.

- [ ] **Step 2: Correr la suite completa del proyecto (regresión)**

Run: `uv run pytest -v`
Expected: todos los tests (Fundación + EPIC-00 + EPIC-01 + EPIC-02) en verde.

- [ ] **Step 3: Lint**

Run: `uv run ruff check .`
Expected: sin errores.

- [ ] **Step 4: Verificar el ciclo completo de migraciones Alembic**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: aplica desde `base` hasta `head` (0001 … 0024) sin errores. Esto valida la portabilidad de toda la cadena.

- [ ] **Step 5: Verificar que la auditoría se registra en operaciones de escritura**

Run (con el servidor levantado en otra terminal `uv run uvicorn app.main:app --reload`):
```bash
# Crear un registro y verificar que aparece en audit_log
curl -s -X POST http://localhost:8000/api/v1/registro-farmacologico \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -H "content-type: application/json" \
  -d '{"ingreso_id": 1, "medico_tratante": "Dr. X", "estado_farmacologico": "activo"}'

curl -s http://localhost:8000/api/v1/audit-log | python3 -m json.tool | grep '"entity": "reg_farmacologico"'
```
Expected: al menos una entrada con `"entity": "reg_farmacologico"` y `"action": "CREATE"`. Detener con Ctrl-C.

- [ ] **Step 6: Commit final si quedó algo sin commitear**

```bash
git add -A
git commit -m "chore(farmacos): verificación integral EPIC-02 — suite verde, lint OK, migraciones OK" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Descripción | Tasks que la implementan |
|----------|-------------|--------------------------|
| **CEPA-020** | Registro farmacológico vinculado al folio | Task 1 (enums), Task 2 (modelo + migración), Task 4 (schemas), Task 5 (servicio + API + tests) |
| **CEPA-021** | Historial clínico farmacológico y esquema | Task 1 (enums FrecuenciaFarmaco), Task 3 (migración esquema_indicacion), Task 4 (schemas), Task 5 (servicio), Task 6 (tests integración) |
| **CEPA-022** | Gestión de recetas y alerta de revisión | Task 3 (migraciones receta + alerta), Task 4 (schemas con validación de fechas), Task 5 (servicio crear_receta + generar_alertas), Task 7 (tests integración) |
| **CEPA-023** | Seguimiento de tratamiento | Task 3 (migración seguim_tratamiento), Task 4 (schemas con model_validator), Task 5 (servicio crear_seguimiento), Task 8 (tests integración) |

**Criterios de Aceptación cubiertos por Test Cases:**

| CA | TC | Test |
|----|-----|------|
| CEPA-020 CA-1 | TC-020-01 | `test_crear_registro_farmacologico_vinculado_al_folio` |
| CEPA-020 CA-2 | TC-020-01, TC-020-02 | `test_obtener_registro_por_ingreso_id` |
| CEPA-020 CA-3 | TC-020-03 | `test_crear_sin_medico_tratante_rechazado`, `test_crear_sin_estado_rechazado` |
| CEPA-020 RN-4 | TC-020-04 | `test_reingreso_mismo_folio_reactiva_registro` |
| CEPA-020 RN-5 | TC-020-05 | `test_auditor_no_puede_crear_registro`, `test_auditor_puede_leer_registro` |
| CEPA-021 CA-1 | TC-021-01 | `test_antecedentes_guardados_vinculados_al_folio`, `test_agregar_indicacion_actual` |
| CEPA-021 CA-2 | TC-021-01 | `test_agregar_indicacion_actual` |
| CEPA-021 CA-3 | TC-021-03 | `test_farmaco_extra_sistema_aceptado` |
| CEPA-021 RN-2 | TC-021-04 | `test_nueva_indicacion_no_borra_la_previa` |
| CEPA-021 RN-5 | TC-021-02, TC-021-05 | `test_indicacion_sin_dosis_rechazada`, `test_auditor_no_puede_agregar_indicacion` |
| CEPA-022 CA-1 | TC-022-01 | `test_crear_receta_vinculada_al_folio`, `test_listar_recetas_del_folio` |
| CEPA-022 CA-2 | TC-022-02 | `test_alerta_generada_para_revision_proxima` |
| CEPA-022 RN-3 (límite) | TC-022-03 | `test_alerta_limite_inclusivo_5_dias` |
| CEPA-022 RN-3 (fuera) | TC-022-05 | `test_no_alerta_para_revision_a_6_dias` |
| CEPA-022 RN-5 | TC-022-04 | `test_receta_revision_anterior_a_emision_rechazada` |
| CEPA-022 RN-6 | TC-022-06 | `test_auditor_no_puede_crear_receta`, `test_auditor_puede_listar_recetas` |
| CEPA-023 CA-1 | TC-023-02 | `test_disminucion_sin_plan_rechazada` |
| CEPA-023 CA-2 | TC-023-03 | `test_cambio_esquema_sin_detalle_rechazado` |
| CEPA-023 CA-3 | TC-023-04 | `test_seguimiento_solo_observaciones` |
| CEPA-023 RN-5 | TC-023-05 | `test_auditor_no_puede_crear_seguimiento`, `test_auditor_puede_leer_seguimiento` |

---

## Notas de cierre

### Marcadores que resolver antes del loop

1. **`<RESOLVER: alembic heads>` en la migración `0020_crear_reg_farmacologico.py`**
   Ejecutar `uv run alembic heads` desde `backend/` con la rama de EPIC-01 en `main`. El valor que aparezca (p. ej. `"001x"` o `"0015"`) es el `down_revision` correcto para la primera migración de esta épica. Sustituir el marcador antes de correr el loop.

2. **Firmas de `app/auth/deps.py` (de EPIC-00)**
   Verificar antes del loop que:
   - `get_current_user` devuelve un objeto con atributo `.username` (se usa en `record_audit`).
   - `require_role(*roles)` devuelve una dependencia FastAPI compatible con `Depends(require_role(...))`.
   Si la firma difiere, ajustar los routers (`farmacos.py`) en consecuencia.

3. **Firma de `record_audit` (de EPIC-00)**
   Verificar que `app.audit.service.record_audit(db, actor=..., action=..., entity=..., entity_id=...)` es la firma real (keyword arguments). Si EPIC-00 la implementó como posicionales, ajustar las llamadas en el servicio y el router.

4. **Fixtures `as_admin`, `as_coordinacion`, `as_auditor` (de EPIC-00)**
   Verificar que los tres fixtures devuelven un `TestClient` con headers JWT pre-configurados. Si el fixture recibe el `db_session` como argumento o tiene otra forma, actualizar los tests de esta épica (`test_farmacos_020..023_api.py`).

5. **Tabla `ingreso` de EPIC-01**
   La migración `0020` referencia `ingreso.id`. Confirmar que la revisión head de EPIC-01 incluye la tabla `ingreso` antes de crear la FK.

### Decisiones de negocio abiertas

- **Catálogo de `EstadoFarmacologico`:** el spec indica "pendiente confirmar el catálogo con Coordinación". El plan usa `{activo, suspendido, completado, pendiente}`. Si se amplía, basta con agregar valores al Enum y actualizar los tests de schema.
- **Catálogo de medicamentos institucional (CEPA-021 RN-3):** el spec deja abierto si el catálogo viene de una tabla dedicada o se carga manualmente. Este plan no crea tabla de catálogo (fármaco se guarda como texto libre + flag `extra_sistema`); si Coordinación decide proveer un catálogo estructurado, se implementará en una Task adicional sin romper lo ya construido.
- **Redirección de alerta (D1, CEPA-022 RN-4):** la alerta in-app se escribe en tabla `alerta` pero no se notifica todavía a ningún usuario; el canal real (panel del administrativo asignado) lo implementa EPIC-10. Verificar con Coordinación si el `administrativo_asignado` debe quedar como FK en `alerta` desde esta épica.
- **Sincronización cambio de esquema → EsquemaIndicacion (CEPA-023 RN-2):** cuando `cambio_esquema=True` en el seguimiento, el spec sugiere reflejar el cambio en el esquema activo para evitar doble digitación. Este plan registra la bandera + detalle en texto; la sincronización automática es una mejora futura (ver Notas de CEPA-023). Confirmar con Coordinación si se requiere en v1.
- **Estadísticas de fármacos (D7):** las estadísticas por tratamiento, programa y profesional se implementan en EPIC-09 (Reportería). Esta épica captura los datos estructurados (`extra_sistema`, `medicamento`, `dosis`, `frecuencia`, `vigente`) que los alimentarán.
