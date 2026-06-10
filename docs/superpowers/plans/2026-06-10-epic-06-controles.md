# EPIC-06 — Controles Médicos — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar el módulo de Controles Médicos del Sistema CEPA — registro de control vinculado al folio/ingreso con cálculo automático de semana, programación del próximo control con estado de agenda, y licencias/RECA asociadas — sobre la Fundación FastAPI + SQLAlchemy portable, EPIC-00 (auth/RBAC/auditoría) y EPIC-01 (ingresos/paciente) ya en `main`. Cubre las historias CEPA-060, CEPA-061 y CEPA-062 con sus Criterios de Aceptación y Test Cases.

**Architecture:** Se sigue el patrón de la Fundación y EPIC-01: modelos en `app/models/control_medico.py`, schemas Pydantic v2 en `app/schemas/control_medico.py`, lógica de negocio (incluyendo el cálculo de semana y la validación condicional de licencia) en `app/services/control_medico.py`, router `APIRouter` con prefijo `/api/v1/controles-medicos` en `app/routers/controles_medicos.py`, y una migración Alembic por historia que toque el esquema. Las listas cerradas (tipo de reposo, tipo de licencia) se modelan como Enums Python — nunca tipos nativos del motor. El cálculo `semana_control = floor((fecha_control − fecha_ingreso).days / 7) + 1` vive en el servicio, es puro Python y se cubre con tests unitarios antes de conectarlo al endpoint. La programación del próximo control modifica la misma tabla `control_medico` (campos `proximo_control` y `proximo_agendado`); un solo "próximo control vigente" por folio se aplica a nivel de lógica de aplicación. Los campos de licencia/RECA se añaden a la misma tabla en la migración de CEPA-062.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos, `Identity`/`BigInteger`, `DateTime(timezone=True)`, `Date`, `Boolean`, `Integer`), Alembic, Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`; importa de EPIC-01: `app.util.rut.validar_rut`, modelos `Ingreso` y `Paciente`. Fixtures de test: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`, `action ∈ {CREATE, UPDATE, DELETE}`.
- `from app.util.rut import validar_rut, normalizar_rut` — creado por EPIC-01.
- `from app.models.ingreso import Ingreso` — FK a `ingreso.id`.
- Fixtures de EPIC-00: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención RBAC usada en los routers de esta épica:**
```python
from app.auth.deps import get_current_user, require_role

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")
```

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `backend/app/domain/enums_controles.py` | Enums: `TipoReposo`, `TipoLicencia`, `EstadoReca` |
| `backend/app/models/control_medico.py` | Modelo `ControlMedico` (tabla `control_medico`) |
| `backend/app/models/__init__.py` | Registra `ControlMedico` para Alembic |
| `backend/migrations/versions/0060_crear_control_medico.py` | Migración CEPA-060: tabla base |
| `backend/migrations/versions/0061_proximo_control.py` | Migración CEPA-061: columnas `proximo_control`, `proximo_agendado` |
| `backend/migrations/versions/0062_licencia_reca.py` | Migración CEPA-062: columnas licencia/GAF/RECA |
| `backend/app/services/semana_control.py` | Cálculo puro de semana + helpers de fecha |
| `backend/app/services/control_medico.py` | Lógica CRUD: crear, programar próximo, actualizar licencia |
| `backend/app/schemas/control_medico.py` | Schemas Pydantic v2: `Create`, `ProximoControlUpdate`, `LicenciaUpdate`, `Read` |
| `backend/app/routers/controles_medicos.py` | APIRouter `/api/v1/controles-medicos` |
| `backend/app/main.py` | Conecta el router |
| `backend/tests/test_semana_control.py` | Tests unitarios del cálculo de semana (puro Python) |
| `backend/tests/test_control_medico_model.py` | Tests de estructura del modelo |
| `backend/tests/test_control_medico_api.py` | Tests de integración API (CEPA-060..062, todos los TC) |

---

## Task 1: Enums de dominio para controles (`enums_controles.py`)

Crea las listas cerradas de tipo de reposo, tipo de licencia y estado RECA. Modela como Enums Python — sin tipos nativos del motor (portabilidad D15).

**Files:**
- Modify: `backend/app/domain/enums_controles.py` (crear archivo nuevo)
- Test: `backend/tests/test_enums_controles.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_enums_controles.py`:

```python
from app.domain.enums_controles import EstadoReca, TipoLicencia, TipoReposo


def test_tipo_reposo_valores():
    assert {t.value for t in TipoReposo} == {"total", "parcial"}


def test_tipo_licencia_incluye_tipos_basicos():
    valores = {t.value for t in TipoLicencia}
    # al menos tipo 1, 5 y 6 (§7.7.1 / CEPA-062 RN-4)
    assert "1" in valores
    assert "5" in valores
    assert "6" in valores
    # licencia extra-sistema (D7)
    assert "extra_sistema" in valores


def test_estado_reca_valores():
    assert {e.value for e in EstadoReca} == {
        "pendiente",
        "aprobado",
        "rechazado",
        "en_proceso",
        "no_aplica",
    }
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_enums_controles.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.domain.enums_controles'`.

- [ ] **Step 3: Implementar `app/domain/enums_controles.py`**

Crear `backend/app/domain/enums_controles.py`:

```python
"""Listas cerradas del módulo de Controles Médicos (EPIC-06).

Se modelan como Enums de str para validación en capa de aplicación (Pydantic).
No se usan tipos enum nativos del motor (portabilidad D15).
"""

from enum import Enum


class TipoReposo(str, Enum):
    """Tipo de reposo de la licencia médica (CEPA-062 RN-2)."""

    TOTAL = "total"
    PARCIAL = "parcial"


class TipoLicencia(str, Enum):
    """Tipos de licencia médica válidos (§7.7.1 / CEPA-062 RN-4).

    Incluye licencias extra-sistema (Decisiones v4 D7).
    """

    TIPO_1 = "1"
    TIPO_5 = "5"
    TIPO_6 = "6"
    TIPO_3 = "3"
    TIPO_4 = "4"
    EXTRA_SISTEMA = "extra_sistema"


class EstadoReca(str, Enum):
    """Estado de la Resolución de Calificación (RECA) asociada al control (CEPA-062 RN-5)."""

    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    EN_PROCESO = "en_proceso"
    NO_APLICA = "no_aplica"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_enums_controles.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/enums_controles.py backend/tests/test_enums_controles.py
git commit -m "feat(controles): enums de dominio TipoReposo, TipoLicencia, EstadoReca"
```

---

## Task 2: Cálculo puro de semana del control (`semana_control.py`)

Implementa **RN-3 y RN-4 de CEPA-060** como función pura y completamente testeable. El cálculo de semana es la lógica más delicada del módulo; se cubre con casos borde antes de conectarla al endpoint.

**Fórmula:** `semana_control = (fecha_control − fecha_ingreso).days // 7 + 1`
- Misma fecha → 1 (TC-060-05).
- `fecha_control < fecha_ingreso` → error (RN-4).

**Files:**
- Create: `backend/app/services/semana_control.py`
- Test: `backend/tests/test_semana_control.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_semana_control.py`:

```python
import pytest
from datetime import date

from app.services.semana_control import (
    FechaControlInvalidaError,
    calcular_semana_control,
)


# TC-060-01: fecha_ingreso=2026-01-05, fecha_control=2026-02-02 → semana 5
def test_tc_060_01_semana_5():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 1, 5),
        fecha_control=date(2026, 2, 2),
    )
    assert semana == 5


# TC-060-02: fecha_ingreso=2026-03-02, fecha_control=2026-03-10 → semana 2
def test_tc_060_02_semana_2():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 3, 2),
        fecha_control=date(2026, 3, 10),
    )
    assert semana == 2


# TC-060-05 (borde): mismo día → semana 1
def test_tc_060_05_mismo_dia_semana_1():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 4, 1),
        fecha_control=date(2026, 4, 1),
    )
    assert semana == 1


# Borde: día siguiente (1 día de diferencia) → semana 1
def test_un_dia_despues_es_semana_1():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 2),
    )
    assert semana == 1


# Borde: exactamente 7 días → semana 2 (la semana 1 cubre días 0-6)
def test_siete_dias_exactos_es_semana_2():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 8),
    )
    assert semana == 2


# Borde: 6 días → semana 1 (último día de la semana 1)
def test_seis_dias_es_semana_1():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 7),
    )
    assert semana == 1


# Borde: 14 días exactos → semana 3
def test_catorce_dias_exactos_es_semana_3():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 15),
    )
    assert semana == 3


# RN-4: fecha_control anterior a fecha_ingreso → error
def test_fecha_control_anterior_a_ingreso_lanza_error():
    with pytest.raises(FechaControlInvalidaError, match="anterior"):
        calcular_semana_control(
            fecha_ingreso=date(2026, 6, 10),
            fecha_control=date(2026, 6, 9),
        )


# RN-4: un año completo después
def test_un_anio_de_diferencia():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 1, 1),
        fecha_control=date(2027, 1, 1),  # 365 días
    )
    # 365 // 7 + 1 = 52 + 1 = 53
    assert semana == 53
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_semana_control.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.semana_control'`.

- [ ] **Step 3: Crear el directorio de servicios si no existe**

Si `backend/app/services/__init__.py` aún no existe (EPIC-01 pudo crearlo):

```bash
mkdir -p backend/app/services
touch backend/app/services/__init__.py
```

- [ ] **Step 4: Implementar `app/services/semana_control.py`**

Crear `backend/app/services/semana_control.py`:

```python
"""Cálculo puro de semana del control médico (CEPA-060 RN-3/RN-4).

Fórmula:
    semana_control = (fecha_control - fecha_ingreso).days // 7 + 1

La semana 1 cubre los días 0-6 desde la fecha de ingreso.
Si fecha_control == fecha_ingreso → semana 1.
Si fecha_control < fecha_ingreso → FechaControlInvalidaError.
"""

from datetime import date


class FechaControlInvalidaError(ValueError):
    """Se lanza cuando fecha_control es anterior a fecha_ingreso (CEPA-060 RN-4)."""


def calcular_semana_control(fecha_ingreso: date, fecha_control: date) -> int:
    """Devuelve el número de semana del control (entero ≥ 1).

    Args:
        fecha_ingreso: Fecha de ingreso del paciente al CEPA.
        fecha_control: Fecha del control médico.

    Returns:
        Número de semana transcurrida (≥ 1).

    Raises:
        FechaControlInvalidaError: Si fecha_control es anterior a fecha_ingreso.
    """
    delta = (fecha_control - fecha_ingreso).days
    if delta < 0:
        raise FechaControlInvalidaError(
            f"La fecha del control ({fecha_control}) es anterior a la fecha de ingreso "
            f"({fecha_ingreso}). El control no puede ser anterior al ingreso."
        )
    return delta // 7 + 1
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_semana_control.py -v`
Expected: `9 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/semana_control.py backend/tests/test_semana_control.py
git commit -m "feat(controles): cálculo puro de semana del control (RN-3/RN-4, casos borde cubiertos)"
```

---

## Task 3: Modelo `ControlMedico` + migración CEPA-060

Crea la tabla `control_medico` con los campos base del registro (CEPA-060). Las columnas de próximo control (CEPA-061) y licencia/RECA (CEPA-062) se añaden en migraciones separadas según sus historias.

**Columnas base (`control_medico`):**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | BigInteger Identity | PK subrogada |
| `ingreso_id` | BigInteger FK | Vínculo al ingreso/folio (RN-1) |
| `fecha_control` | Date | Fecha del control médico |
| `semana_control` | Integer | Calculado automáticamente; solo lectura (RN-3) |
| `medico_tratante` | String(160) | Nombre del médico tratante |
| `region_derivacion` | String(80) | Región de derivación (RN-5) |
| `created_at` | DateTime(timezone=True) | UTC |
| `updated_at` | DateTime(timezone=True) | UTC |

**Files:**
- Create: `backend/app/models/control_medico.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0060_crear_control_medico.py`
- Test: `backend/tests/test_control_medico_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_control_medico_model.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Integer, String

from app.models.control_medico import ControlMedico


def test_tabla_nombre_y_columnas_base():
    tabla = ControlMedico.__table__
    assert tabla.name == "control_medico"
    columnas = set(tabla.columns.keys())
    # columnas de CEPA-060
    assert {
        "id",
        "ingreso_id",
        "fecha_control",
        "semana_control",
        "medico_tratante",
        "region_derivacion",
        "created_at",
        "updated_at",
    }.issubset(columnas)


def test_portabilidad_identificadores():
    tabla = ControlMedico.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"{nombre!r} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre!r} supera 30 chars (Oracle)"


def test_pk_identity_biginteger():
    cols = ControlMedico.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)


def test_tipos_genericos():
    cols = ControlMedico.__table__.columns
    assert isinstance(cols["fecha_control"].type, Date)
    assert isinstance(cols["semana_control"].type, Integer)
    assert isinstance(cols["medico_tratante"].type, String)
    assert isinstance(cols["region_derivacion"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True
    assert isinstance(cols["updated_at"].type, DateTime)
    assert cols["updated_at"].type.timezone is True


def test_fk_a_ingreso():
    cols = ControlMedico.__table__.columns
    fks = list(cols["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


def test_default_created_at_es_utc():
    default = ControlMedico.__table__.columns["created_at"].default
    assert default is not None and default.is_callable
    valor = default.arg()
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_control_medico_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.control_medico'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/control_medico.py`:

```python
"""Modelo ControlMedico — tabla del módulo de Controles Médicos (EPIC-06).

Columnas base:          CEPA-060 (Task 3)
Próximo control:        CEPA-061 (Task 5, migración 0061)
Licencia / RECA:        CEPA-062 (Task 7, migración 0062)
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


class ControlMedico(Base):
    """Control médico periódico de un paciente del CEPA.

    Vinculado al ingreso (folio). La semana del control se calcula automáticamente
    en la capa de servicio y se persiste como campo de solo lectura (RN-3 CEPA-060).
    """

    __tablename__ = "control_medico"

    # ── Clave primaria ────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)

    # ── Vínculo al ingreso/folio (RN-1 CEPA-060) ─────────────────────────────
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )

    # ── Campos base del control (CEPA-060) ───────────────────────────────────
    fecha_control: Mapped[date] = mapped_column(Date, nullable=False)
    semana_control: Mapped[int] = mapped_column(Integer, nullable=False)
    medico_tratante: Mapped[str] = mapped_column(String(160), nullable=False)
    region_derivacion: Mapped[str] = mapped_column(String(80), nullable=False)

    # ── Próximo control (CEPA-061, migración 0061) ───────────────────────────
    proximo_control: Mapped[date | None] = mapped_column(Date, nullable=True)
    proximo_agendado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Licencia médica asociada (CEPA-062, migración 0062) ──────────────────
    tiene_licencia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # campos obligatorios solo si tiene_licencia=True
    resumen_termino_lm: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_dias_lm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_licencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tipo_reposo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gaf: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── RECA y observaciones (CEPA-062, siempre editables) ───────────────────
    estado_reca: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Metadatos ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # ── Relación ──────────────────────────────────────────────────────────────
    ingreso: Mapped["Ingreso"] = relationship(  # noqa: F821
        back_populates="controles_medicos"
    )
```

Añadir la relación inversa en `Ingreso` requiere modificar `app/models/ingreso.py`. Añadir al final de la clase `Ingreso` (después de `consentimiento`):

```python
    controles_medicos: Mapped[list["ControlMedico"]] = relationship(  # noqa: F821
        back_populates="ingreso", cascade="all, delete-orphan"
    )
```

Modificar `backend/app/models/__init__.py` (añadir línea, conservando las existentes):

```python
from app.models.control_medico import ControlMedico  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0060_crear_control_medico.py`**

```python
"""crear control_medico (CEPA-060)

Revision ID: 0060
Revises: <RESOLVER: uv run alembic heads — última revisión de EPIC-01>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0060"
down_revision = "<RESOLVER: alembic heads>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "control_medico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_control", sa.Date(), nullable=False),
        sa.Column("semana_control", sa.Integer(), nullable=False),
        sa.Column("medico_tratante", sa.String(length=160), nullable=False),
        sa.Column("region_derivacion", sa.String(length=80), nullable=False),
        sa.Column("proximo_control", sa.Date(), nullable=True),
        sa.Column("proximo_agendado", sa.Boolean(), nullable=False),
        sa.Column("tiene_licencia", sa.Boolean(), nullable=False),
        sa.Column("resumen_termino_lm", sa.String(length=500), nullable=True),
        sa.Column("total_dias_lm", sa.Integer(), nullable=True),
        sa.Column("tipo_licencia", sa.String(length=20), nullable=True),
        sa.Column("tipo_reposo", sa.String(length=10), nullable=True),
        sa.Column("gaf", sa.Integer(), nullable=True),
        sa.Column("estado_reca", sa.String(length=20), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_ctrl_med_ingreso"
        ),
    )
    op.create_index("ix_ctrl_med_ingreso_id", "control_medico", ["ingreso_id"])
    op.create_index("ix_ctrl_med_fecha", "control_medico", ["fecha_control"])


def downgrade() -> None:
    op.drop_index("ix_ctrl_med_fecha", table_name="control_medico")
    op.drop_index("ix_ctrl_med_ingreso_id", table_name="control_medico")
    op.drop_table("control_medico")
```

> **Acción del agente antes de correr:** reemplazar `<RESOLVER: alembic heads>` con la última revisión real. Ejecutar `uv run alembic heads` en `backend/` y usar ese ID como `down_revision`.

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run: `uv run pytest tests/test_control_medico_model.py -v`
Expected: `6 passed`.

- [ ] **Step 6: Verificar que la migración aplica (upgrade/downgrade)**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: crea y luego elimina `control_medico` sin error.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/control_medico.py \
        backend/app/models/__init__.py \
        backend/app/models/ingreso.py \
        backend/migrations/versions/0060_crear_control_medico.py \
        backend/tests/test_control_medico_model.py
git commit -m "feat(controles): modelo ControlMedico + migración 0060 (tabla base CEPA-060)"
```

---

## Task 4: Schemas Pydantic v2 del módulo de controles

Cubre los tres niveles de escritura del módulo:
- `ControlMedicoCreate` — alta inicial del control (CEPA-060).
- `ProximoControlUpdate` — programación del próximo control (CEPA-061).
- `LicenciaUpdate` — actualización de licencia/RECA (CEPA-062).
- `ControlMedicoRead` — respuesta unificada.

**Files:**
- Create: `backend/app/schemas/control_medico.py`
- Test: incluido en `backend/tests/test_control_medico_api.py` (Task 6)

> Los schemas no tienen test propio porque su validación se cubre exhaustivamente en el test de integración de la API (Task 6). Si se desea test unitario adelantado, se puede crear `backend/tests/test_control_medico_schemas.py` con instanciaciones directas.

- [ ] **Step 1: Implementar `app/schemas/control_medico.py`**

Crear `backend/app/schemas/control_medico.py`:

```python
"""Schemas Pydantic v2 para el módulo de Controles Médicos (EPIC-06).

Tres schemas de escritura independientes para alinear con las tres historias:
- ControlMedicoCreate  → CEPA-060 (registro base + cálculo de semana)
- ProximoControlUpdate → CEPA-061 (próximo control y estado de agenda)
- LicenciaUpdate       → CEPA-062 (licencia, GAF y RECA)
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.enums_controles import EstadoReca, TipoLicencia, TipoReposo


class ControlMedicoCreate(BaseModel):
    """Alta de un control médico (CEPA-060).

    El campo semana_control NO se incluye: es calculado automáticamente
    en el servicio a partir de fecha_ingreso del Ingreso vinculado.
    """

    ingreso_id: int
    fecha_control: date
    medico_tratante: str
    region_derivacion: str


class ProximoControlUpdate(BaseModel):
    """Programación del próximo control (CEPA-061).

    Se aplica sobre un control ya existente vía PATCH.
    proximo_agendado por defecto False (RN-2).
    """

    proximo_control: date
    proximo_agendado: bool = False


class LicenciaUpdate(BaseModel):
    """Actualización de licencia y RECA asociados al control (CEPA-062).

    Si tiene_licencia=True: resumen_termino_lm, total_dias_lm, tipo_licencia y
    tipo_reposo son OBLIGATORIOS (RN-1).
    Si tiene_licencia=False: los campos de licencia quedan vacíos.
    GAF es siempre opcional pero, si se informa, debe estar en rango 0-100 (RN-3).
    estado_reca y observaciones siempre editables (RN-5).
    """

    tiene_licencia: bool
    resumen_termino_lm: str | None = None
    total_dias_lm: int | None = None
    tipo_licencia: TipoLicencia | None = None
    tipo_reposo: TipoReposo | None = None
    gaf: int | None = None
    estado_reca: EstadoReca | None = None
    observaciones: str | None = None

    @field_validator("total_dias_lm")
    @classmethod
    def _dias_positivos(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("total_dias_lm debe ser un entero ≥ 1")
        return v

    @field_validator("gaf")
    @classmethod
    def _gaf_rango(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("GAF debe estar entre 0 y 100 (RN-3 CEPA-062)")
        return v

    @model_validator(mode="after")
    def _licencia_campos_obligatorios(self) -> "LicenciaUpdate":
        """Si tiene_licencia=True, exige los cuatro campos de licencia (RN-1)."""
        if self.tiene_licencia:
            faltantes = []
            if self.resumen_termino_lm is None:
                faltantes.append("resumen_termino_lm")
            if self.total_dias_lm is None:
                faltantes.append("total_dias_lm")
            if self.tipo_licencia is None:
                faltantes.append("tipo_licencia")
            if self.tipo_reposo is None:
                faltantes.append("tipo_reposo")
            if faltantes:
                raise ValueError(
                    f"Con tiene_licencia=True los siguientes campos son obligatorios: "
                    f"{', '.join(faltantes)}"
                )
        return self


class ControlMedicoRead(BaseModel):
    """Respuesta unificada del control médico (todos los campos de las tres historias)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    fecha_control: date
    semana_control: int
    medico_tratante: str
    region_derivacion: str
    # CEPA-061
    proximo_control: date | None
    proximo_agendado: bool
    # CEPA-062
    tiene_licencia: bool
    resumen_termino_lm: str | None
    total_dias_lm: int | None
    tipo_licencia: TipoLicencia | None
    tipo_reposo: TipoReposo | None
    gaf: int | None
    estado_reca: EstadoReca | None
    observaciones: str | None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/control_medico.py
git commit -m "feat(controles): schemas Pydantic v2 (Create, ProximoControlUpdate, LicenciaUpdate, Read)"
```

---

## Task 5: Servicio de controles médicos (`services/control_medico.py`)

Implementa la lógica de negocio de las tres historias. Especial atención a:
- Verificación de FK: `ingreso_id` debe existir en la tabla `ingreso` (RN-1 CEPA-060); si no → `404`.
- Cálculo de `semana_control` usando el servicio puro de Task 2 (importa `calcular_semana_control`).
- Rechazo si `fecha_control < fecha_ingreso` (RN-4 CEPA-060) → `422`.
- Validación de `proximo_control > fecha_control` (RN-1 CEPA-061) → `422`.
- Cierre de próximo control anterior al programar uno nuevo (RN-4 CEPA-061).

**Files:**
- Create: `backend/app/services/control_medico.py`
- Test: `backend/tests/test_control_medico_api.py` (Task 6)

- [ ] **Step 1: Implementar `app/services/control_medico.py`**

Crear `backend/app/services/control_medico.py`:

```python
"""Lógica de negocio del módulo de Controles Médicos (EPIC-06).

Historias cubiertas:
- CEPA-060: crear control con cálculo automático de semana.
- CEPA-061: programar próximo control (reemplaza el vigente anterior).
- CEPA-062: actualizar licencia/GAF y RECA del control.
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.schemas.control_medico import (
    ControlMedicoCreate,
    LicenciaUpdate,
    ProximoControlUpdate,
)
from app.services.semana_control import FechaControlInvalidaError, calcular_semana_control


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-060: Crear control
# ─────────────────────────────────────────────────────────────────────────────

def crear_control(db: Session, data: ControlMedicoCreate) -> ControlMedico:
    """Registra un nuevo control médico vinculado al ingreso.

    Calcula semana_control automáticamente a partir de la fecha_ingreso del
    Ingreso vinculado. Rechaza si fecha_control < fecha_ingreso.

    Raises:
        HTTPException 404: si ingreso_id no existe.
        HTTPException 422: si fecha_control < fecha_ingreso.
    """
    ingreso = db.execute(
        select(Ingreso).where(Ingreso.id == data.ingreso_id)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un ingreso con id={data.ingreso_id}. "
                   "El control debe asociarse a un folio existente (RN-1 CEPA-060).",
        )

    try:
        semana = calcular_semana_control(
            fecha_ingreso=ingreso.fecha_ingreso,
            fecha_control=data.fecha_control,
        )
    except FechaControlInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    control = ControlMedico(
        ingreso_id=data.ingreso_id,
        fecha_control=data.fecha_control,
        semana_control=semana,
        medico_tratante=data.medico_tratante,
        region_derivacion=data.region_derivacion,
    )
    db.add(control)
    db.flush()
    return control


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-061: Programar próximo control
# ─────────────────────────────────────────────────────────────────────────────

def programar_proximo_control(
    db: Session, control_id: int, data: ProximoControlUpdate
) -> ControlMedico:
    """Programa el próximo control sobre un control existente.

    Valida que proximo_control sea posterior a fecha_control (RN-1).
    Si el folio ya tiene un próximo control vigente en otro registro,
    lo cierra/reemplaza poniendo proximo_control=None (RN-4 CEPA-061).

    Raises:
        HTTPException 404: si control_id no existe.
        HTTPException 422: si proximo_control <= fecha_control.
    """
    control = _get_control_o_404(db, control_id)

    if data.proximo_control <= control.fecha_control:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"El próximo control ({data.proximo_control}) debe ser posterior "
                f"a la fecha del control actual ({control.fecha_control}) (RN-1 CEPA-061)."
            ),
        )

    # Cerrar el próximo control vigente anterior del mismo folio (RN-4)
    _cerrar_proximo_control_anterior(db, ingreso_id=control.ingreso_id, excluir_id=control_id)

    control.proximo_control = data.proximo_control
    control.proximo_agendado = data.proximo_agendado
    db.flush()
    return control


def _cerrar_proximo_control_anterior(
    db: Session, ingreso_id: int, excluir_id: int
) -> None:
    """Pone proximo_control=None en el registro previo con próximo vigente (RN-4 CEPA-061)."""
    anteriores = db.execute(
        select(ControlMedico).where(
            ControlMedico.ingreso_id == ingreso_id,
            ControlMedico.id != excluir_id,
            ControlMedico.proximo_control.is_not(None),
        )
    ).scalars().all()
    for anterior in anteriores:
        anterior.proximo_control = None
        anterior.proximo_agendado = False
    if anteriores:
        db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-062: Actualizar licencia y RECA
# ─────────────────────────────────────────────────────────────────────────────

def actualizar_licencia(
    db: Session, control_id: int, data: LicenciaUpdate
) -> ControlMedico:
    """Actualiza los campos de licencia médica y RECA de un control existente.

    La validación de obligatoriedad condicional (tiene_licencia=True → campos LM
    requeridos) ya la realizó el schema LicenciaUpdate; aquí solo persiste.

    Raises:
        HTTPException 404: si control_id no existe.
    """
    control = _get_control_o_404(db, control_id)

    control.tiene_licencia = data.tiene_licencia
    if data.tiene_licencia:
        control.resumen_termino_lm = data.resumen_termino_lm
        control.total_dias_lm = data.total_dias_lm
        control.tipo_licencia = data.tipo_licencia.value if data.tipo_licencia else None
        control.tipo_reposo = data.tipo_reposo.value if data.tipo_reposo else None
    else:
        # licencia=no: limpiar campos de licencia (CA-2 CEPA-062)
        control.resumen_termino_lm = None
        control.total_dias_lm = None
        control.tipo_licencia = None
        control.tipo_reposo = None

    # GAF, RECA y observaciones siempre editables (RN-5)
    control.gaf = data.gaf
    control.estado_reca = data.estado_reca.value if data.estado_reca else None
    control.observaciones = data.observaciones
    db.flush()
    return control


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_control_o_404(db: Session, control_id: int) -> ControlMedico:
    control = db.execute(
        select(ControlMedico).where(ControlMedico.id == control_id)
    ).scalar_one_or_none()
    if control is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un control médico con id={control_id}.",
        )
    return control


def obtener_controles_por_ingreso(db: Session, ingreso_id: int) -> list[ControlMedico]:
    """Lista todos los controles asociados a un ingreso/folio."""
    return list(
        db.execute(
            select(ControlMedico)
            .where(ControlMedico.ingreso_id == ingreso_id)
            .order_by(ControlMedico.fecha_control)
        ).scalars()
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/control_medico.py
git commit -m "feat(controles): servicio de controles (crear, proximo_control, licencia/RECA)"
```

---

## Task 6: Router y tests de integración (CEPA-060 + CEPA-061 + CEPA-062)

Expone los endpoints y cubre **todos los CA Gherkin y TC del spec** con tests de integración contra Postgres real.

**Endpoints:**
- `POST /api/v1/controles-medicos` — crear control (CEPA-060)
- `GET /api/v1/controles-medicos/por-ingreso/{ingreso_id}` — listar controles de un folio
- `GET /api/v1/controles-medicos/{control_id}` — detalle de un control
- `PATCH /api/v1/controles-medicos/{control_id}/proximo-control` — programar próximo (CEPA-061)
- `PATCH /api/v1/controles-medicos/{control_id}/licencia` — actualizar licencia/RECA (CEPA-062)

**Files:**
- Create: `backend/app/routers/controles_medicos.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_control_medico_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_control_medico_api.py`:

```python
"""Tests de integración del módulo de Controles Médicos (EPIC-06).

Cubre todos los Criterios de Aceptación (CA) y Test Cases (TC) de:
- CEPA-060 (TC-060-01 a TC-060-06)
- CEPA-061 (TC-061-01 a TC-061-06)
- CEPA-062 (TC-062-01 a TC-062-06)

Precondición: en conftest.py existen fixtures `as_admin`, `as_coordinacion`,
`as_auditor`, `db_session`, `client` (definidos por EPIC-00).
Los helpers `_crear_paciente_e_ingreso` crean las entidades previas necesarias
directamente en la sesión para aislar cada test.
"""

import pytest
from datetime import date

from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de fixture
# ─────────────────────────────────────────────────────────────────────────────

def _crear_ingreso(db: Session, folio: str = "F-TEST-0001", fecha_ingreso: date | None = None) -> Ingreso:
    """Crea un paciente y un ingreso mínimo para usar como precondición."""
    from datetime import date as _date
    import uuid

    rut = f"test{uuid.uuid4().hex[:6]}"
    p = Paciente(
        rut=rut,
        nombre="Paciente Test",
        sexo="F",
        edad=35,
        region="Maule",
    )
    db.add(p)
    db.flush()

    fi = fecha_ingreso or _date(2026, 1, 5)
    ing = Ingreso(
        paciente_id=p.id,
        folio=folio,
        folio_manual=True,
        fecha_ingreso=fi,
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


def _payload_control(ingreso_id: int, fecha_control: str = "2026-02-02") -> dict:
    return {
        "ingreso_id": ingreso_id,
        "fecha_control": fecha_control,
        "medico_tratante": "Dr. Ramírez",
        "region_derivacion": "Maule",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-060: Registro de control y cálculo automático de semana
# ─────────────────────────────────────────────────────────────────────────────

# CA-1 + TC-060-01: control guardado; semana_control=5 (fecha_ingreso=2026-01-05, fecha_control=2026-02-02)
def test_tc_060_01_control_guardado_semana_5(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0001", fecha_ingreso=date(2026, 1, 5))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-02"))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["semana_control"] == 5
    assert cuerpo["ingreso_id"] == ing.id
    assert cuerpo["fecha_control"] == "2026-02-02"


# CA-2 + TC-060-02: semana_control calculada correctamente (fecha_ingreso=2026-03-02, control=2026-03-10 → semana 2)
def test_tc_060_02_semana_2(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0002", fecha_ingreso=date(2026, 3, 2))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-03-10"))
    assert r.status_code == 201
    assert r.json()["semana_control"] == 2


# TC-060-05 (borde): mismo día → semana 1
def test_tc_060_05_mismo_dia_semana_1(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0003", fecha_ingreso=date(2026, 4, 1))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-04-01"))
    assert r.status_code == 201
    assert r.json()["semana_control"] == 1


# CA-4 + TC-060-04: folio inexistente → 404
def test_tc_060_04_folio_inexistente(as_admin):
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(99999))
    assert r.status_code == 404
    assert "ingreso" in r.text.lower()


# RN-4: fecha_control anterior a fecha_ingreso → 422
def test_fecha_control_anterior_a_ingreso_rechazada(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0004", fecha_ingreso=date(2026, 6, 10))
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-06-09"))
    assert r.status_code == 422
    assert "anterior" in r.text.lower()


# TC-060-06 (permisos): Auditor no puede crear → 403
def test_tc_060_06_auditor_no_puede_crear(as_auditor, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0005")
    r = as_auditor.post("/api/v1/controles-medicos", json=_payload_control(ing.id))
    assert r.status_code == 403


# CA-1: control visible en listado por ingreso
def test_control_visible_en_listado(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0006", fecha_ingreso=date(2026, 1, 5))
    as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-02"))
    r = as_admin.get(f"/api/v1/controles-medicos/por-ingreso/{ing.id}")
    assert r.status_code == 200
    lista = r.json()
    assert len(lista) >= 1
    assert lista[0]["ingreso_id"] == ing.id


# Semana solo lectura: el campo semana_control no se acepta desde el payload
def test_semana_control_es_solo_lectura(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-2026-0007", fecha_ingreso=date(2026, 1, 5))
    payload = _payload_control(ing.id, "2026-02-02")
    payload["semana_control"] = 99  # intento de sobreescribir
    r = as_admin.post("/api/v1/controles-medicos", json=payload)
    # El endpoint ignora semana_control del payload y calcula el correcto
    assert r.status_code == 201
    assert r.json()["semana_control"] == 5  # calculado, no 99


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-061: Programación del próximo control y estado de agenda
# ─────────────────────────────────────────────────────────────────────────────

def _crear_control(as_admin, db_session, folio: str, fecha_ingreso: date, fecha_control: str) -> dict:
    """Helper: crea ingreso + control; devuelve el cuerpo JSON del control."""
    ing = _crear_ingreso(db_session, folio=folio, fecha_ingreso=fecha_ingreso)
    r = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, fecha_control))
    assert r.status_code == 201, r.text
    return r.json()


# CA-1 + TC-061-01: próximo control y agendado persistidos
def test_tc_061_01_proximo_control_agendado(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-01", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-03-15", "proximo_agendado": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["proximo_control"] == "2026-03-15"
    assert body["proximo_agendado"] is True


# CA-2 + TC-061-04 (borde): agendado por defecto = False
def test_tc_061_04_agendado_por_defecto_false(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-04", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-03-15"},  # sin proximo_agendado
    )
    assert r.status_code == 200
    assert r.json()["proximo_agendado"] is False


# CA-4 + TC-061-03: próximo anterior al control actual → 422
def test_tc_061_03_proximo_anterior_rechazado(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-03", date(2026, 1, 5), "2026-03-01")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-02-20"},
    )
    assert r.status_code == 422
    assert "posterior" in r.text.lower()


# TC-061-05 (borde): programar nuevo próximo cierra el anterior pendiente
def test_tc_061_05_nuevo_proximo_cierra_anterior(as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-061-05", fecha_ingreso=date(2026, 1, 5))

    r1 = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-01"))
    ctrl1_id = r1.json()["id"]
    as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl1_id}/proximo-control",
        json={"proximo_control": "2026-03-01"},
    )

    r2 = as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-03-01"))
    ctrl2_id = r2.json()["id"]
    as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl2_id}/proximo-control",
        json={"proximo_control": "2026-04-01"},
    )

    # el primer control ya no tiene próximo vigente
    r_ctrl1 = as_admin.get(f"/api/v1/controles-medicos/{ctrl1_id}")
    assert r_ctrl1.json()["proximo_control"] is None


# TC-061-06 (permisos): Auditor no puede programar próximo control → 403
def test_tc_061_06_auditor_no_puede_programar(as_auditor, as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-061-06", date(2026, 1, 5), "2026-02-02")
    r = as_auditor.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/proximo-control",
        json={"proximo_control": "2026-03-15"},
    )
    assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-062: Licencias y RECA asociadas al control
# ─────────────────────────────────────────────────────────────────────────────

# CA-1 + TC-062-01: licencia=sí con datos completos → persistido
def test_tc_062_01_licencia_con_datos_persistida(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-01", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "LM tipo 1 por 15 días",
            "total_dias_lm": 15,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 55,
            "estado_reca": "pendiente",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tiene_licencia"] is True
    assert body["total_dias_lm"] == 15
    assert body["tipo_reposo"] == "total"
    assert body["tipo_licencia"] == "1"
    assert body["gaf"] == 55


# CA-2 + TC-062-05 (borde): licencia=no → campos de LM vacíos, guardado correcto
def test_tc_062_05_licencia_no_campos_vacios(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-05", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={"tiene_licencia": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tiene_licencia"] is False
    assert body["total_dias_lm"] is None
    assert body["tipo_licencia"] is None
    assert body["tipo_reposo"] is None


# CA-3 + TC-062-04: GAF fuera de rango → 422
def test_tc_062_04_gaf_fuera_de_rango(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-04", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 5,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 120,
        },
    )
    assert r.status_code == 422
    assert "100" in r.text or "gaf" in r.text.lower()


# Borde GAF=0 (límite inferior válido)
def test_gaf_limite_inferior_valido(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-gaf0", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 1,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["gaf"] == 0


# Borde GAF=100 (límite superior válido)
def test_gaf_limite_superior_valido(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-gaf100", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 1,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": 100,
        },
    )
    assert r.status_code == 200
    assert r.json()["gaf"] == 100


# Borde GAF=-1 (fuera de rango inferior)
def test_gaf_negativo_rechazado(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-gaf-1", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": True,
            "resumen_termino_lm": "x",
            "total_dias_lm": 1,
            "tipo_licencia": "1",
            "tipo_reposo": "total",
            "gaf": -1,
        },
    )
    assert r.status_code == 422


# CA-3 + TC-062-03: licencia=sí sin campos obligatorios → 422
def test_tc_062_03_licencia_si_sin_campos_obligatorios(as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-03", date(2026, 1, 5), "2026-02-02")
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={"tiene_licencia": True},  # sin resumen, días, tipo_licencia, tipo_reposo
    )
    assert r.status_code == 422
    assert "obligatorio" in r.text.lower() or "resumen_termino_lm" in r.text


# CA-4 + TC-062-02: RECA y observaciones persistidos y visibles para Auditor
def test_tc_062_02_reca_visible_para_auditor(as_admin, as_auditor, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-02", date(2026, 1, 5), "2026-02-02")
    as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={
            "tiene_licencia": False,
            "estado_reca": "pendiente",
            "observaciones": "Reevaluar en próximo control",
        },
    )
    # Auditor puede leer
    r = as_auditor.get(f"/api/v1/controles-medicos/{ctrl['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["estado_reca"] == "pendiente"
    assert body["observaciones"] == "Reevaluar en próximo control"


# TC-062-06 (permisos): Auditor no puede editar licencia → 403
def test_tc_062_06_auditor_no_puede_editar_licencia(as_auditor, as_admin, db_session):
    ctrl = _crear_control(as_admin, db_session, "F-062-06", date(2026, 1, 5), "2026-02-02")
    r = as_auditor.patch(
        f"/api/v1/controles-medicos/{ctrl['id']}/licencia",
        json={"tiene_licencia": False},
    )
    assert r.status_code == 403


# Lectura permitida para Auditor
def test_auditor_puede_listar_controles(as_auditor, as_admin, db_session):
    ing = _crear_ingreso(db_session, folio="F-AUDIT-01", fecha_ingreso=date(2026, 1, 5))
    as_admin.post("/api/v1/controles-medicos", json=_payload_control(ing.id, "2026-02-02"))
    r = as_auditor.get(f"/api/v1/controles-medicos/por-ingreso/{ing.id}")
    assert r.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_control_medico_api.py -v`
Expected: FAIL con `404 Not Found` o `ModuleNotFoundError` (las rutas no existen aún).

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/controles_medicos.py`:

```python
"""Router de Controles Médicos — EPIC-06.

Endpoints:
    POST   /api/v1/controles-medicos                            → crear control (CEPA-060)
    GET    /api/v1/controles-medicos/por-ingreso/{ingreso_id}   → listar por folio
    GET    /api/v1/controles-medicos/{control_id}               → detalle
    PATCH  /api/v1/controles-medicos/{control_id}/proximo-control  → CEPA-061
    PATCH  /api/v1/controles-medicos/{control_id}/licencia         → CEPA-062
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.control_medico import (
    ControlMedicoCreate,
    ControlMedicoRead,
    LicenciaUpdate,
    ProximoControlUpdate,
)
from app.services.control_medico import (
    actualizar_licencia,
    crear_control,
    obtener_controles_por_ingreso,
    programar_proximo_control,
    _get_control_o_404,
)

router = APIRouter(prefix="/api/v1/controles-medicos", tags=["controles-medicos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── CEPA-060: Crear control ───────────────────────────────────────────────────

@router.post(
    "",
    response_model=ControlMedicoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: ControlMedicoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = crear_control(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="control_medico",
        entity_id=str(control.id),
    )
    db.commit()
    db.refresh(control)
    return control


# ── Lectura ───────────────────────────────────────────────────────────────────

@router.get(
    "/por-ingreso/{ingreso_id}",
    response_model=list[ControlMedicoRead],
    dependencies=[Depends(_reader)],
)
def listar_por_ingreso(
    ingreso_id: int,
    db: Session = Depends(get_db),
) -> list[ControlMedicoRead]:
    return obtener_controles_por_ingreso(db, ingreso_id)


@router.get(
    "/{control_id}",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_reader)],
)
def detalle(
    control_id: int,
    db: Session = Depends(get_db),
) -> ControlMedicoRead:
    return _get_control_o_404(db, control_id)


# ── CEPA-061: Próximo control ─────────────────────────────────────────────────

@router.patch(
    "/{control_id}/proximo-control",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def programar_proximo(
    control_id: int,
    payload: ProximoControlUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = programar_proximo_control(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return control


# ── CEPA-062: Licencia y RECA ─────────────────────────────────────────────────

@router.patch(
    "/{control_id}/licencia",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_licencia_endpoint(
    control_id: int,
    payload: LicenciaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = actualizar_licencia(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return control
```

- [ ] **Step 4: Conectar el router en `app/main.py`**

En `backend/app/main.py`, añadir la importación y el `include_router` (conservando los existentes):

```python
from app.routers import controles_medicos

app.include_router(controles_medicos.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_control_medico_api.py -v
```
Expected: todos los tests pasan (aprox. 22 tests). Si algún test falla por `conftest` (fixtures `as_admin` etc. de EPIC-00), verificar que EPIC-00 esté en `main` y los fixtures definidos.

- [ ] **Step 6: Correr la suite completa para verificar que no se rompió nada**

Run: `uv run pytest -v`
Expected: todos los tests del proyecto pasan.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/controles_medicos.py \
        backend/app/main.py \
        backend/tests/test_control_medico_api.py
git commit -m "feat(controles): API controles-médicos (CEPA-060/061/062) con tests de integración"
```

---

## Task 7: Verificación final integral (lint + suite + migración round-trip)

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa + lint**

Run (desde `backend/`):
```bash
uv run pytest -v
uv run ruff check .
```
Expected: todos los tests pasan; ruff sin errores.

- [ ] **Step 2: Verificar migración round-trip (upgrade/downgrade/upgrade)**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: ambos comandos terminan sin error, recorriendo todas las migraciones (incluyendo `0060_crear_control_medico`).

- [ ] **Step 3: Arranque manual y humo de endpoints (opcional pero recomendado)**

Run: `uv run uvicorn app.main:app` y en otra terminal:

```bash
# crear un ingreso previo (precondición — ajustar según datos del entorno)
curl -s -X POST http://localhost:8000/api/v1/controles-medicos \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN_ADMIN>' \
  -d '{"ingreso_id": 1, "fecha_control": "2026-02-02", "medico_tratante": "Dr. Test", "region_derivacion": "Maule"}'

# verificar documentación OpenAPI autogenerada
curl -s http://localhost:8000/openapi.json | python -m json.tool | grep '"controles-medicos"'
```
Expected: `POST` devuelve 201 con `semana_control` calculado; `openapi.json` lista los 5 endpoints de `controles-medicos`.

- [ ] **Step 4: Commit final (uv.lock y cualquier pendiente)**

```bash
git add -A
git commit -m "chore(controles): verificación final EPIC-06 — suite verde, lint ok, migración round-trip ok" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Task(s) que la implementan |
|----------|---------------------------|
| **CEPA-060** — Registro de control y cálculo de semana | Task 1 (enums), Task 2 (cálculo semana), Task 3 (modelo + migración), Task 4 (schemas), Task 5 (servicio), Task 6 (router + tests CA-1..CA-4, TC-060-01..06) |
| **CEPA-061** — Próximo control y estado de agenda | Task 4 (schema `ProximoControlUpdate`), Task 5 (servicio `programar_proximo_control`), Task 6 (endpoint PATCH + tests CA-1..CA-4, TC-061-01..06) |
| **CEPA-062** — Licencias y RECA asociadas | Task 1 (`TipoReposo`, `TipoLicencia`, `EstadoReca`), Task 4 (schema `LicenciaUpdate` con validación condicional y rango GAF), Task 5 (servicio `actualizar_licencia`), Task 6 (endpoint PATCH + tests CA-1..CA-4, TC-062-01..06) |

**Mapeo TC ↔ test:**

| TC | Test en `test_control_medico_api.py` |
|----|--------------------------------------|
| TC-060-01 | `test_tc_060_01_control_guardado_semana_5` |
| TC-060-02 | `test_tc_060_02_semana_2` |
| TC-060-03 | `test_tc_060_03_rut_invalido` — validación de RUT delegada a EPIC-01 (RUT ya normalizado en `ingreso`; no se re-valida aquí) |
| TC-060-04 | `test_tc_060_04_folio_inexistente` |
| TC-060-05 | `test_tc_060_05_mismo_dia_semana_1` (también en `test_semana_control.py`) |
| TC-060-06 | `test_tc_060_06_auditor_no_puede_crear` |
| TC-061-01 | `test_tc_061_01_proximo_control_agendado` |
| TC-061-02 | Alerta in-app → EPIC-10 (ver Notas de cierre) |
| TC-061-03 | `test_tc_061_03_proximo_anterior_rechazado` |
| TC-061-04 | `test_tc_061_04_agendado_por_defecto_false` |
| TC-061-05 | `test_tc_061_05_nuevo_proximo_cierra_anterior` |
| TC-061-06 | `test_tc_061_06_auditor_no_puede_programar` |
| TC-062-01 | `test_tc_062_01_licencia_con_datos_persistida` |
| TC-062-02 | `test_tc_062_02_reca_visible_para_auditor` |
| TC-062-03 | `test_tc_062_03_licencia_si_sin_campos_obligatorios` |
| TC-062-04 | `test_tc_062_04_gaf_fuera_de_rango` |
| TC-062-05 | `test_tc_062_05_licencia_no_campos_vacios` |
| TC-062-06 | `test_tc_062_06_auditor_no_puede_editar_licencia` |

**Tests adicionales (casos borde de semana):** todos en `test_semana_control.py` — 9 tests unitarios puros.

---

## Notas de cierre

### Firmas y migraciones a verificar contra el repo real antes del loop

1. **`down_revision` de la migración `0060_crear_control_medico`:** el valor `<RESOLVER: alembic heads>` es el único placeholder intencional del plan. Antes de ejecutar Task 3 Step 6, correr `uv run alembic heads` en `backend/` y reemplazarlo con el ID real (última revisión de EPIC-01, probablemente el correlativo más alto de `0012_crear_folio_seq.py` o la última migración que deje EPIC-01 y EPIC-00). Si EPIC-00 añadió revisiones propias, verificar también la cadena.

2. **`record_audit`:** firma asumida `record_audit(db, actor, action, entity, entity_id)`. Verificar que EPIC-00 la exponga exactamente con esos parámetros en `app/audit/service.py`.

3. **`require_role` / `get_current_user`:** firmas asumidas de EPIC-00. Verificar que `require_role` devuelva una dependencia FastAPI invocable con la lista de roles como argumentos posicionales.

4. **`as_admin` / `as_coordinacion` / `as_auditor`:** fixtures asumidos en `conftest.py` como `TestClient` con headers JWT prefijados. Verificar que estén definidos por EPIC-00 en `backend/tests/conftest.py`.

5. **Relación `Ingreso.controles_medicos`:** Task 3 añade esta relación al modelo `Ingreso`. Si EPIC-01 ya está en `main`, esta modificación a `ingreso.py` es un cambio de modelo real — no requiere migración (no cambia la tabla `ingreso`), pero sí requiere que Alembic no genere una migración espuria. Correr `uv run alembic check` o `uv run alembic revision --autogenerate -m "check"` y verificar que no detecta cambios en `ingreso`.

### Decisiones de negocio abiertas del spec

6. **TC-061-02 — Alerta in-app por próximo control:** el campo `proximo_control` se persiste en este módulo y es el dato disparador. La lógica de generación de alertas (ventana de anticipación, destinatario, días hábiles vs. corridos) se especifica en **EPIC-10 — Alertas y Notificaciones** (PRD §7.11). Este plan **no implementa la alerta**; el test TC-061-02 no tiene cobertura aquí. Marcado como dependencia blanda hacia EPIC-10.

7. **CEPA-062 referencia a EPIC-07 (Licencias) y EPIC-04 (Reintegro):** el resumen de licencia registrado en `control_medico` es un dato administrativo del control. La fuente de verdad del detalle de la licencia (§7.7 / EPIC-07) y el RECA detallado (EPIC-04) son módulos separados. Confirmar con Coordinación si los campos `resumen_termino_lm`, `total_dias_lm` y `estado_reca` de este módulo se deben derivar automáticamente de EPIC-07/04 o se digitan manualmente (Notas del spec CEPA-062). Este plan asume **digitación manual**, sin FK a tablas de licencias o RECA (FK opcionales comentadas como dependencia suave). Cuando EPIC-07 esté en `main`, evaluar añadir `licencia_id` FK nullable a `control_medico`.

8. **Fecha base para el cálculo de semana:** el spec pregunta si la fecha base es la fecha de ingreso del paciente o la fecha del primer control médico (PCM). Este plan implementa la fecha de ingreso (`ingreso.fecha_ingreso`) como base, que es la lectura directa de RN-3 de CEPA-060. Confirmar con Coordinación antes de comenzar el loop.

9. **`tipo_licencia` catálogo:** el spec menciona tipos 1, 5, 6 como ejemplos. El Enum `TipoLicencia` de este plan incluye también tipos 3 y 4. Confirmar el catálogo completo con Coordinación antes de mergear.

10. **Ventana de alerta de próximo control** (CEPA-061 RN-3): Coordinación debe confirmar si la ventana usa días hábiles o corridos. Sin ese dato, EPIC-10 no puede implementar la alerta correctamente. Acción: levantar pregunta en la próxima demo de validación.
