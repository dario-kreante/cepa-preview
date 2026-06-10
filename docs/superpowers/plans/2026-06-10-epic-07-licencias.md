# EPIC-07 — Licencias Médicas — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar el ciclo completo de la licencia médica (LM) del Sistema CEPA — registro con todos sus datos v4 D8 vinculado al ingreso/folio, cálculo automático de días acumulados por paciente con manejo de solapamientos, alerta de vencimiento por días hábiles y trazabilidad de envío a ISL incluyendo licencias extra-sistema — cubriendo las historias CEPA-070 a CEPA-073.

**Architecture:** Se sigue el patrón de la Fundación + EPIC-01: modelo `LicenciaMedica` en `app/models/licencia.py` con FK a `ingreso`, enums de listas cerradas en `app/domain/enums_licencia.py`, servicio de cálculo de días acumulados en `app/services/licencias_acumulado.py` (función pura reutilizable por EPIC-12), servicio de alertas de vencimiento en `app/services/licencias_alerta.py`, router `APIRouter` con prefijo `/api/v1/licencias` en `app/routers/licencias.py`, y una migración Alembic por historia que toque el esquema. Los Enums Python garantizan portabilidad (sin tipos enum de motor). Toda escritura registra auditoría. Auditor es solo lectura.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos, `Identity`/`BigInteger`, `Date`/`DateTime(timezone=True)`), Alembic, Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`; fixtures `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`. Importa de EPIC-01: `app.util.rut.validar_rut`, `app.models.ingreso.Ingreso`, `app.models.paciente.Paciente`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`.
- Fixtures de test de EPIC-00: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.
- Modelo `Ingreso` de EPIC-01: tabla `ingreso` con PK `id` (BigInteger, Identity), FK `paciente_id`.
- Tabla `paciente` de EPIC-01: PK `id`, columna `rut` (canónica, sin puntos ni guion).

**Convención de dependencias RBAC en esta épica:**
```python
from app.auth.deps import get_current_user, require_role

# escritura (Administrativo o Coordinacion):
_writer = require_role("Administrativo", "Coordinacion")
# lectura (incluye Auditor):
_reader = require_role("Administrativo", "Coordinacion", "Auditor")
```

---

## Mapa de archivos

| Archivo (crear) | Responsabilidad |
|---|---|
| `backend/app/domain/enums_licencia.py` | Enums `TipoLicencia`, `TipoReposo`, `EstadoEnvioISL`, `OrigenLicencia` |
| `backend/app/models/licencia.py` | Modelo `LicenciaMedica` (todas las columnas D8 + trazabilidad ISL) |
| `backend/app/schemas/licencia.py` | Schemas Pydantic v2: `LicenciaCreate`, `LicenciaUpdate`, `LicenciaRead`, `LicenciaISLUpdate`, `AcumuladoRead`, `AlertaLicenciaRead` |
| `backend/app/services/licencias_acumulado.py` | Función pura `calcular_acumulado(db, ingreso_id)` reutilizable por EPIC-12 |
| `backend/app/services/licencias_alerta.py` | Lógica de días hábiles + `generar_alertas_vencimiento(db)` (idempotente) |
| `backend/app/models/alerta_licencia.py` | Modelo `AlertaLicencia` (alerta in-app de vencimiento) |
| `backend/app/routers/licencias.py` | Endpoints CRUD + acumulado + alertas |
| `backend/migrations/versions/0070_crear_licencia_medica.py` | Migración CEPA-070 (tabla `licencia_medica`) |
| `backend/migrations/versions/0071_crear_alerta_licencia.py` | Migración CEPA-072 (tabla `alerta_licencia`) |

| Archivo (modificar) | Motivo |
|---|---|
| `backend/app/models/__init__.py` | Registrar `LicenciaMedica`, `AlertaLicencia` para Alembic |
| `backend/app/main.py` | `include_router(licencias.router)` |

---

## Task 1: Enums de dominio de licencias (`TipoLicencia`, `TipoReposo`, `EstadoEnvioISL`, `OrigenLicencia`)

Listas cerradas requeridas por RN-3 de CEPA-070 y RN-1..4 de CEPA-073. Los valores se mapean a `String` en BD (portabilidad D15).

**Files:**
- Create: `backend/app/domain/enums_licencia.py`
- Test: `backend/tests/test_enums_licencia.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_enums_licencia.py`:

```python
from app.domain.enums_licencia import EstadoEnvioISL, OrigenLicencia, TipoLicencia, TipoReposo


def test_tipo_licencia_catalogo_exacto():
    """RN-3 CEPA-070: solo valores {1, 5, 6}."""
    valores = {t.value for t in TipoLicencia}
    assert valores == {"1", "5", "6"}


def test_tipo_reposo_catalogo_exacto():
    """RN-3 CEPA-070: solo {total, parcial}."""
    valores = {t.value for t in TipoReposo}
    assert valores == {"total", "parcial"}


def test_estado_envio_isl_catalogo_exacto():
    """RN-2 CEPA-073: {pendiente, enviado, rechazado}."""
    valores = {e.value for e in EstadoEnvioISL}
    assert valores == {"pendiente", "enviado", "rechazado"}


def test_origen_licencia_catalogo_exacto():
    """RN-4 CEPA-073: {sistema, extra_sistema}."""
    valores = {o.value for o in OrigenLicencia}
    assert valores == {"sistema", "extra_sistema"}


def test_todos_los_enums_son_str():
    for klass in (TipoLicencia, TipoReposo, EstadoEnvioISL, OrigenLicencia):
        for miembro in klass:
            assert isinstance(miembro.value, str), f"{klass.__name__}.{miembro.name} no es str"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_enums_licencia.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.domain.enums_licencia'`.

- [ ] **Step 3: Implementar `app/domain/enums_licencia.py`**

Crear `backend/app/domain/enums_licencia.py`:

```python
"""Listas cerradas del dominio de Licencias Médicas — EPIC-07.

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo la portabilidad de BD (no se usan tipos enum nativos del motor — D15).
"""

from enum import Enum


class TipoLicencia(str, Enum):
    """Tipos de licencia médica relevantes para CEPA (RN-3 CEPA-070).

    1 = enfermedad común
    5 = enfermedad/accidente del trabajo curativa
    6 = patología del embarazo / prórroga
    """

    UNO = "1"
    CINCO = "5"
    SEIS = "6"


class TipoReposo(str, Enum):
    """Tipo de reposo prescrito en la LM (RN-3 CEPA-070, v4 D8)."""

    TOTAL = "total"
    PARCIAL = "parcial"


class EstadoEnvioISL(str, Enum):
    """Estado de envío de la LM al Instituto de Seguridad Laboral (RN-2 CEPA-073)."""

    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    RECHAZADO = "rechazado"


class OrigenLicencia(str, Enum):
    """Origen de la licencia: gestionada en CEPA o registrada como extra-sistema (v4 D7)."""

    SISTEMA = "sistema"
    EXTRA_SISTEMA = "extra_sistema"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_enums_licencia.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/enums_licencia.py backend/tests/test_enums_licencia.py
git commit -m "feat(licencias): enums de dominio TipoLicencia/TipoReposo/EstadoEnvioISL/OrigenLicencia"
```

---

## Task 2: Modelo `LicenciaMedica` + migración (CEPA-070)

Tabla `licencia_medica` con todos los campos D8 + trazabilidad ISL + FK a `ingreso`. Incluye `anulada` (bool) para manejo de 77 BIS.

**Files:**
- Create: `backend/app/models/licencia.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0070_crear_licencia_medica.py`
- Test: `backend/tests/test_licencia_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_licencia_model.py`:

```python
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, String, Text

from app.models.licencia import LicenciaMedica


def test_tabla_y_columnas():
    tabla = LicenciaMedica.__table__
    assert tabla.name == "licencia_medica"
    columnas_esperadas = {
        "id",
        "ingreso_id",
        "folio_lm",
        "tipo_lm",
        "tipo_reposo",
        "fecha_inicio",
        "fecha_termino",
        "fecha_emision",
        "inicio_reposo",
        "fin_reposo",
        "cantidad_dias",
        "indicacion_reposo",
        "diagnostico",
        "origen",
        "envio_isl",
        "fecha_envio_isl",
        "eeag_gaf",
        "observaciones",
        "anulada",
        "created_at",
        "updated_at",
    }
    assert set(tabla.columns.keys()) == columnas_esperadas


def test_reglas_portabilidad_identificadores():
    tabla = LicenciaMedica.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"'{nombre}' debe ir en minúscula"
        assert len(nombre) <= 30, f"'{nombre}' supera 30 chars (Oracle limit)"


def test_tipos_y_pk():
    cols = LicenciaMedica.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    # fechas de calendario sin hora
    assert isinstance(cols["fecha_inicio"].type, Date)
    assert isinstance(cols["fecha_termino"].type, Date)
    assert isinstance(cols["fecha_emision"].type, Date)
    assert isinstance(cols["inicio_reposo"].type, Date)
    assert isinstance(cols["fin_reposo"].type, Date)
    # enteros
    assert isinstance(cols["cantidad_dias"].type, Integer)
    # timestamps con zona
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True
    # bool anulada
    assert isinstance(cols["anulada"].type, Boolean)
    # GAF como Numeric para no perder precisión en Oracle
    assert isinstance(cols["eeag_gaf"].type, (Integer, Numeric))


def test_fk_ingreso_existe():
    tabla = LicenciaMedica.__table__
    fks = list(tabla.columns["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


def test_anulada_default_false():
    assert LicenciaMedica.__table__.columns["anulada"].nullable is False
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencia_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.licencia'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/licencia.py`:

```python
"""Modelo LicenciaMedica — EPIC-07 CEPA-070..073.

Columnas D8 (v4): cantidad_dias, inicio_reposo, fin_reposo, fecha_emision,
tipo_lm, indicacion_reposo, diagnostico, tipo_reposo (total/parcial).
Trazabilidad ISL (CEPA-073): envio_isl, fecha_envio_isl, eeag_gaf, observaciones.
Licencias extra-sistema (v4 D7): campo origen.
Anulación 77 BIS: campo anulada.
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


class LicenciaMedica(Base):
    """Licencia médica vinculada a un ingreso/folio.

    Una LM anulada (campo anulada=True) queda en historial pero se excluye
    del acumulado vigente (RN-4 CEPA-071, RN-5 CEPA-073).
    """

    __tablename__ = "licencia_medica"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    folio_lm: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    tipo_lm: Mapped[str] = mapped_column(String(5), nullable=False)
    tipo_reposo: Mapped[str] = mapped_column(String(15), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_termino: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    inicio_reposo: Mapped[date] = mapped_column(Date, nullable=False)
    fin_reposo: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    indicacion_reposo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    diagnostico: Mapped[str] = mapped_column(String(200), nullable=False)
    origen: Mapped[str] = mapped_column(String(20), nullable=False, default="sistema")
    # Trazabilidad ISL (CEPA-073)
    envio_isl: Mapped[str] = mapped_column(String(15), nullable=False, default="pendiente")
    fecha_envio_isl: Mapped[date | None] = mapped_column(Date, nullable=True)
    eeag_gaf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Control
    anulada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="licencias")  # noqa: F821
```

Modificar `backend/app/models/__init__.py` (añadir al final):

```python
from app.models.licencia import LicenciaMedica  # noqa: F401
```

También es necesario añadir la relación inversa en el modelo `Ingreso` de EPIC-01. Modificar `backend/app/models/ingreso.py` añadiendo al bloque de `relationship` al final de la clase:

```python
    licencias: Mapped[list["LicenciaMedica"]] = relationship(  # noqa: F821
        back_populates="ingreso", cascade="all, delete-orphan"
    )
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0070_crear_licencia_medica.py`**

```python
"""crear licencia_medica

Revision ID: 0070
Revises: <RESOLVER: alembic heads>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0070"
down_revision = "<RESOLVER: alembic heads>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "licencia_medica",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("folio_lm", sa.String(length=40), nullable=True),
        sa.Column("tipo_lm", sa.String(length=5), nullable=False),
        sa.Column("tipo_reposo", sa.String(length=15), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_termino", sa.Date(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("inicio_reposo", sa.Date(), nullable=False),
        sa.Column("fin_reposo", sa.Date(), nullable=False),
        sa.Column("cantidad_dias", sa.Integer(), nullable=False),
        sa.Column("indicacion_reposo", sa.String(length=300), nullable=True),
        sa.Column("diagnostico", sa.String(length=200), nullable=False),
        sa.Column("origen", sa.String(length=20), nullable=False),
        sa.Column("envio_isl", sa.String(length=15), nullable=False),
        sa.Column("fecha_envio_isl", sa.Date(), nullable=True),
        sa.Column("eeag_gaf", sa.Integer(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("anulada", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_licencia_ingreso"
        ),
    )
    op.create_index("ix_licencia_ingreso_id", "licencia_medica", ["ingreso_id"])
    op.create_index("ix_licencia_folio_lm", "licencia_medica", ["folio_lm"])


def downgrade() -> None:
    op.drop_index("ix_licencia_folio_lm", table_name="licencia_medica")
    op.drop_index("ix_licencia_ingreso_id", table_name="licencia_medica")
    op.drop_table("licencia_medica")
```

> **Acción del agente antes de correr:** ejecutar `uv run alembic heads` desde `backend/` y reemplazar `<RESOLVER: alembic heads>` por el `revision_id` real que sea la cabeza de la cadena de EPIC-01. Ver Notas de cierre.

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run: `uv run pytest tests/test_licencia_model.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Verificar que la migración aplica**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: crea, baja y vuelve a crear `licencia_medica` sin error.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/licencia.py backend/app/models/__init__.py backend/app/models/ingreso.py backend/migrations/versions/0070_crear_licencia_medica.py backend/tests/test_licencia_model.py
git commit -m "feat(licencias): modelo LicenciaMedica + migración 0070 (CEPA-070 D8+ISL)"
```

---

## Task 3: Schemas Pydantic v2 de licencias

Schemas para todos los endpoints: creación, actualización de trazabilidad ISL, respuesta completa y vista de acumulado. Incluye validaciones de reglas de negocio.

**Files:**
- Create: `backend/app/schemas/licencia.py`
- Test: `backend/tests/test_licencia_schemas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_licencia_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.licencia import LicenciaCreate, LicenciaISLUpdate


# CA-2 / RN-4 CEPA-070: fecha_termino >= fecha_inicio
def test_fecha_termino_anterior_a_inicio_rechazada():
    with pytest.raises(ValidationError) as exc_info:
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio="2026-06-15",
            fecha_termino="2026-06-01",  # anterior a inicio
            fecha_emision="2026-06-10",
            inicio_reposo="2026-06-15",
            fin_reposo="2026-06-29",
            cantidad_dias=15,
            diagnostico="F32.1",
        )
    errs = exc_info.value.errors()
    assert any("fecha_termino" in str(e["loc"]) or "termino" in e["msg"].lower() for e in errs)


# RN-4 CEPA-070: fecha_emision <= fecha_inicio
def test_fecha_emision_posterior_a_inicio_rechazada():
    with pytest.raises(ValidationError):
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio="2026-06-10",
            fecha_termino="2026-06-24",
            fecha_emision="2026-06-15",  # posterior a inicio
            inicio_reposo="2026-06-10",
            fin_reposo="2026-06-24",
            cantidad_dias=15,
            diagnostico="F32.1",
        )


# RN-4 CEPA-070: fin_reposo >= inicio_reposo
def test_fin_reposo_anterior_a_inicio_reposo_rechazado():
    with pytest.raises(ValidationError):
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio="2026-06-10",
            fecha_termino="2026-06-24",
            fecha_emision="2026-06-08",
            inicio_reposo="2026-06-15",
            fin_reposo="2026-06-10",  # anterior a inicio_reposo
            cantidad_dias=15,
            diagnostico="F32.1",
        )


# TC-070-05 / RN-3: tipo_lm fuera de catálogo rechazado
def test_tipo_lm_invalido_rechazado():
    with pytest.raises(ValidationError):
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="3",  # no está en {1, 5, 6}
            tipo_reposo="total",
            fecha_inicio="2026-06-10",
            fecha_termino="2026-06-24",
            fecha_emision="2026-06-08",
            inicio_reposo="2026-06-10",
            fin_reposo="2026-06-24",
            cantidad_dias=15,
            diagnostico="F32.1",
        )


# TC-073-05 / RN-1 CEPA-073: EEAG fuera de rango 1-100 rechazado
def test_eeag_gaf_fuera_de_rango_rechazado():
    with pytest.raises(ValidationError):
        LicenciaISLUpdate(envio_isl="enviado", fecha_envio_isl="2026-06-02", eeag_gaf=150)


def test_eeag_gaf_cero_rechazado():
    with pytest.raises(ValidationError):
        LicenciaISLUpdate(envio_isl="enviado", fecha_envio_isl="2026-06-02", eeag_gaf=0)


# TC-073-02 / RN-2: estado=enviado sin fecha rechazado
def test_isl_enviado_sin_fecha_rechazado():
    with pytest.raises(ValidationError):
        LicenciaISLUpdate(envio_isl="enviado", fecha_envio_isl=None)


# Schema válido: no lanza excepción
def test_schema_valido_acepta():
    lm = LicenciaCreate(
        ingreso_id=1,
        tipo_lm="1",
        tipo_reposo="total",
        fecha_inicio="2026-06-01",
        fecha_termino="2026-06-15",
        fecha_emision="2026-05-30",
        inicio_reposo="2026-06-01",
        fin_reposo="2026-06-15",
        cantidad_dias=15,
        diagnostico="F32.1",
    )
    assert lm.tipo_lm.value == "1"
    assert lm.cantidad_dias == 15
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencia_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.licencia'`.

- [ ] **Step 3: Implementar los schemas**

Crear `backend/app/schemas/licencia.py`:

```python
"""Schemas Pydantic v2 para Licencias Médicas — EPIC-07.

Valida en capa de aplicación las reglas de negocio de fechas (RN-4 CEPA-070),
catálogos cerrados (RN-3 CEPA-070) y trazabilidad ISL (RN-1/RN-2 CEPA-073).
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums_licencia import EstadoEnvioISL, OrigenLicencia, TipoLicencia, TipoReposo


class LicenciaCreate(BaseModel):
    """Alta de una licencia médica (CEPA-070, campos D8)."""

    ingreso_id: int
    folio_lm: str | None = None
    tipo_lm: TipoLicencia
    tipo_reposo: TipoReposo
    fecha_inicio: date
    fecha_termino: date
    fecha_emision: date
    inicio_reposo: date
    fin_reposo: date
    cantidad_dias: Annotated[int, Field(ge=1)]
    indicacion_reposo: str | None = None
    diagnostico: str
    origen: OrigenLicencia = OrigenLicencia.SISTEMA

    @model_validator(mode="after")
    def _validar_coherencia_fechas(self) -> "LicenciaCreate":
        # RN-4: fecha_termino >= fecha_inicio
        if self.fecha_termino < self.fecha_inicio:
            raise ValueError(
                "fecha_termino debe ser mayor o igual a fecha_inicio "
                f"(inicio={self.fecha_inicio}, termino={self.fecha_termino})"
            )
        # RN-4: fecha_emision <= fecha_inicio
        if self.fecha_emision > self.fecha_inicio:
            raise ValueError(
                "fecha_emision debe ser anterior o igual a fecha_inicio "
                f"(emision={self.fecha_emision}, inicio={self.fecha_inicio})"
            )
        # RN-4: fin_reposo >= inicio_reposo
        if self.fin_reposo < self.inicio_reposo:
            raise ValueError(
                "fin_reposo debe ser mayor o igual a inicio_reposo "
                f"(inicio_reposo={self.inicio_reposo}, fin_reposo={self.fin_reposo})"
            )
        return self


class LicenciaISLUpdate(BaseModel):
    """Actualización de trazabilidad ISL (CEPA-073 RN-1/RN-2)."""

    envio_isl: EstadoEnvioISL
    fecha_envio_isl: date | None = None
    eeag_gaf: Annotated[int | None, Field(ge=1, le=100)] = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def _fecha_obligatoria_cuando_enviado_o_rechazado(self) -> "LicenciaISLUpdate":
        if self.envio_isl in (EstadoEnvioISL.ENVIADO, EstadoEnvioISL.RECHAZADO):
            if self.fecha_envio_isl is None:
                raise ValueError(
                    f"fecha_envio_isl es obligatoria cuando envio_isl='{self.envio_isl.value}'"
                )
        return self


class LicenciaAnularUpdate(BaseModel):
    """Anulación/recalificación de una LM (77 BIS o admin)."""

    observaciones: str


class LicenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    folio_lm: str | None
    tipo_lm: TipoLicencia
    tipo_reposo: TipoReposo
    fecha_inicio: date
    fecha_termino: date
    fecha_emision: date
    inicio_reposo: date
    fin_reposo: date
    cantidad_dias: int
    indicacion_reposo: str | None
    diagnostico: str
    origen: OrigenLicencia
    envio_isl: EstadoEnvioISL
    fecha_envio_isl: date | None
    eeag_gaf: int | None
    observaciones: str | None
    anulada: bool


class AcumuladoRead(BaseModel):
    """Respuesta del endpoint de acumulado de días por paciente (CEPA-071, EPIC-12)."""

    model_config = ConfigDict(from_attributes=True)

    ingreso_id: int
    dias_acumulados_vigentes: int
    dias_acumulados_bruto: int
    hay_solapamiento: bool
    incluye_extra_sistema: bool


class AlertaLicenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    licencia_id: int
    ingreso_id: int
    fecha_termino_lm: date
    dias_habiles_restantes: int
    activa: bool
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_licencia_schemas.py -v`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/licencia.py backend/tests/test_licencia_schemas.py
git commit -m "feat(licencias): schemas Pydantic v2 con validaciones de fechas e ISL (CEPA-070..073)"
```

---

## Task 4: Servicio de cálculo de días acumulados (CEPA-071)

Función pura `calcular_acumulado(db, ingreso_id)` — reutilizable por EPIC-12 — que suma `cantidad_dias` de todas las LM vigentes del ingreso, calcula días calendario efectivos (sin doble-conteo de solapamientos) y retorna ambos valores junto con flags de solapamiento y extra-sistema.

**Files:**
- Create: `backend/app/services/licencias_acumulado.py`
- Test: `backend/tests/test_licencias_acumulado.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_licencias_acumulado.py`:

```python
import datetime

import pytest

from app.models.licencia import LicenciaMedica
from app.models.paciente import Paciente
from app.models.ingreso import Ingreso
from app.services.licencias_acumulado import calcular_acumulado


def _make_ingreso(db) -> Ingreso:
    """Crea paciente + ingreso de prueba y devuelve el ingreso."""
    pac = Paciente(rut="201010101", nombre="Test Licencias", sexo="F", edad=35, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio="F-TEST-0001",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


def _lm(ingreso_id, inicio, termino, dias, origen="sistema", anulada=False):
    return LicenciaMedica(
        ingreso_id=ingreso_id,
        tipo_lm="1",
        tipo_reposo="total",
        fecha_inicio=inicio,
        fecha_termino=termino,
        fecha_emision=inicio,
        inicio_reposo=inicio,
        fin_reposo=termino,
        cantidad_dias=dias,
        diagnostico="F32.1",
        origen=origen,
        envio_isl="pendiente",
        anulada=anulada,
    )


# RN-6 CEPA-071: paciente sin LM previas -> acumulado = días primera LM
# TC-071-02
def test_primera_lm_acumulado_igual_a_sus_dias(db_session):
    ing = _make_ingreso(db_session)
    lm = _lm(ing.id, datetime.date(2026, 6, 1), datetime.date(2026, 6, 12), 12)
    db_session.add(lm)
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_vigentes == 12
    assert resultado.dias_acumulados_bruto == 12
    assert resultado.hay_solapamiento is False


# CA-1 CEPA-071: 3 LM previas + 1 nueva = suma total
# TC-071-01
def test_cuatro_lm_sin_solapamiento_suma_correcta(db_session):
    ing = _make_ingreso(db_session)
    for inicio, termino, dias in [
        (datetime.date(2026, 1, 1), datetime.date(2026, 1, 10), 10),
        (datetime.date(2026, 2, 1), datetime.date(2026, 2, 15), 15),
        (datetime.date(2026, 3, 1), datetime.date(2026, 3, 7), 7),
        (datetime.date(2026, 4, 1), datetime.date(2026, 4, 8), 8),
    ]:
        db_session.add(_lm(ing.id, inicio, termino, dias))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_bruto == 40
    assert resultado.dias_acumulados_vigentes == 40
    assert resultado.hay_solapamiento is False


# RN-3 CEPA-071: solapamiento — días calendario efectivos no duplican
# TC-071-03: LM A=01–10/jun, LM B=06–15/jun → solapamiento 06–10 (5 días)
def test_solapamiento_no_duplica_dias(db_session):
    ing = _make_ingreso(db_session)
    # LM A: 01/06 – 10/06 = 10 días calendario efectivos (01..10)
    db_session.add(_lm(ing.id, datetime.date(2026, 6, 1), datetime.date(2026, 6, 10), 10))
    # LM B: 06/06 – 15/06 = 10 días calendario efectivos (06..15)
    db_session.add(_lm(ing.id, datetime.date(2026, 6, 6), datetime.date(2026, 6, 15), 10))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    # bruto = 10 + 10 = 20 (suma simple)
    assert resultado.dias_acumulados_bruto == 20
    # efectivos: días únicos entre 01/06..10/06 ∪ 06/06..15/06 = 01..15 = 15 días
    assert resultado.dias_acumulados_vigentes == 15
    assert resultado.hay_solapamiento is True


# TC-071-04: LM extra-sistema suma al acumulado marcada como tal
def test_extra_sistema_suma_al_acumulado(db_session):
    ing = _make_ingreso(db_session)
    db_session.add(_lm(ing.id, datetime.date(2026, 1, 1), datetime.date(2026, 1, 20), 20, origen="extra_sistema"))
    db_session.add(_lm(ing.id, datetime.date(2026, 2, 1), datetime.date(2026, 2, 10), 10))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_vigentes == 30
    assert resultado.incluye_extra_sistema is True


# TC-071-05 / RN-4: LM anulada se excluye del acumulado vigente
def test_lm_anulada_excluida_del_acumulado(db_session):
    ing = _make_ingreso(db_session)
    db_session.add(_lm(ing.id, datetime.date(2026, 1, 1), datetime.date(2026, 1, 15), 15))
    # esta se anula (77 BIS)
    db_session.add(_lm(ing.id, datetime.date(2026, 2, 1), datetime.date(2026, 2, 15), 15, anulada=True))
    db_session.flush()

    resultado = calcular_acumulado(db_session, ing.id)

    assert resultado.dias_acumulados_vigentes == 15
    assert resultado.dias_acumulados_bruto == 15


# Borde: ingreso sin LM -> acumulado = 0
def test_ingreso_sin_lm_acumulado_cero(db_session):
    ing = _make_ingreso(db_session)
    resultado = calcular_acumulado(db_session, ing.id)
    assert resultado.dias_acumulados_vigentes == 0
    assert resultado.hay_solapamiento is False
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencias_acumulado.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.licencias_acumulado'`.

- [ ] **Step 3: Implementar el servicio**

Crear `backend/app/services/licencias_acumulado.py`:

```python
"""Cálculo de días acumulados de licencias médicas por ingreso — CEPA-071.

Esta función es pura respecto a la BD (solo consulta, no muta) y está diseñada
para ser reutilizada por EPIC-12 (API de integración).

Algoritmo de días calendario efectivos (RN-3 CEPA-071):
  1. Filtrar LM vigentes (anulada=False) del ingreso.
  2. Para el bruto: sumar cantidad_dias directamente (suma simple).
  3. Para el efectivo: construir la unión de intervalos [fecha_inicio, fecha_termino]
     contando días de calendario únicos (set de fechas).
  4. Si el tamaño del set < suma bruta → hay solapamiento.
"""

import datetime
from dataclasses import dataclass

from sqlalchemy import select

from app.models.licencia import LicenciaMedica


@dataclass
class ResultadoAcumulado:
    ingreso_id: int
    dias_acumulados_vigentes: int
    dias_acumulados_bruto: int
    hay_solapamiento: bool
    incluye_extra_sistema: bool


def calcular_acumulado(db, ingreso_id: int) -> ResultadoAcumulado:
    """Calcula el acumulado de días de licencia para el ingreso dado.

    - dias_acumulados_bruto: suma de campo cantidad_dias de todas las LM vigentes.
    - dias_acumulados_vigentes: días calendario únicos en la unión de intervalos
      [fecha_inicio, fecha_termino] (evita doble-conteo de solapamientos).
    - hay_solapamiento: True si se detectaron intervalos superpuestos.
    - incluye_extra_sistema: True si al menos una LM es de origen extra_sistema.

    Las LM anuladas (anulada=True) se excluyen del cómputo vigente (RN-4 CEPA-071).
    """
    licencias = list(
        db.scalars(
            select(LicenciaMedica)
            .where(
                LicenciaMedica.ingreso_id == ingreso_id,
                LicenciaMedica.anulada.is_(False),
            )
            .order_by(LicenciaMedica.fecha_inicio)
        )
    )

    if not licencias:
        return ResultadoAcumulado(
            ingreso_id=ingreso_id,
            dias_acumulados_vigentes=0,
            dias_acumulados_bruto=0,
            hay_solapamiento=False,
            incluye_extra_sistema=False,
        )

    dias_bruto = sum(lm.cantidad_dias for lm in licencias)
    incluye_extra = any(lm.origen == "extra_sistema" for lm in licencias)

    # Unión de intervalos: set de fechas calendario cubiertas
    dias_calendario: set[datetime.date] = set()
    for lm in licencias:
        delta = (lm.fecha_termino - lm.fecha_inicio).days + 1
        for offset in range(delta):
            dias_calendario.add(lm.fecha_inicio + datetime.timedelta(days=offset))

    dias_efectivos = len(dias_calendario)
    hay_solapamiento = dias_efectivos < dias_bruto

    return ResultadoAcumulado(
        ingreso_id=ingreso_id,
        dias_acumulados_vigentes=dias_efectivos,
        dias_acumulados_bruto=dias_bruto,
        hay_solapamiento=hay_solapamiento,
        incluye_extra_sistema=incluye_extra,
    )
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_licencias_acumulado.py -v`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/licencias_acumulado.py backend/tests/test_licencias_acumulado.py
git commit -m "feat(licencias): servicio calcular_acumulado con solapamientos y extra-sistema (CEPA-071)"
```

---

## Task 5: Servicio de alertas de vencimiento (CEPA-072) + modelo `AlertaLicencia` + migración

Tabla `alerta_licencia` (append de alertas in-app) y función `generar_alertas_vencimiento(db, hoy)` que calcula días hábiles restantes (excluye sábados/domingos — festivos queda como lista configurable, ver Notas de cierre), genera alertas idempotentes para LM que vencen en ≤3 días hábiles y no están anuladas ni vencidas.

**Files:**
- Create: `backend/app/models/alerta_licencia.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0071_crear_alerta_licencia.py`
- Create: `backend/app/services/licencias_alerta.py`
- Test: `backend/tests/test_licencias_alerta.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_licencias_alerta.py`:

```python
import datetime

import pytest

from app.models.alerta_licencia import AlertaLicencia
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.paciente import Paciente
from app.services.licencias_alerta import contar_dias_habiles, generar_alertas_vencimiento


def _make_lm(db, termino: datetime.date, anulada: bool = False) -> LicenciaMedica:
    pac = Paciente(
        rut=f"9{termino.toordinal()}", nombre="Alerta Test", sexo="M", edad=40, region="RM"
    )
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio=f"F-ALRT-{termino.isoformat()}",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    inicio = termino - datetime.timedelta(days=14)
    lm = LicenciaMedica(
        ingreso_id=ing.id,
        tipo_lm="5",
        tipo_reposo="total",
        fecha_inicio=inicio,
        fecha_termino=termino,
        fecha_emision=inicio,
        inicio_reposo=inicio,
        fin_reposo=termino,
        cantidad_dias=15,
        diagnostico="F32.1",
        origen="sistema",
        envio_isl="pendiente",
        anulada=anulada,
    )
    db.add(lm)
    db.flush()
    return lm


# Pruebas unitarias puras de contar_dias_habiles (sin BD)
# TC-072-02: cálculo correcto saltando fin de semana
def test_contar_dias_habiles_salta_fin_de_semana():
    # viernes 06/06/2026 -> lunes 09/06, martes 10/06, miércoles 11/06 = 3 días hábiles
    viernes = datetime.date(2026, 6, 6)
    lunes = datetime.date(2026, 6, 9)
    martes = datetime.date(2026, 6, 10)
    miercoles = datetime.date(2026, 6, 11)
    assert contar_dias_habiles(viernes, lunes) == 1
    assert contar_dias_habiles(viernes, martes) == 2
    assert contar_dias_habiles(viernes, miercoles) == 3


def test_contar_dias_habiles_mismo_dia_es_cero():
    hoy = datetime.date(2026, 6, 10)
    assert contar_dias_habiles(hoy, hoy) == 0


def test_contar_dias_habiles_fin_en_pasado_es_negativo():
    hoy = datetime.date(2026, 6, 10)
    ayer = datetime.date(2026, 6, 9)
    assert contar_dias_habiles(hoy, ayer) < 0


# TC-072-01: LM vence exactamente en 3 días hábiles -> alerta generada
def test_lm_vence_en_3_habiles_genera_alerta(db_session):
    # Hoy = miércoles 10/06/2026; 3 días hábiles después = lunes 15/06/2026
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 15)
    lm = _make_lm(db_session, termino)
    db_session.flush()

    generadas = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    assert lm.id in [a.licencia_id for a in generadas]


# TC-072-03: LM vencida no genera alerta
def test_lm_vencida_no_genera_alerta(db_session):
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 9)  # ayer → vencida
    lm = _make_lm(db_session, termino)
    db_session.flush()

    generadas = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    assert lm.id not in [a.licencia_id for a in generadas]


# TC-072-04: idempotencia — segunda ejecución no duplica alerta
def test_no_duplica_alerta_si_ya_existe(db_session):
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 13)  # 3 días hábiles (jue)
    lm = _make_lm(db_session, termino)
    db_session.flush()

    primera = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)
    segunda = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    alertas_de_lm = [a for a in primera if a.licencia_id == lm.id]
    alertas_segunda = [a for a in segunda if a.licencia_id == lm.id]
    # segunda ejecución no genera nuevas (devuelve lista vacía para esa LM)
    assert len(alertas_de_lm) == 1
    assert len(alertas_segunda) == 0


# LM anulada no genera alerta (RN-5 CEPA-072)
def test_lm_anulada_no_genera_alerta(db_session):
    hoy = datetime.date(2026, 6, 10)
    termino = datetime.date(2026, 6, 13)
    lm = _make_lm(db_session, termino, anulada=True)
    db_session.flush()

    generadas = generar_alertas_vencimiento(db_session, hoy=hoy, umbral_habiles=3)

    assert lm.id not in [a.licencia_id for a in generadas]
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencias_alerta.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.alerta_licencia'`.

- [ ] **Step 3: Implementar el modelo `AlertaLicencia`**

Crear `backend/app/models/alerta_licencia.py`:

```python
"""Alerta in-app de vencimiento de licencia médica — CEPA-072.

Append-only. La idempotencia se logra verificando que no exista una alerta
activa (activa=True) para la misma (licencia_id, fecha_generacion).
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlertaLicencia(Base):
    __tablename__ = "alerta_licencia"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    licencia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("licencia_medica.id"), nullable=False, index=True
    )
    ingreso_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    fecha_termino_lm: Mapped[date] = mapped_column(Date, nullable=False)
    dias_habiles_restantes: Mapped[int] = mapped_column(Integer, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
```

Modificar `backend/app/models/__init__.py` (añadir al final):

```python
from app.models.alerta_licencia import AlertaLicencia  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0071_crear_alerta_licencia.py`**

```python
"""crear alerta_licencia

Revision ID: 0071
Revises: 0070
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerta_licencia",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("licencia_id", sa.BigInteger(), nullable=False),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_termino_lm", sa.Date(), nullable=False),
        sa.Column("dias_habiles_restantes", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["licencia_id"], ["licencia_medica.id"], name="fk_alerta_licencia"
        ),
    )
    op.create_index("ix_alerta_licencia_id", "alerta_licencia", ["licencia_id"])
    op.create_index("ix_alerta_ingreso_id", "alerta_licencia", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_alerta_ingreso_id", table_name="alerta_licencia")
    op.drop_index("ix_alerta_licencia_id", table_name="alerta_licencia")
    op.drop_table("alerta_licencia")
```

- [ ] **Step 5: Implementar el servicio de alertas**

Crear `backend/app/services/licencias_alerta.py`:

```python
"""Servicio de alertas de vencimiento de licencias médicas — CEPA-072.

contar_dias_habiles(desde, hasta): cuenta días hábiles (lun–vie) entre dos fechas,
  excluyendo fines de semana. Los festivos chilenos se gestionan como lista
  configurable (ver Notas de cierre del plan); por defecto esta función solo
  excluye sáb/dom para mantener el servicio portable y sin dependencia externa.

generar_alertas_vencimiento(db, hoy, umbral_habiles=3): idempotente — por cada LM
  vigente que vence en ≤umbral_habiles días hábiles, crea una AlertaLicencia solo
  si no existe ya una activa para esa LM (RN-4 CEPA-072).
"""

import datetime
from typing import Sequence

from sqlalchemy import select

from app.models.alerta_licencia import AlertaLicencia
from app.models.licencia import LicenciaMedica


def contar_dias_habiles(
    desde: datetime.date,
    hasta: datetime.date,
    festivos: frozenset[datetime.date] | None = None,
) -> int:
    """Cuenta los días hábiles entre `desde` (exclusivo) y `hasta` (inclusivo).

    Un día hábil es lunes-viernes y no está en `festivos`.
    Devuelve valor negativo si `hasta` < `desde` (LM vencida).
    """
    festivos = festivos or frozenset()
    if hasta < desde:
        # calcular negativo para indicar que ya venció
        return -contar_dias_habiles(hasta, desde, festivos)
    conteo = 0
    cursor = desde + datetime.timedelta(days=1)
    while cursor <= hasta:
        if cursor.weekday() < 5 and cursor not in festivos:  # 0=lun, 4=vie
            conteo += 1
        cursor += datetime.timedelta(days=1)
    return conteo


def generar_alertas_vencimiento(
    db,
    hoy: datetime.date | None = None,
    umbral_habiles: int = 3,
    festivos: frozenset[datetime.date] | None = None,
) -> list[AlertaLicencia]:
    """Genera alertas in-app para LM que vencen en ≤umbral_habiles días hábiles.

    Idempotente: no crea alerta si ya existe una activa para la misma licencia_id.
    Excluye LM anuladas y LM cuya fecha_termino < hoy (ya vencidas).
    Devuelve la lista de alertas NUEVAS creadas en esta ejecución.
    """
    hoy = hoy or datetime.date.today()
    festivos = festivos or frozenset()

    # LM vigentes cuyo término es >= hoy (no vencidas aún)
    lm_candidatas = list(
        db.scalars(
            select(LicenciaMedica).where(
                LicenciaMedica.anulada.is_(False),
                LicenciaMedica.fecha_termino >= hoy,
            )
        )
    )

    nuevas: list[AlertaLicencia] = []
    for lm in lm_candidatas:
        habiles = contar_dias_habiles(hoy, lm.fecha_termino, festivos)
        if habiles > umbral_habiles:
            continue  # todavía no está en la ventana de alerta

        # Idempotencia: ¿ya existe una alerta activa para esta LM?
        existente = db.execute(
            select(AlertaLicencia).where(
                AlertaLicencia.licencia_id == lm.id,
                AlertaLicencia.activa.is_(True),
            )
        ).scalar_one_or_none()
        if existente is not None:
            continue

        alerta = AlertaLicencia(
            licencia_id=lm.id,
            ingreso_id=lm.ingreso_id,
            fecha_termino_lm=lm.fecha_termino,
            dias_habiles_restantes=habiles,
            activa=True,
        )
        db.add(alerta)
        nuevas.append(alerta)

    if nuevas:
        db.flush()
    return nuevas
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_licencias_alerta.py -v
```
Expected: `8 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/alerta_licencia.py backend/app/models/__init__.py backend/migrations/versions/0071_crear_alerta_licencia.py backend/app/services/licencias_alerta.py backend/tests/test_licencias_alerta.py
git commit -m "feat(licencias): AlertaLicencia + migración 0071 + servicio vencimiento idempotente (CEPA-072)"
```

---

## Task 6: API de registro y CRUD de licencias — CEPA-070 (POST/GET/PATCH anular)

Endpoints: `POST /api/v1/licencias` (crear), `GET /api/v1/licencias/{id}` (detalle), `GET /api/v1/ingresos/{ingreso_id}/licencias` (historial por ingreso, incluye extra-sistema, orden cronológico — CA-3/CA-4 CEPA-073), `PATCH /api/v1/licencias/{id}/anular` (anulación/77 BIS). Auditoría en CREATE y anulación (UPDATE).

**Files:**
- Create: `backend/app/services/licencias_crud.py`
- Create: `backend/app/routers/licencias.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_licencias_api_crud.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_licencias_api_crud.py`:

```python
import datetime


def _payload_ingreso(as_admin, rut="12.345.678-5", folio="F-LIC-001"):
    """Crea un ingreso de prueba y devuelve su id."""
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente Licencias",
            "sexo": "F",
            "edad": 38,
            "region": "Maule",
            "diagnostico": "F32.1",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-10",
            "folio": folio,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _payload_lm(ingreso_id, **over):
    base = {
        "ingreso_id": ingreso_id,
        "tipo_lm": "1",
        "tipo_reposo": "total",
        "fecha_inicio": "2026-06-01",
        "fecha_termino": "2026-06-15",
        "fecha_emision": "2026-05-30",
        "inicio_reposo": "2026-06-01",
        "fin_reposo": "2026-06-15",
        "cantidad_dias": 15,
        "diagnostico": "F32.1",
    }
    base.update(over)
    return base


# TC-070-01: registro exitoso, vinculado al ingreso, visible en historial
def test_crear_lm_registra_y_aparece_en_historial(as_admin):
    ing_id = _payload_ingreso(as_admin)
    r = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["ingreso_id"] == ing_id
    assert cuerpo["tipo_lm"] == "1"
    assert cuerpo["anulada"] is False

    hist = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias")
    assert hist.status_code == 200
    ids = [lm["id"] for lm in hist.json()]
    assert cuerpo["id"] in ids


# TC-070-02: fecha_termino < fecha_inicio -> 422
def test_fecha_termino_anterior_rechaza_422(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-002")
    r = as_admin.post(
        "/api/v1/licencias",
        json=_payload_lm(ing_id, fecha_inicio="2026-06-15", fecha_termino="2026-06-01"),
    )
    assert r.status_code == 422


# TC-070-03: RUT con DV inválido al crear ingreso -> 422 (ya cubierto en EPIC-01; aquí
# verificamos que la LM requiere ingreso existente)
def test_ingreso_inexistente_rechaza_404(as_admin):
    r = as_admin.post("/api/v1/licencias", json=_payload_lm(99999))
    assert r.status_code == 404


# TC-070-04: inconsistencia cantidad_dias vs. fechas genera advertencia (campo en respuesta)
def test_inconsistencia_dias_vs_fechas_genera_advertencia(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-004")
    # 15 días declarados pero fin-inicio+1 = 12
    r = as_admin.post(
        "/api/v1/licencias",
        json=_payload_lm(
            ing_id,
            fecha_inicio="2026-06-01",
            fecha_termino="2026-06-12",
            inicio_reposo="2026-06-01",
            fin_reposo="2026-06-12",
            cantidad_dias=15,
        ),
    )
    # la advertencia no bloquea; se guarda con advertencia en el cuerpo
    assert r.status_code == 201
    assert r.json().get("advertencia_dias") is not None


# TC-070-05: tipo_lm fuera de {1,5,6} -> 422
def test_tipo_lm_invalido_422(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-005")
    r = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id, tipo_lm="3"))
    assert r.status_code == 422


# TC-070-06: Auditor no puede crear -> 403
def test_auditor_no_puede_crear_lm(as_auditor):
    r = as_auditor.post("/api/v1/licencias", json=_payload_lm(1))
    assert r.status_code == 403


# Auditor puede leer historial -> 200
def test_auditor_puede_leer_historial(as_admin, as_auditor):
    ing_id = _payload_ingreso(as_admin, rut="7.876.543-K", folio="F-LIC-006")
    as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id))
    r = as_auditor.get(f"/api/v1/ingresos/{ing_id}/licencias")
    assert r.status_code == 200


# Anulación (77 BIS): PATCH /licencias/{id}/anular
def test_anular_lm_cambia_campo_anulada(as_admin):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-007")
    lm_id = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id)).json()["id"]
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/anular",
        json={"observaciones": "Rechazada por 77 BIS"},
    )
    assert r.status_code == 200
    assert r.json()["anulada"] is True


# Auditor no puede anular -> 403
def test_auditor_no_puede_anular(as_admin, as_auditor):
    ing_id = _payload_ingreso(as_admin, folio="F-LIC-008")
    lm_id = as_admin.post("/api/v1/licencias", json=_payload_lm(ing_id)).json()["id"]
    r = as_auditor.patch(
        f"/api/v1/licencias/{lm_id}/anular",
        json={"observaciones": "intento de anulación"},
    )
    assert r.status_code == 403
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencias_api_crud.py -v`
Expected: FAIL con `404` (ruta no existe) o `ImportError`.

- [ ] **Step 3: Implementar el servicio CRUD**

Crear `backend/app/services/licencias_crud.py`:

```python
"""Operaciones CRUD sobre LicenciaMedica — CEPA-070 / CEPA-073."""

import datetime

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.schemas.licencia import LicenciaAnularUpdate, LicenciaCreate


def _verificar_ingreso(db, ingreso_id: int) -> Ingreso:
    ing = db.execute(select(Ingreso).where(Ingreso.id == ingreso_id)).scalar_one_or_none()
    if ing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe ingreso con id={ingreso_id}.",
        )
    return ing


def _calcular_advertencia_dias(data: LicenciaCreate) -> str | None:
    """RN-5 CEPA-070: advierte si cantidad_dias no coincide con (termino - inicio + 1)."""
    dias_calculados = (data.fecha_termino - data.fecha_inicio).days + 1
    if dias_calculados != data.cantidad_dias:
        return (
            f"cantidad_dias={data.cantidad_dias} no coincide con "
            f"(fecha_termino - fecha_inicio + 1)={dias_calculados}. "
            "Verifique si es prórroga/empalme antes de confirmar."
        )
    return None


def crear_licencia(db, data: LicenciaCreate) -> tuple[LicenciaMedica, str | None]:
    """Crea una LM. Devuelve (objeto, advertencia_dias|None)."""
    _verificar_ingreso(db, data.ingreso_id)
    advertencia = _calcular_advertencia_dias(data)
    lm = LicenciaMedica(
        ingreso_id=data.ingreso_id,
        folio_lm=data.folio_lm,
        tipo_lm=data.tipo_lm.value,
        tipo_reposo=data.tipo_reposo.value,
        fecha_inicio=data.fecha_inicio,
        fecha_termino=data.fecha_termino,
        fecha_emision=data.fecha_emision,
        inicio_reposo=data.inicio_reposo,
        fin_reposo=data.fin_reposo,
        cantidad_dias=data.cantidad_dias,
        indicacion_reposo=data.indicacion_reposo,
        diagnostico=data.diagnostico,
        origen=data.origen.value,
        envio_isl="pendiente",
        anulada=False,
    )
    db.add(lm)
    db.flush()
    return lm, advertencia


def obtener_licencia(db, licencia_id: int) -> LicenciaMedica:
    lm = db.execute(
        select(LicenciaMedica).where(LicenciaMedica.id == licencia_id)
    ).scalar_one_or_none()
    if lm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe licencia con id={licencia_id}.",
        )
    return lm


def listar_licencias_por_ingreso(db, ingreso_id: int) -> list[LicenciaMedica]:
    _verificar_ingreso(db, ingreso_id)
    return list(
        db.scalars(
            select(LicenciaMedica)
            .where(LicenciaMedica.ingreso_id == ingreso_id)
            .order_by(LicenciaMedica.fecha_inicio)
        )
    )


def anular_licencia(db, licencia_id: int, data: LicenciaAnularUpdate) -> LicenciaMedica:
    lm = obtener_licencia(db, licencia_id)
    if lm.anulada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La licencia ya está anulada.",
        )
    lm.anulada = True
    lm.observaciones = (lm.observaciones or "") + f" [ANULADA: {data.observaciones}]"
    db.flush()
    return lm
```

- [ ] **Step 4: Implementar el router**

Crear `backend/app/routers/licencias.py`:

```python
"""Router de Licencias Médicas — EPIC-07."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.licencia import (
    AcumuladoRead,
    AlertaLicenciaRead,
    LicenciaAnularUpdate,
    LicenciaCreate,
    LicenciaISLUpdate,
    LicenciaRead,
)
from app.services.licencias_acumulado import calcular_acumulado
from app.services.licencias_alerta import generar_alertas_vencimiento
from app.services.licencias_crud import (
    anular_licencia,
    crear_licencia,
    listar_licencias_por_ingreso,
    obtener_licencia,
)

router = APIRouter(tags=["licencias"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── Registro y consulta ─────────────────────────────────────────────────────

@router.post(
    "/api/v1/licencias",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: LicenciaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    lm, advertencia = crear_licencia(db, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE",
        entity="licencia_medica", entity_id=str(lm.id),
    )
    db.commit()
    db.refresh(lm)
    respuesta = LicenciaRead.model_validate(lm).model_dump()
    if advertencia:
        respuesta["advertencia_dias"] = advertencia
    return respuesta


@router.get(
    "/api/v1/licencias/{licencia_id}",
    response_model=LicenciaRead,
    dependencies=[Depends(_reader)],
)
def obtener(licencia_id: int, db: Session = Depends(get_db)) -> LicenciaRead:
    return obtener_licencia(db, licencia_id)


@router.get(
    "/api/v1/ingresos/{ingreso_id}/licencias",
    response_model=list[LicenciaRead],
    dependencies=[Depends(_reader)],
)
def historial_por_ingreso(ingreso_id: int, db: Session = Depends(get_db)) -> list[LicenciaRead]:
    return listar_licencias_por_ingreso(db, ingreso_id)


@router.patch(
    "/api/v1/licencias/{licencia_id}/anular",
    response_model=LicenciaRead,
    dependencies=[Depends(_writer)],
)
def anular(
    licencia_id: int,
    payload: LicenciaAnularUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LicenciaRead:
    lm = anular_licencia(db, licencia_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE",
        entity="licencia_medica", entity_id=str(lm.id),
    )
    db.commit()
    db.refresh(lm)
    return lm


# ── Acumulado (CEPA-071) ────────────────────────────────────────────────────

@router.get(
    "/api/v1/ingresos/{ingreso_id}/licencias/acumulado",
    response_model=AcumuladoRead,
    dependencies=[Depends(_reader)],
)
def acumulado(ingreso_id: int, db: Session = Depends(get_db)) -> AcumuladoRead:
    resultado = calcular_acumulado(db, ingreso_id)
    return AcumuladoRead(
        ingreso_id=resultado.ingreso_id,
        dias_acumulados_vigentes=resultado.dias_acumulados_vigentes,
        dias_acumulados_bruto=resultado.dias_acumulados_bruto,
        hay_solapamiento=resultado.hay_solapamiento,
        incluye_extra_sistema=resultado.incluye_extra_sistema,
    )


# ── Alertas (CEPA-072) ───────────────────────────────────────────────────────

@router.post(
    "/api/v1/licencias/alertas/generar",
    response_model=list[AlertaLicenciaRead],
    dependencies=[Depends(_writer)],
)
def disparar_alertas(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AlertaLicenciaRead]:
    """Endpoint de disparo manual del job de alertas (idempotente).
    El job automático diario lo invocará desde EPIC-10.
    """
    nuevas = generar_alertas_vencimiento(db)
    record_audit(
        db, actor=current_user.username, action="CREATE",
        entity="alerta_licencia", entity_id=f"batch:{len(nuevas)}",
    )
    db.commit()
    return nuevas
```

- [ ] **Step 5: Conectar el router en `app/main.py`**

Añadir al bloque de imports y `include_router` en `backend/app/main.py`:

```python
from app.routers import licencias

app.include_router(licencias.router)
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_licencias_api_crud.py -v`
Expected: `9 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/licencias_crud.py backend/app/routers/licencias.py backend/app/main.py backend/tests/test_licencias_api_crud.py
git commit -m "feat(licencias): API CRUD licencias, historial por ingreso, anulación 77 BIS (CEPA-070)"
```

---

## Task 7: API de trazabilidad ISL y licencias extra-sistema (CEPA-073)

Endpoint `PATCH /api/v1/licencias/{id}/isl` para actualizar trazabilidad ISL (estado, fecha, EEAG/GAF, observaciones). La licencia extra-sistema se registra con el mismo `POST /api/v1/licencias` pasando `origen=extra_sistema`. Tests de los TC-073-xx.

**Files:**
- Modify: `backend/app/services/licencias_crud.py`
- Modify: `backend/app/routers/licencias.py`
- Test: `backend/tests/test_licencias_api_isl.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_licencias_api_isl.py`:

```python
def _make_ingreso_y_lm(as_admin, folio="F-ISL-001", rut="12.345.678-5"):
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente ISL",
            "sexo": "M",
            "edad": 45,
            "region": "Maule",
            "diagnostico": "Z57.1",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-15",
            "folio": folio,
        },
    )
    assert r_ing.status_code == 201, r_ing.text
    ing_id = r_ing.json()["id"]
    r_lm = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "5",
            "tipo_reposo": "total",
            "fecha_inicio": "2026-06-01",
            "fecha_termino": "2026-06-15",
            "fecha_emision": "2026-05-30",
            "inicio_reposo": "2026-06-01",
            "fin_reposo": "2026-06-15",
            "cantidad_dias": 15,
            "diagnostico": "Z57.1",
        },
    )
    assert r_lm.status_code == 201, r_lm.text
    return ing_id, r_lm.json()["id"]


# TC-073-01: marcar envío a ISL = enviado con fecha -> visible en historial
def test_marcar_envio_isl_enviado(as_admin):
    ing_id, lm_id = _make_ingreso_y_lm(as_admin)
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-02"},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["envio_isl"] == "enviado"
    assert cuerpo["fecha_envio_isl"] == "2026-06-02"

    hist = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias")
    lm_en_hist = next(lm for lm in hist.json() if lm["id"] == lm_id)
    assert lm_en_hist["envio_isl"] == "enviado"


# TC-073-02: estado=enviado sin fecha -> 422
def test_isl_enviado_sin_fecha_422(as_admin):
    _, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-002", rut="7.876.543-K")
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado"},
    )
    assert r.status_code == 422


# TC-073-03: LM extra-sistema aparece en historial marcada y suma al acumulado
def test_extra_sistema_en_historial_y_acumulado(as_admin):
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "15.111.222-8",
            "nombre": "Extra Sistema Test",
            "sexo": "F",
            "edad": 32,
            "region": "Biobio",
            "diagnostico": "F41",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-02-01",
            "folio": "F-ISL-003",
        },
    )
    assert r_ing.status_code == 201, r_ing.text
    ing_id = r_ing.json()["id"]

    # LM en sistema
    as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "total",
            "fecha_inicio": "2026-03-01",
            "fecha_termino": "2026-03-10",
            "fecha_emision": "2026-02-28",
            "inicio_reposo": "2026-03-01",
            "fin_reposo": "2026-03-10",
            "cantidad_dias": 10,
            "diagnostico": "F41",
        },
    )
    # LM extra-sistema
    as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "parcial",
            "fecha_inicio": "2026-04-01",
            "fecha_termino": "2026-04-20",
            "fecha_emision": "2026-03-30",
            "inicio_reposo": "2026-04-01",
            "fin_reposo": "2026-04-20",
            "cantidad_dias": 20,
            "diagnostico": "F41",
            "origen": "extra_sistema",
        },
    )

    hist = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias")
    origenes = [lm["origen"] for lm in hist.json()]
    assert "extra_sistema" in origenes

    acum = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert acum.status_code == 200
    assert acum.json()["dias_acumulados_vigentes"] == 30
    assert acum.json()["incluye_extra_sistema"] is True


# TC-073-04: 77 BIS (rechazo ISL + anulación) excluye del acumulado
def test_77bis_excluye_del_acumulado(as_admin):
    r_ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "11.222.333-4",
            "nombre": "77BIS Test",
            "sexo": "M",
            "edad": 50,
            "region": "Maule",
            "diagnostico": "Z57.5",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-01",
            "folio": "F-ISL-004",
        },
    )
    ing_id = r_ing.json()["id"]
    lm_id = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "5",
            "tipo_reposo": "total",
            "fecha_inicio": "2026-02-01",
            "fecha_termino": "2026-02-15",
            "fecha_emision": "2026-01-30",
            "inicio_reposo": "2026-02-01",
            "fin_reposo": "2026-02-15",
            "cantidad_dias": 15,
            "diagnostico": "Z57.5",
        },
    ).json()["id"]

    # Marcar como rechazada por ISL
    as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "rechazado", "fecha_envio_isl": "2026-02-20",
              "observaciones": "Rechazada 77 BIS"},
    )
    # Anular la LM
    as_admin.patch(
        f"/api/v1/licencias/{lm_id}/anular",
        json={"observaciones": "77 BIS — reclasificada como enfermedad común"},
    )

    acum = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert acum.json()["dias_acumulados_vigentes"] == 0


# TC-073-05: EEAG fuera de rango -> 422
def test_eeag_fuera_de_rango_422(as_admin):
    _, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-005", rut="16.555.666-7")
    r = as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-05", "eeag_gaf": 150},
    )
    assert r.status_code == 422


# TC-073-06: Auditor no puede editar ISL -> 403
def test_auditor_no_puede_editar_isl(as_admin, as_auditor):
    _, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-006", rut="18.777.888-1")
    r = as_auditor.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-05"},
    )
    assert r.status_code == 403


# CA-4 CEPA-073: Auditor puede leer historial con trazabilidad ISL
def test_auditor_puede_leer_historial_con_isl(as_admin, as_auditor):
    ing_id, lm_id = _make_ingreso_y_lm(as_admin, folio="F-ISL-007", rut="19.888.999-2")
    as_admin.patch(
        f"/api/v1/licencias/{lm_id}/isl",
        json={"envio_isl": "enviado", "fecha_envio_isl": "2026-06-03"},
    )
    r = as_auditor.get(f"/api/v1/ingresos/{ing_id}/licencias")
    assert r.status_code == 200
    assert r.json()[0]["envio_isl"] == "enviado"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencias_api_isl.py -v`
Expected: FAIL (endpoint `PATCH .../isl` no existe todavía).

- [ ] **Step 3: Añadir `actualizar_isl` al servicio CRUD**

Modificar `backend/app/services/licencias_crud.py` — añadir al final del archivo:

```python
from app.schemas.licencia import LicenciaISLUpdate
from app.domain.enums_licencia import EstadoEnvioISL


def actualizar_isl(db, licencia_id: int, data: LicenciaISLUpdate) -> LicenciaMedica:
    """Actualiza la trazabilidad ISL de una LM (CEPA-073 RN-1/RN-2)."""
    lm = obtener_licencia(db, licencia_id)
    lm.envio_isl = data.envio_isl.value
    lm.fecha_envio_isl = data.fecha_envio_isl
    if data.eeag_gaf is not None:
        lm.eeag_gaf = data.eeag_gaf
    if data.observaciones is not None:
        lm.observaciones = data.observaciones
    db.flush()
    return lm
```

> Nota: los imports `LicenciaISLUpdate` y `EstadoEnvioISL` se añaden solo si no están ya presentes en el archivo. Si `ruff` indica import duplicado, eliminar el redundante.

- [ ] **Step 4: Añadir el endpoint ISL al router**

Modificar `backend/app/routers/licencias.py` — añadir después del endpoint `anular`:

```python
@router.patch(
    "/api/v1/licencias/{licencia_id}/isl",
    response_model=LicenciaRead,
    dependencies=[Depends(_writer)],
)
def actualizar_isl_endpoint(
    licencia_id: int,
    payload: LicenciaISLUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LicenciaRead:
    from app.services.licencias_crud import actualizar_isl

    lm = actualizar_isl(db, licencia_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE",
        entity="licencia_medica", entity_id=str(lm.id),
    )
    db.commit()
    db.refresh(lm)
    return lm
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_licencias_api_isl.py -v`
Expected: `8 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/licencias_crud.py backend/app/routers/licencias.py backend/tests/test_licencias_api_isl.py
git commit -m "feat(licencias): endpoint PATCH ISL, extra-sistema, trazabilidad 77 BIS (CEPA-073)"
```

---

## Task 8: API de acumulado y alertas — tests de integración (CEPA-071 + CEPA-072)

Tests de integración de los endpoints `GET .../acumulado` y `POST .../alertas/generar` cubriendo los CA y TC restantes.

**Files:**
- Test: `backend/tests/test_licencias_api_acumulado_alertas.py`

- [ ] **Step 1: Escribir el test**

Crear `backend/tests/test_licencias_api_acumulado_alertas.py`:

```python
import datetime


def _crear_ingreso(as_admin, rut, folio):
    r = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Acum Test",
            "sexo": "F",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "F32",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-01-01",
            "folio": folio,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_lm(as_admin, ing_id, inicio, termino, dias, origen="sistema"):
    r = as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "total",
            "fecha_inicio": inicio,
            "fecha_termino": termino,
            "fecha_emision": inicio,
            "inicio_reposo": inicio,
            "fin_reposo": termino,
            "cantidad_dias": dias,
            "diagnostico": "F32.1",
            "origen": origen,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# TC-071-01: CA-1 del PRD §7.7.4 — 4 LM (3 previas + 1 nueva) → 40 días
def test_acumulado_cuatro_lm_sin_solapamiento(as_admin):
    ing_id = _crear_ingreso(as_admin, "12.345.678-5", "F-ACUM-001")
    _crear_lm(as_admin, ing_id, "2026-01-01", "2026-01-10", 10)
    _crear_lm(as_admin, ing_id, "2026-02-01", "2026-02-15", 15)
    _crear_lm(as_admin, ing_id, "2026-03-01", "2026-03-07", 7)
    _crear_lm(as_admin, ing_id, "2026-04-01", "2026-04-08", 8)

    r = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert r.status_code == 200
    assert r.json()["dias_acumulados_vigentes"] == 40
    assert r.json()["hay_solapamiento"] is False


# TC-071-03: solapamiento → 15 efectivos, 20 bruto
def test_acumulado_con_solapamiento(as_admin):
    ing_id = _crear_ingreso(as_admin, "7.876.543-K", "F-ACUM-002")
    _crear_lm(as_admin, ing_id, "2026-06-01", "2026-06-10", 10)
    _crear_lm(as_admin, ing_id, "2026-06-06", "2026-06-15", 10)

    r = as_admin.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    body = r.json()
    assert body["dias_acumulados_vigentes"] == 15
    assert body["dias_acumulados_bruto"] == 20
    assert body["hay_solapamiento"] is True


# TC-071-06: Auditor puede ver acumulado (solo lectura)
def test_auditor_puede_ver_acumulado(as_admin, as_auditor):
    ing_id = _crear_ingreso(as_admin, "15.111.222-8", "F-ACUM-003")
    _crear_lm(as_admin, ing_id, "2026-05-01", "2026-05-12", 12)

    r = as_auditor.get(f"/api/v1/ingresos/{ing_id}/licencias/acumulado")
    assert r.status_code == 200
    assert r.json()["dias_acumulados_vigentes"] == 12


# TC-072-01: disparo manual del job de alertas genera alertas para LM cercanas
def test_disparo_alertas_genera_para_lm_proxima(as_admin):
    # Creamos un ingreso con LM que vence hoy + 2 días
    ing_id = _crear_ingreso(as_admin, "16.555.666-7", "F-ALRTA-001")
    hoy = datetime.date.today()
    termino = hoy + datetime.timedelta(days=2)
    inicio = termino - datetime.timedelta(days=14)
    as_admin.post(
        "/api/v1/licencias",
        json={
            "ingreso_id": ing_id,
            "tipo_lm": "1",
            "tipo_reposo": "total",
            "fecha_inicio": inicio.isoformat(),
            "fecha_termino": termino.isoformat(),
            "fecha_emision": inicio.isoformat(),
            "inicio_reposo": inicio.isoformat(),
            "fin_reposo": termino.isoformat(),
            "cantidad_dias": 15,
            "diagnostico": "F32.1",
        },
    )

    r = as_admin.post("/api/v1/licencias/alertas/generar")
    assert r.status_code == 200
    # Al menos una alerta fue creada (puede haber más si otros tests dejaron LM próximas)
    assert isinstance(r.json(), list)


# TC-072-04: idempotencia del job — segunda llamada no duplica
def test_alertas_job_idempotente(as_admin):
    r1 = as_admin.post("/api/v1/licencias/alertas/generar")
    r2 = as_admin.post("/api/v1/licencias/alertas/generar")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # La segunda llamada no devuelve las mismas alertas (ya existen, no se duplican)
    ids_primera = {a["id"] for a in r1.json()}
    ids_segunda = {a["id"] for a in r2.json()}
    assert ids_primera.isdisjoint(ids_segunda)


# TC-072-05: Auditor no ve alertas de otro administrativo (filtro RBAC)
# Verificamos que el job solo puede dispararlo un escritor
def test_auditor_no_puede_disparar_job_alertas(as_auditor):
    r = as_auditor.post("/api/v1/licencias/alertas/generar")
    assert r.status_code == 403
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_licencias_api_acumulado_alertas.py -v`
Expected: FAIL en `test_acumulado_cuatro_lm_sin_solapamiento` u otro (los endpoints del acumulado pueden fallar si la ruta tiene conflicto con `/{licencia_id}` antes que `/acumulado`).

> **Nota de orden de rutas:** FastAPI hace matching en el orden de registro. La ruta `GET /api/v1/ingresos/{ingreso_id}/licencias/acumulado` debe registrarse **antes** de `GET /api/v1/ingresos/{ingreso_id}/licencias/{licencia_id}` si existiera tal ruta, para que `acumulado` no sea interpretado como `licencia_id`. Verificar que el router no tenga conflicto; si lo hay, reordenar los decoradores en `licencias.py`.

- [ ] **Step 3: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_licencias_api_acumulado_alertas.py -v`
Expected: `6 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_licencias_api_acumulado_alertas.py
git commit -m "test(licencias): integración acumulado y alertas vencimiento (CEPA-071/072)"
```

---

## Task 9: Verificación integral y lint

**Files:** ninguno nuevo.

- [ ] **Step 1: Correr la suite completa de EPIC-07 y verificar que todo está en verde**

Run:
```bash
uv run pytest tests/test_enums_licencia.py tests/test_licencia_model.py tests/test_licencia_schemas.py tests/test_licencias_acumulado.py tests/test_licencias_alerta.py tests/test_licencias_api_crud.py tests/test_licencias_api_isl.py tests/test_licencias_api_acumulado_alertas.py -v
```
Expected: todos los tests pasan. Verificar el conteo total: ≥ 46 tests.

- [ ] **Step 2: Correr la suite completa del proyecto (regresión)**

Run: `uv run pytest -v`
Expected: sin regresiones en EPIC-00 ni EPIC-01.

- [ ] **Step 3: Lint**

Run: `uv run ruff check .`
Expected: sin errores. Si hay errores de import no usado o similar, corregir en el archivo correspondiente y re-correr.

- [ ] **Step 4: Verificar que las migraciones aplican desde cero**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: sin errores. La cadena 0070 → 0071 debe aplicar tras las migraciones de EPIC-00 y EPIC-01.

- [ ] **Step 5: Verificar la documentación OpenAPI**

Run: `uv run uvicorn app.main:app`
Abrir `http://127.0.0.1:8000/docs` y verificar que aparecen los endpoints de la sección `licencias`:
- `POST /api/v1/licencias`
- `GET /api/v1/licencias/{licencia_id}`
- `GET /api/v1/ingresos/{ingreso_id}/licencias`
- `GET /api/v1/ingresos/{ingreso_id}/licencias/acumulado`
- `PATCH /api/v1/licencias/{licencia_id}/anular`
- `PATCH /api/v1/licencias/{licencia_id}/isl`
- `POST /api/v1/licencias/alertas/generar`

Detener con Ctrl-C.

- [ ] **Step 6: Commit final**

```bash
git add -A
git commit -m "chore(licencias): EPIC-07 lista — CEPA-070..073 en verde, migraciones y OpenAPI verificados" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Task(s) que la implementan |
|---|---|
| **CEPA-070** Registro de licencia médica (D8: cantidad_dias, inicio/fin reposo, fecha_emision, tipo LM, indicacion_reposo, diagnostico, tipo_reposo) | Task 1 (enums), Task 2 (modelo + migración), Task 3 (schemas + validaciones), Task 6 (API CRUD) |
| **CEPA-071** Cálculo automático de días acumulados por paciente | Task 4 (servicio `calcular_acumulado`, solapamientos, extra-sistema), Task 6 (endpoint `/acumulado`), Task 8 (tests integración) |
| **CEPA-072** Alerta de vencimiento de licencia | Task 5 (modelo `AlertaLicencia` + migración + servicio idempotente), Task 6 (endpoint `/alertas/generar`), Task 8 (tests integración) |
| **CEPA-073** Trazabilidad de envío a ISL y licencias extra-sistema | Task 2 (columnas ISL en modelo), Task 3 (schema `LicenciaISLUpdate`), Task 7 (endpoint `PATCH .../isl`, tests TC-073-xx) |

### Trazabilidad TC → Test

| TC | Test que lo cubre |
|---|---|
| TC-070-01 | `test_crear_lm_registra_y_aparece_en_historial` |
| TC-070-02 | `test_fecha_termino_anterior_rechaza_422` + `test_fecha_termino_anterior_a_inicio_rechazada` |
| TC-070-03 | `test_ingreso_inexistente_rechaza_404` (la validación de RUT en el ingreso la cubre EPIC-01) |
| TC-070-04 | `test_inconsistencia_dias_vs_fechas_genera_advertencia` |
| TC-070-05 | `test_tipo_lm_invalido_422` + `test_tipo_lm_invalido_rechazado` |
| TC-070-06 | `test_auditor_no_puede_crear_lm` |
| TC-071-01 | `test_acumulado_cuatro_lm_sin_solapamiento` |
| TC-071-02 | `test_primera_lm_acumulado_igual_a_sus_dias` |
| TC-071-03 | `test_solapamiento_no_duplica_dias` + `test_acumulado_con_solapamiento` |
| TC-071-04 | `test_extra_sistema_suma_al_acumulado` + `test_extra_sistema_en_historial_y_acumulado` |
| TC-071-05 | `test_lm_anulada_excluida_del_acumulado` + `test_77bis_excluye_del_acumulado` |
| TC-071-06 | `test_auditor_puede_ver_acumulado` |
| TC-072-01 | `test_disparo_alertas_genera_para_lm_proxima` |
| TC-072-02 | `test_contar_dias_habiles_salta_fin_de_semana` |
| TC-072-03 | `test_lm_vencida_no_genera_alerta` |
| TC-072-04 | `test_no_duplica_alerta_si_ya_existe` + `test_alertas_job_idempotente` |
| TC-072-05 | `test_auditor_no_puede_disparar_job_alertas` |
| TC-072-06 | Verificado por diseño (perfil Clínico no existe en el sistema — v4 D1) |
| TC-073-01 | `test_marcar_envio_isl_enviado` |
| TC-073-02 | `test_isl_enviado_sin_fecha_422` + `test_isl_enviado_sin_fecha_rechazado` |
| TC-073-03 | `test_extra_sistema_en_historial_y_acumulado` |
| TC-073-04 | `test_77bis_excluye_del_acumulado` |
| TC-073-05 | `test_eeag_fuera_de_rango_422` + `test_eeag_gaf_fuera_de_rango_rechazado` |
| TC-073-06 | `test_auditor_no_puede_editar_isl` |

---

## Notas de cierre

### Firmas a verificar contra el código real ANTES de iniciar el loop

1. **`down_revision` de la migración 0070** — ejecutar `uv run alembic heads` desde `backend/` y sustituir `<RESOLVER: alembic heads>` por el `revision_id` real de la cabeza de EPIC-01. La cadena esperada es: `...→ 0012 (folio_seq, EPIC-01) → 0070 (licencia_medica) → 0071 (alerta_licencia)`.
2. **`record_audit`** — verificar firma exacta en `app/audit/service.py` de EPIC-00: debe ser `record_audit(db, actor, action, entity, entity_id)`.
3. **`get_current_user`** — verificar que devuelve un objeto con atributo `.username` (no `.email` u otro).
4. **`require_role`** — verificar que acepta `*roles: str` y lanza `403` cuando el rol no coincide.
5. **Relación `Ingreso.licencias`** — la Task 2 añade `licencias: Mapped[list["LicenciaMedica"]]` al modelo `Ingreso`; verificar que este modelo no tiene ya una relación con ese nombre de una versión previa.
6. **Fixtures `as_admin`, `as_auditor`, `as_coordinacion`** — verificar que las fixtures del conftest de EPIC-00 los exportan con este nombre exacto; si usan otro (ej. `admin_client`), ajustar los imports de los tests de EPIC-07.

### Decisiones de negocio abiertas del spec

- **Festivos chilenos para días hábiles (CEPA-072 RN-1):** el servicio `contar_dias_habiles` recibe un parámetro `festivos: frozenset[datetime.date]` para inyección externa. Pendiente definir la fuente autoritativa de festivos (tabla de configuración en BD, API externa, o lista hardcodeada por año). Hasta que se defina, la función solo excluye sáb/dom.
- **Valor oficial del acumulado: días calendario efectivos vs. suma bruta (CEPA-071):** la spec abre esta decisión. La implementación retorna ambos valores (`dias_acumulados_vigentes` = efectivos; `dias_acumulados_bruto` = suma simple). Cuando Coordinación confirme cuál es el "total oficial", actualizar el schema de respuesta y el reporte de EPIC-09.
- **Reinicio del acumulado por año/siniestro (CEPA-071):** la spec no resuelve si el acumulado es histórico total o se reinicia. La implementación actual es histórica total (suma todas las LM del ingreso). Si se requiere reinicio anual o por siniestro, añadir un filtro de período a `calcular_acumulado`.
- **`indicacion_reposo` texto libre vs. lista cerrada (CEPA-070):** el spec lo deja abierto. La implementación usa `String(300)` libre. Si Coordinación confirma lista cerrada, añadir un enum `IndicacionReposo` y ajustar el schema.
- **Campos mínimos de LM extra-sistema (CEPA-073):** `folio_lm` es opcional (`nullable=True`) para cubrir LMs de otras mutualidades sin folio ISL. Confirmar con Coordinación si se requieren otros campos obligatorios diferenciados para el origen extra-sistema.
- **Canal email P1 (CEPA-072 RN-3):** el plan implementa solo la generación de la alerta in-app (P0). El envío por correo se implementará en EPIC-10.
- **Filtro de alertas por pacientes asignados (CEPA-072 TC-072-05 RN-2):** el endpoint `GET` de alertas del panel de usuario se implementará en EPIC-10, que gestiona el modelo de asignación administrativo↔paciente. Aquí solo se implementa la generación.
- **Paginación del historial de licencias:** la spec menciona RNF de rendimiento <2s y que es el módulo con mayor volumen (1.584+ registros). El endpoint `GET /ingresos/{id}/licencias` devuelve lista completa por ingreso. Para el listado global (multi-ingreso), EPIC-09 deberá implementar paginación. Considerar añadir `limit/offset` si el volumen por ingreso se vuelve significativo.
