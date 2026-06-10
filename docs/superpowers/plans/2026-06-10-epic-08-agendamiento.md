# EPIC-08 — Agendamiento Inteligente — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar la propuesta automática de agenda diaria, semanal y mensual por profesional (CEPA-080), con exclusión de reposos vigentes, priorización de controles vencidos/próximos y recetas recientes, respeto de cupo y disponibilidad diaria, confirmación de citas y alimentación del denominador de adherencia — sobre Fundación + EPIC-00 + EPIC-01 + EPIC-06 (controles) + EPIC-07 (licencias) ya en `main`.

**Architecture:** El módulo de agendamiento vive en `app/agendamiento/`. La lógica algorítmica de propuesta (selección, exclusión por reposo, priorización, distribución) reside en `app/agendamiento/scheduler.py` como funciones puras sin I/O, altamente testables en aislamiento. El servicio `app/agendamiento/service.py` orquesta la carga de datos desde BD y llama al scheduler. El router expone `/api/v1/propuestas-agenda` y `/api/v1/citas-propuestas`. Una migración Alembic por historia que toca el esquema. Todo respeta las reglas de portabilidad D15 (tipos genéricos, `Identity`/`BigInteger`, ≤30 chars, UTC).

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`. Fixtures: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Prioridad:** P1 Should — Sprint 1-2 (PRD §11.2). Oleada 4 (depende de EPIC-01 y EPIC-06).

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`.
- Fixtures `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client` (de EPIC-00).
- Tabla `licencia` con columna `reposo_inicio: Date`, `reposo_fin: Date`, `paciente_id: int` (EPIC-07).
- Tabla `control` con columna `fecha_prox_control: Date`, `paciente_id: int`, `profesional_id: int` (EPIC-06).
- Tabla `receta` con columnas `fecha_emision: Date`, `fecha_revision: Date | None`, `requiere_seguimiento: bool`, `gestionada: bool`, `paciente_id: int` (EPIC-02).
- Tabla `paciente` con `id: int`, `nombre: str` (EPIC-01).

---

## Convenciones de modelado de esta épica

- **PK subrogada:** `id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)`.
- **Fechas de calendario:** `Date` (sin hora). Fechas con hora en UTC: `DateTime(timezone=True)`.
- **Listas cerradas:** Enums Python `str, Enum`; columna `String(30)`; sin tipos enum nativos del motor.
- **Identificadores:** minúscula y ≤30 caracteres.
- **Helper UTC:** `def _utcnow() -> datetime: return datetime.now(timezone.utc)`.

Tablas nuevas: `disponibilidad_prof`, `propuesta_agenda`, `cita_propuesta`.

---

## Task 1: Enums y modelos del módulo de agendamiento + migración

Crea los Enums de dominio, los tres modelos portables y la primera migración Alembic.

**Files:**
- Create: `backend/app/agendamiento/__init__.py` (vacío)
- Create: `backend/app/agendamiento/enums.py`
- Create: `backend/app/agendamiento/models.py`
- Create: `backend/migrations/versions/0801_agendamiento_tablas.py`
- Modify: `backend/app/models/__init__.py` (registrar los nuevos modelos)
- Test: `backend/tests/agendamiento/test_agendamiento_models.py`

- [ ] **Step 1: Crear directorio de tests y escribir el test que falla**

```bash
mkdir -p backend/tests/agendamiento
touch backend/tests/agendamiento/__init__.py
```

Crear `backend/tests/agendamiento/test_agendamiento_models.py`:

```python
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, SmallInteger, String

from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda


def _nombres(tabla):
    return set(tabla.columns.keys())


def test_disponibilidad_prof_columnas():
    t = DisponibilidadProf.__table__
    assert t.name == "disponibilidad_prof"
    assert _nombres(t) == {
        "id", "profesional_id", "dia_semana", "cupo_diario", "activo", "created_at",
    }


def test_propuesta_agenda_columnas():
    t = PropuestaAgenda.__table__
    assert t.name == "propuesta_agenda"
    assert _nombres(t) == {
        "id", "profesional_id", "tipo", "fecha_inicio", "fecha_fin",
        "estado", "generado_por", "created_at",
    }


def test_cita_propuesta_columnas():
    t = CitaPropuesta.__table__
    assert t.name == "cita_propuesta"
    assert _nombres(t) == {
        "id", "propuesta_id", "paciente_id", "fecha_candidata",
        "prioridad", "razon", "estado", "excluida_por", "created_at",
    }


def test_portabilidad_identificadores():
    for modelo in (DisponibilidadProf, PropuestaAgenda, CitaPropuesta):
        t = modelo.__table__
        for nombre in [t.name, *t.columns.keys()]:
            assert nombre == nombre.lower(), f"{nombre} debe ser minúscula"
            assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pks_son_biginteger_con_identity():
    for modelo in (DisponibilidadProf, PropuestaAgenda, CitaPropuesta):
        cols = modelo.__table__.columns
        assert isinstance(cols["id"].type, BigInteger)
        assert cols["id"].identity is not None


def test_fechas_con_timezone():
    for modelo in (DisponibilidadProf, PropuestaAgenda, CitaPropuesta):
        cols = modelo.__table__.columns
        assert isinstance(cols["created_at"].type, DateTime)
        assert cols["created_at"].type.timezone is True
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/agendamiento/test_agendamiento_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.agendamiento.models'`.

- [ ] **Step 3: Crear `backend/app/agendamiento/__init__.py`**

Archivo vacío.

- [ ] **Step 4: Crear `backend/app/agendamiento/enums.py`**

```python
"""Listas cerradas del módulo de agendamiento (EPIC-08).

Modelos como Enums de str: validación en capa de aplicación, sin tipos enum de motor (D15).
"""

from enum import Enum


class TipoPropuesta(str, Enum):
    """Horizonte de la propuesta de agenda."""
    DIARIA = "diaria"
    SEMANAL = "semanal"
    MENSUAL = "mensual"


class EstadoPropuesta(str, Enum):
    """Estado de ciclo de vida de una propuesta."""
    BORRADOR = "borrador"
    CONFIRMADA = "confirmada"
    DESCARTADA = "descartada"


class EstadoCita(str, Enum):
    """Estado de una cita dentro de una propuesta."""
    PROPUESTA = "propuesta"
    CONFIRMADA = "confirmada"
    DESCARTADA = "descartada"


class PrioridadCita(str, Enum):
    """Prioridad de candidatura según RN-2."""
    CONTROL_VENCIDO = "control_vencido"      # (1) más alta
    CONTROL_PROXIMO = "control_proximo"       # (2)
    SEGUIMIENTO_RECETA = "seguimiento_receta" # (3)


class DiaSemana(int, Enum):
    """ISO weekday: 1=lunes … 5=viernes (no se admiten 6=sáb, 7=dom — RN-4)."""
    LUNES = 1
    MARTES = 2
    MIERCOLES = 3
    JUEVES = 4
    VIERNES = 5
```

- [ ] **Step 5: Crear `backend/app/agendamiento/models.py`**

```python
"""Modelos SQLAlchemy del módulo de agendamiento.

Tres tablas portables (D15): disponibilidad_prof, propuesta_agenda, cita_propuesta.
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DisponibilidadProf(Base):
    """Disponibilidad semanal recurrente de un profesional (RN-3, RN-4).

    dia_semana: ISO weekday 1–5 (lunes–viernes).
    cupo_diario: máximo de citas propuestas ese día de semana.
    """

    __tablename__ = "disponibilidad_prof"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    profesional_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)          # 1–5
    cupo_diario: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class PropuestaAgenda(Base):
    """Propuesta de agenda generada para un profesional en un horizonte (diaria/semanal/mensual).

    tipo:       TipoPropuesta.value  — almacenado como String(10).
    estado:     EstadoPropuesta.value — almacenado como String(15).
    generado_por: username del actor que la generó (auditoría inline + RN-9).
    """

    __tablename__ = "propuesta_agenda"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    profesional_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="borrador")
    generado_por: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class CitaPropuesta(Base):
    """Cita individual dentro de una PropuestaAgenda.

    prioridad:   PrioridadCita.value — String(25).
    razon:       texto libre de hasta 120 chars (p. ej. "control vencido desde 2026-05-01").
    estado:      EstadoCita.value — String(15).
    excluida_por: motivo de exclusión si aplica (p. ej. "reposo vigente hasta 2026-06-20").
                  NULL si la cita no fue excluida.
    """

    __tablename__ = "cita_propuesta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    propuesta_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    paciente_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fecha_candidata: Mapped[date] = mapped_column(Date, nullable=False)
    prioridad: Mapped[str] = mapped_column(String(25), nullable=False)
    razon: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="propuesta")
    excluida_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
```

- [ ] **Step 6: Registrar modelos en `backend/app/models/__init__.py`**

Agregar al final del archivo existente:

```python
from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda  # noqa: F401
```

- [ ] **Step 7: Correr el test y verificar que pasa**

Run: `uv run pytest tests/agendamiento/test_agendamiento_models.py -v`
Expected: `6 passed`.

- [ ] **Step 8: Crear la migración Alembic `backend/migrations/versions/0801_agendamiento_tablas.py`**

> Nota: el `down_revision` debe apuntar a la última revisión en `main` al ejecutar este loop.
> Antes de crear la migración, verificar con: `uv run alembic heads`
> Reemplazar `<RESOLVER: alembic heads>` con ese valor (p. ej. `"0701"` si la última es de EPIC-07).

```python
"""agendamiento tablas: disponibilidad_prof, propuesta_agenda, cita_propuesta

Revision ID: 0801
Revises: <RESOLVER: alembic heads>
Create Date: 2026-06-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0801"
down_revision = "<RESOLVER: alembic heads>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disponibilidad_prof",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("profesional_id", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("cupo_diario", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_disp_prof_profesional", "disponibilidad_prof", ["profesional_id"])

    op.create_table(
        "propuesta_agenda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("profesional_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False, server_default="borrador"),
        sa.Column("generado_por", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_agenda_profesional", "propuesta_agenda", ["profesional_id"])

    op.create_table(
        "cita_propuesta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("propuesta_id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column("fecha_candidata", sa.Date(), nullable=False),
        sa.Column("prioridad", sa.String(25), nullable=False),
        sa.Column("razon", sa.String(120), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False, server_default="propuesta"),
        sa.Column("excluida_por", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cita_prop_propuesta", "cita_propuesta", ["propuesta_id"])
    op.create_index("ix_cita_prop_paciente", "cita_propuesta", ["paciente_id"])


def downgrade() -> None:
    op.drop_index("ix_cita_prop_paciente", table_name="cita_propuesta")
    op.drop_index("ix_cita_prop_propuesta", table_name="cita_propuesta")
    op.drop_table("cita_propuesta")
    op.drop_index("ix_prop_agenda_profesional", table_name="propuesta_agenda")
    op.drop_table("propuesta_agenda")
    op.drop_index("ix_disp_prof_profesional", table_name="disponibilidad_prof")
    op.drop_table("disponibilidad_prof")
```

- [ ] **Step 9: Aplicar la migración y verificar**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: ningún error en los tres comandos; las tablas se crean, se eliminan y se recrean limpiamente.

- [ ] **Step 10: Suite completa verde**

Run: `uv run pytest -v`
Expected: todos los tests (incluyendo los anteriores) pasan.

- [ ] **Step 11: Commit**

```bash
git add backend/app/agendamiento/ \
        backend/app/models/__init__.py \
        backend/migrations/versions/0801_agendamiento_tablas.py \
        backend/tests/agendamiento/
git commit -m "feat(agendamiento): modelos portables DisponibilidadProf, PropuestaAgenda, CitaPropuesta + migración 0801"
```

---

## Task 2: Schemas Pydantic v2 del módulo

**Files:**
- Create: `backend/app/agendamiento/schemas.py`
- Test: `backend/tests/agendamiento/test_agendamiento_schemas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/agendamiento/test_agendamiento_schemas.py`:

```python
import pytest
from datetime import date
from pydantic import ValidationError

from app.agendamiento.enums import DiaSemana, EstadoCita, PrioridadCita, TipoPropuesta
from app.agendamiento.schemas import (
    CitaPropuestaRead,
    DisponibilidadProfCreate,
    DisponibilidadProfRead,
    GenerarPropuestaRequest,
    PropuestaAgendaRead,
    ConfirmarCitasRequest,
)


def test_disponibilidad_prof_create_valida():
    d = DisponibilidadProfCreate(profesional_id=1, dia_semana=DiaSemana.LUNES, cupo_diario=8)
    assert d.dia_semana == DiaSemana.LUNES
    assert d.cupo_diario == 8


def test_disponibilidad_prof_create_rechaza_fin_de_semana():
    with pytest.raises(ValidationError):
        DisponibilidadProfCreate(profesional_id=1, dia_semana=6, cupo_diario=5)


def test_disponibilidad_prof_create_rechaza_cupo_cero():
    with pytest.raises(ValidationError):
        DisponibilidadProfCreate(profesional_id=1, dia_semana=DiaSemana.MARTES, cupo_diario=0)


def test_generar_propuesta_request_diaria():
    req = GenerarPropuestaRequest(
        profesional_id=1,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=date(2026, 7, 7),
    )
    assert req.fecha_fin == date(2026, 7, 7)


def test_generar_propuesta_request_semanal_calcula_fecha_fin():
    req = GenerarPropuestaRequest(
        profesional_id=1,
        tipo=TipoPropuesta.SEMANAL,
        fecha_inicio=date(2026, 7, 7),  # lunes
    )
    assert req.fecha_fin == date(2026, 7, 11)  # viernes de la misma semana


def test_generar_propuesta_request_mensual_calcula_fecha_fin():
    req = GenerarPropuestaRequest(
        profesional_id=1,
        tipo=TipoPropuesta.MENSUAL,
        fecha_inicio=date(2026, 7, 1),
    )
    assert req.fecha_fin == date(2026, 7, 31)


def test_generar_propuesta_request_rechaza_fin_de_semana_como_inicio():
    with pytest.raises(ValidationError):
        GenerarPropuestaRequest(
            profesional_id=1,
            tipo=TipoPropuesta.DIARIA,
            fecha_inicio=date(2026, 7, 11),  # sábado
        )


def test_confirmar_citas_request_requiere_al_menos_una():
    with pytest.raises(ValidationError):
        ConfirmarCitasRequest(cita_ids=[])


def test_propuesta_agenda_read_from_attributes():
    from datetime import datetime, timezone
    from app.agendamiento.models import PropuestaAgenda
    obj = PropuestaAgenda(
        id=1, profesional_id=2, tipo="diaria",
        fecha_inicio=date(2026, 7, 7), fecha_fin=date(2026, 7, 7),
        estado="borrador", generado_por="ana.silva",
        created_at=datetime.now(timezone.utc),
    )
    r = PropuestaAgendaRead.model_validate(obj)
    assert r.id == 1
    assert r.tipo == TipoPropuesta.DIARIA
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/agendamiento/test_agendamiento_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.agendamiento.schemas'`.

- [ ] **Step 3: Crear `backend/app/agendamiento/schemas.py`**

```python
"""Schemas Pydantic v2 para el módulo de agendamiento (EPIC-08).

GenerarPropuestaRequest calcula fecha_fin automáticamente según el tipo de propuesta,
evitando que el cliente deba calcular rangos de fechas.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agendamiento.enums import (
    DiaSemana,
    EstadoCita,
    EstadoPropuesta,
    PrioridadCita,
    TipoPropuesta,
)


# ─── Disponibilidad ────────────────────────────────────────────────────────────

class DisponibilidadProfCreate(BaseModel):
    profesional_id: int
    dia_semana: DiaSemana
    cupo_diario: int = Field(ge=1)

    @field_validator("dia_semana", mode="before")
    @classmethod
    def solo_dias_habiles(cls, v: int | DiaSemana) -> DiaSemana:
        val = int(v)
        if val not in {1, 2, 3, 4, 5}:
            raise ValueError("dia_semana debe ser 1–5 (lunes–viernes). No se permiten fines de semana.")
        return DiaSemana(val)


class DisponibilidadProfRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profesional_id: int
    dia_semana: int
    cupo_diario: int
    activo: bool
    created_at: datetime


# ─── Propuesta ─────────────────────────────────────────────────────────────────

class GenerarPropuestaRequest(BaseModel):
    """Parámetros de generación de una propuesta de agenda.

    fecha_inicio debe ser un día hábil (lun–vie).
    fecha_fin se calcula automáticamente según el tipo:
      - diaria: misma fecha que fecha_inicio
      - semanal: viernes de la semana de fecha_inicio
      - mensual: último día del mes de fecha_inicio
    """

    profesional_id: int
    tipo: TipoPropuesta
    fecha_inicio: date
    fecha_fin: date = Field(default=None)  # type: ignore[assignment]

    @field_validator("fecha_inicio")
    @classmethod
    def debe_ser_dia_habil(cls, v: date) -> date:
        if v.isoweekday() > 5:
            raise ValueError(
                f"fecha_inicio {v} es fin de semana. Solo se aceptan días hábiles (lun–vie)."
            )
        return v

    @model_validator(mode="after")
    def calcular_fecha_fin(self) -> "GenerarPropuestaRequest":
        if self.tipo == TipoPropuesta.DIARIA:
            self.fecha_fin = self.fecha_inicio
        elif self.tipo == TipoPropuesta.SEMANAL:
            # viernes de la semana (isoweekday=5)
            dias_hasta_viernes = 5 - self.fecha_inicio.isoweekday()
            from datetime import timedelta
            self.fecha_fin = self.fecha_inicio + timedelta(days=dias_hasta_viernes)
        elif self.tipo == TipoPropuesta.MENSUAL:
            ultimo = calendar.monthrange(self.fecha_inicio.year, self.fecha_inicio.month)[1]
            self.fecha_fin = date(self.fecha_inicio.year, self.fecha_inicio.month, ultimo)
        return self


class PropuestaAgendaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profesional_id: int
    tipo: TipoPropuesta
    fecha_inicio: date
    fecha_fin: date
    estado: EstadoPropuesta
    generado_por: str
    created_at: datetime


# ─── Cita propuesta ────────────────────────────────────────────────────────────

class CitaPropuestaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    propuesta_id: int
    paciente_id: int
    fecha_candidata: date
    prioridad: PrioridadCita
    razon: str
    estado: EstadoCita
    excluida_por: str | None
    created_at: datetime


class ConfirmarCitasRequest(BaseModel):
    """IDs de CitaPropuesta a confirmar (deben pertenecer a la misma propuesta)."""
    cita_ids: list[int] = Field(min_length=1)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/agendamiento/test_agendamiento_schemas.py -v`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agendamiento/schemas.py \
        backend/tests/agendamiento/test_agendamiento_schemas.py
git commit -m "feat(agendamiento): schemas Pydantic v2 con validación de días hábiles y cálculo de fecha_fin"
```

---

## Task 3: Scheduler — lógica algorítmica pura (núcleo de CEPA-080)

Esta es la pieza más crítica del módulo. Las funciones son **puras** (sin BD, sin I/O): reciben listas de datos en memoria y devuelven listas de candidatos. Se testean exhaustivamente con todos los casos borde de los TC y las RN.

**Files:**
- Create: `backend/app/agendamiento/scheduler.py`
- Test: `backend/tests/agendamiento/test_scheduler.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/agendamiento/test_scheduler.py`:

```python
"""Tests exhaustivos del scheduler puro (sin BD).

Cubre todos los TC-080-XX, CA y RN del spec CEPA-080.
"""

from datetime import date, timedelta

import pytest

from app.agendamiento.enums import PrioridadCita
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ParametrosProf,
    ReposoPaciente,
    proponer_agenda,
    proponer_agenda_semana,
    tiene_reposo_vigente,
)


# ─── Fixtures de datos ──────────────────────────────────────────────────────────

HOY = date(2026, 7, 7)  # martes (isoweekday=2)

DISPONIBILIDAD_COMPLETA = [
    DisponibilidadDia(dia_semana=1, cupo=8),
    DisponibilidadDia(dia_semana=2, cupo=8),
    DisponibilidadDia(dia_semana=3, cupo=8),
    DisponibilidadDia(dia_semana=4, cupo=8),
    DisponibilidadDia(dia_semana=5, cupo=8),
]


def candidato_control_vencido(paciente_id: int, fecha_ctrl: date) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=PrioridadCita.CONTROL_VENCIDO,
        razon=f"control vencido desde {fecha_ctrl}",
        fecha_ctrl=fecha_ctrl,
        reposos=[],
    )


def candidato_control_proximo(paciente_id: int, fecha_ctrl: date) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=PrioridadCita.CONTROL_PROXIMO,
        razon=f"control próximo el {fecha_ctrl}",
        fecha_ctrl=fecha_ctrl,
        reposos=[],
    )


def candidato_receta(paciente_id: int) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=PrioridadCita.SEGUIMIENTO_RECETA,
        razon="seguimiento de receta",
        fecha_ctrl=None,
        reposos=[],
    )


def candidato_con_reposo(
    paciente_id: int, inicio: date, fin: date, prioridad: PrioridadCita
) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=prioridad,
        razon="control próximo",
        fecha_ctrl=HOY,
        reposos=[ReposoPaciente(inicio=inicio, fin=fin)],
    )


# ─── tiene_reposo_vigente ────────────────────────────────────────────────────────

def test_tiene_reposo_vigente_dentro_del_rango():
    """RN-1, RN-5: la evaluación es contra la fecha candidata, no contra hoy."""
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 5)) is True


def test_tiene_reposo_vigente_en_borde_inicio():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 1)) is True


def test_tiene_reposo_vigente_en_borde_fin():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 10)) is True


def test_no_tiene_reposo_vigente_antes():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 6, 30)) is False


def test_no_tiene_reposo_vigente_despues():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 11)) is False


def test_reposos_multiples_alguno_activo():
    reposos = [
        ReposoPaciente(inicio=date(2026, 6, 1), fin=date(2026, 6, 10)),
        ReposoPaciente(inicio=date(2026, 7, 5), fin=date(2026, 7, 15)),
    ]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 8)) is True


def test_sin_reposos_nunca_vigente():
    assert tiene_reposo_vigente([], date(2026, 7, 7)) is False


# ─── TC-080-01: propuesta diaria básica ────────────────────────────────────────

def test_tc_080_01_propuesta_diaria_cinco_candidatos():
    """TC-080-01: 5 candidatos sin reposo, cupo 8 → se proponen los 5."""
    candidatos = [candidato_control_proximo(i, HOY + timedelta(days=1)) for i in range(1, 6)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 5


def test_propuesta_diaria_no_excede_cupo():
    """RN-3: con 10 candidatos y cupo 8, solo 8 se proponen ese día."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 11)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 8


# ─── TC-080-04: exclusión por reposo (RN-1) ────────────────────────────────────

def test_tc_080_04_exclusion_por_reposo_vigente():
    """TC-080-04: paciente con reposo que cubre la fecha candidata → NO se propone."""
    candidatos = [
        candidato_con_reposo(
            1,
            date(2026, 7, 1), date(2026, 7, 10),
            PrioridadCita.CONTROL_PROXIMO,
        )
    ]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 7),
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert len(resultado) == 1
    assert resultado[0].excluida_por is not None
    assert "reposo vigente" in resultado[0].excluida_por
    assert "2026-07-10" in resultado[0].excluida_por


def test_exclusion_reposo_incluye_fecha_fin_en_mensaje():
    """RN-1, CA-4: el mensaje indica hasta cuándo dura el reposo."""
    candidatos = [
        candidato_con_reposo(
            99, date(2026, 7, 1), date(2026, 7, 31),
            PrioridadCita.CONTROL_VENCIDO,
        )
    ]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 15),
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert resultado[0].excluida_por == "reposo vigente hasta 2026-07-31"


# ─── TC-080-07: reposo prevalece sobre receta (RN-1) ───────────────────────────

def test_tc_080_07_reposo_prevalece_sobre_receta():
    """TC-080-07: paciente con receta reciente Y reposo vigente → excluido (RN-1)."""
    candidatos = [
        candidato_con_reposo(
            1, date(2026, 7, 1), date(2026, 7, 10),
            PrioridadCita.SEGUIMIENTO_RECETA,
        )
    ]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 7),
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert resultado[0].excluida_por is not None


# ─── TC-080-05: priorización (RN-2) ────────────────────────────────────────────

def test_tc_080_05_control_vencido_antes_que_proximo():
    """TC-080-05: control vencido tiene mayor prioridad que control próximo."""
    ctrl_vencido = candidato_control_vencido(1, HOY - timedelta(days=3))
    ctrl_proximo = candidato_control_proximo(2, HOY + timedelta(days=2))
    # Cupo 1 para forzar el orden
    disponibilidad_cupo1 = [DisponibilidadDia(dia_semana=d, cupo=1) for d in range(1, 6)]
    resultado = proponer_agenda(
        candidatos=[ctrl_proximo, ctrl_vencido],  # orden inverso intencionado
        fecha=HOY,
        disponibilidad=disponibilidad_cupo1,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 1
    assert propuestos[0].paciente_id == 1  # el vencido, no el próximo


def test_orden_de_prioridad_completo_rn2():
    """RN-2: vencido(1) > próximo(2) > receta(3). A igual prioridad, más antiguo primero."""
    receta = candidato_receta(3)
    proximo = candidato_control_proximo(2, HOY + timedelta(days=1))
    vencido = candidato_control_vencido(1, HOY - timedelta(days=5))
    # Los 3 caben (cupo 8) pero el orden de la lista resultante debe respetar RN-2
    resultado = proponer_agenda(
        candidatos=[receta, proximo, vencido],
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    prioridades = [r.prioridad for r in propuestos]
    assert prioridades == [
        PrioridadCita.CONTROL_VENCIDO,
        PrioridadCita.CONTROL_PROXIMO,
        PrioridadCita.SEGUIMIENTO_RECETA,
    ]


def test_a_igual_prioridad_vencido_antes_se_propone_primero():
    """RN-2: a igual prioridad, más antiguo/vencido primero."""
    mas_antiguo = candidato_control_vencido(1, HOY - timedelta(days=10))
    menos_antiguo = candidato_control_vencido(2, HOY - timedelta(days=2))
    disponibilidad_cupo1 = [DisponibilidadDia(dia_semana=d, cupo=1) for d in range(1, 6)]
    resultado = proponer_agenda(
        candidatos=[menos_antiguo, mas_antiguo],
        fecha=HOY,
        disponibilidad=disponibilidad_cupo1,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert propuestos[0].paciente_id == 1  # el más antiguo


# ─── TC-080-06: candidato por receta (CA-6) ─────────────────────────────────────

def test_tc_080_06_receta_reciente_incluye_candidato():
    """TC-080-06: candidato con receta reciente sin reposo → propuesto con etiqueta."""
    candidatos = [candidato_receta(42)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 1
    assert propuestos[0].prioridad == PrioridadCita.SEGUIMIENTO_RECETA
    assert "seguimiento de receta" in propuestos[0].razon.lower()


# ─── Fin de semana nunca se propone (RN-4) ─────────────────────────────────────

def test_fin_de_semana_devuelve_lista_vacia():
    """RN-4: sabado y domingo → no hay bloques disponibles → lista vacía."""
    candidatos = [candidato_control_proximo(1, date(2026, 7, 11))]
    resultado_sab = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 11),  # sábado
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    resultado_dom = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 12),  # domingo
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert len(resultado_sab) == 0
    assert len(resultado_dom) == 0


# ─── Sin disponibilidad → lista vacía ──────────────────────────────────────────

def test_sin_disponibilidad_para_el_dia_devuelve_vacio():
    """RN-3/4: si el profesional no tiene disponibilidad ese día de semana → vacío."""
    # Solo disponibilidad el lunes (1), pero la fecha es martes (2)
    disponibilidad_solo_lunes = [DisponibilidadDia(dia_semana=1, cupo=8)]
    candidatos = [candidato_control_proximo(1, HOY)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,  # martes
        disponibilidad=disponibilidad_solo_lunes,
    )
    assert len(resultado) == 0


# ─── Sin candidatos → lista vacía ──────────────────────────────────────────────

def test_sin_candidatos_devuelve_lista_vacia():
    resultado = proponer_agenda(
        candidatos=[],
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert len(resultado) == 0


# ─── TC-080-02: propuesta semanal (CA-2) ───────────────────────────────────────

def test_tc_080_02_propuesta_semanal_distribuye_12_candidatos():
    """TC-080-02: 12 candidatos, cupo 8/día, semana lun–vie → distribuidos sin exceder cupo."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 13)]
    lunes = date(2026, 7, 6)  # lunes
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    # 12 candidatos caben en lun+mar (8+4); ningún día supera 8
    propuestos_por_dia: dict[str, int] = {}
    for r in resultado:
        if r.excluida_por is None:
            dia = str(r.fecha_candidata)
            propuestos_por_dia[dia] = propuestos_por_dia.get(dia, 0) + 1
    assert all(v <= 8 for v in propuestos_por_dia.values()), "Ningún día puede superar el cupo"
    total_propuestos = sum(1 for r in resultado if r.excluida_por is None)
    assert total_propuestos == 12


def test_propuesta_semanal_no_incluye_fin_de_semana():
    """RN-4: la semana lun–vie nunca produce citas en sáb/dom."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 5)]
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    for r in resultado:
        assert r.fecha_candidata.isoweekday() <= 5, "No debe haber citas en fin de semana"


# ─── TC-080-08: desbordamiento de cupo se difiere (RN-3) ───────────────────────

def test_tc_080_08_exceso_se_difiere_al_dia_siguiente():
    """TC-080-08: 14 candidatos, cupo 8/día → 8 el día 1, 6 el día 2 (siguiente hábil)."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 15)]
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    # 8 el lunes + 6 el martes
    assert len(propuestos) == 14
    dias = {str(r.fecha_candidata) for r in propuestos}
    assert len(dias) >= 2  # distribuidos en al menos 2 días


# ─── Reposo evaluado fecha a fecha en propuesta semanal (RN-5) ─────────────────

def test_rn5_reposo_evaluado_por_fecha_candidata_no_hoy():
    """RN-5: propuesta semanal excluye el paciente solo en días con reposo, no en todos."""
    # Reposo solo mar–mié (días 2 y 3); debe ser propuesto el lun, jue, vie
    reposo_martes_miercoles = [
        ReposoPaciente(inicio=date(2026, 7, 7), fin=date(2026, 7, 8))
    ]
    candidato = Candidato(
        paciente_id=1,
        prioridad=PrioridadCita.CONTROL_PROXIMO,
        razon="control próximo",
        fecha_ctrl=date(2026, 7, 10),
        reposos=reposo_martes_miercoles,
    )
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=[candidato],
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    # Solo lunes (07-06) debe aparecer como propuesto (el primero disponible sin reposo)
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 1
    assert propuestos[0].fecha_candidata == date(2026, 7, 6)  # lunes
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/agendamiento/test_scheduler.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.agendamiento.scheduler'`.

- [ ] **Step 3: Crear `backend/app/agendamiento/scheduler.py`**

```python
"""Scheduler puro (sin I/O) para EPIC-08 — Agendamiento Inteligente.

Todas las funciones son puras: reciben datos en memoria y devuelven resultados.
Sin sesiones de BD, sin side effects. Esto facilita los tests exhaustivos
y permite que el service llame al scheduler con datos ya cargados.

Reglas de negocio implementadas:
  RN-1: reposo prevalece sobre cualquier criterio de inclusión.
  RN-2: prioridad (1) control_vencido > (2) control_proximo > (3) seguimiento_receta;
         a igual prioridad, más antiguo primero (fecha_ctrl más lejana en el pasado).
  RN-3: nunca se supera el cupo del profesional para el día; el exceso se difiere.
  RN-4: solo días hábiles (isoweekday 1–5); fines de semana retornan lista vacía.
  RN-5: el reposo se evalúa contra la fecha candidata, no contra la fecha de hoy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import NamedTuple

from app.agendamiento.enums import PrioridadCita

# ─── Tipos de datos para el scheduler ──────────────────────────────────────────

class ReposoPaciente(NamedTuple):
    inicio: date
    fin: date


class DisponibilidadDia(NamedTuple):
    dia_semana: int   # ISO weekday 1–5
    cupo: int


@dataclass
class Candidato:
    """Paciente candidato a ser agendado, con su contexto de prioridad."""
    paciente_id: int
    prioridad: PrioridadCita
    razon: str
    fecha_ctrl: date | None        # fecha del control (vencido o próximo); None si es receta
    reposos: list[ReposoPaciente] = field(default_factory=list)


@dataclass
class ResultadoCandidato:
    """Resultado de la evaluación de un candidato para una fecha concreta."""
    paciente_id: int
    fecha_candidata: date
    prioridad: PrioridadCita
    razon: str
    excluida_por: str | None      # None = candidato propuesto; str = motivo de exclusión


# ─── Utilidades ────────────────────────────────────────────────────────────────

_ORDEN_PRIORIDAD: dict[PrioridadCita, int] = {
    PrioridadCita.CONTROL_VENCIDO: 0,
    PrioridadCita.CONTROL_PROXIMO: 1,
    PrioridadCita.SEGUIMIENTO_RECETA: 2,
}

_FECHA_CTRL_MAX = date(9999, 12, 31)  # sentinela para candidatos sin fecha_ctrl


def tiene_reposo_vigente(reposos: list[ReposoPaciente], fecha: date) -> bool:
    """True si la fecha cae dentro de alguno de los períodos de reposo (RN-1, RN-5)."""
    return any(r.inicio <= fecha <= r.fin for r in reposos)


def _cupo_para_dia(disponibilidad: list[DisponibilidadDia], fecha: date) -> int:
    """Retorna el cupo del profesional para la fecha, o 0 si no tiene disponibilidad."""
    dow = fecha.isoweekday()
    for d in disponibilidad:
        if d.dia_semana == dow:
            return d.cupo
    return 0


def _clave_orden(c: Candidato) -> tuple[int, date]:
    """Clave de ordenamiento para RN-2: (nivel_prioridad, fecha_ctrl asc)."""
    nivel = _ORDEN_PRIORIDAD[c.prioridad]
    fecha = c.fecha_ctrl if c.fecha_ctrl is not None else _FECHA_CTRL_MAX
    return (nivel, fecha)


def _reposo_vigente_hasta(reposos: list[ReposoPaciente], fecha: date) -> date | None:
    """Retorna la fecha_fin del reposo que cubre la fecha dada, o None."""
    for r in reposos:
        if r.inicio <= fecha <= r.fin:
            return r.fin
    return None


# ─── Propuesta diaria ──────────────────────────────────────────────────────────

def proponer_agenda(
    candidatos: list[Candidato],
    fecha: date,
    disponibilidad: list[DisponibilidadDia],
) -> list[ResultadoCandidato]:
    """Genera propuesta para un día concreto.

    Retorna lista de ResultadoCandidato. Los candidatos excluidos aparecen en la lista
    con excluida_por != None (para que el llamador pueda reportar el motivo — CA-4).
    Los candidatos propuestos tienen excluida_por == None.

    Si la fecha es fin de semana o el profesional no tiene disponibilidad, devuelve [].
    """
    if fecha.isoweekday() > 5:
        return []

    cupo = _cupo_para_dia(disponibilidad, fecha)
    if cupo == 0:
        return []

    candidatos_ordenados = sorted(candidatos, key=_clave_orden)
    resultado: list[ResultadoCandidato] = []
    propuestos = 0

    for c in candidatos_ordenados:
        fin_reposo = _reposo_vigente_hasta(c.reposos, fecha)
        if fin_reposo is not None:
            resultado.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=fecha,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=f"reposo vigente hasta {fin_reposo.isoformat()}",
            ))
            continue

        if propuestos >= cupo:
            # Cupo agotado: el candidato se omite de este día
            # (será recogido por proponer_agenda_semana para el día siguiente)
            continue

        resultado.append(ResultadoCandidato(
            paciente_id=c.paciente_id,
            fecha_candidata=fecha,
            prioridad=c.prioridad,
            razon=c.razon,
            excluida_por=None,
        ))
        propuestos += 1

    return resultado


# ─── Propuesta semanal/mensual ─────────────────────────────────────────────────

def _dias_habiles_en_rango(inicio: date, fin: date) -> list[date]:
    """Retorna la lista de días hábiles (lun–vie) entre inicio y fin, inclusive."""
    dias: list[date] = []
    actual = inicio
    while actual <= fin:
        if actual.isoweekday() <= 5:
            dias.append(actual)
        actual += timedelta(days=1)
    return dias


def proponer_agenda_semana(
    candidatos: list[Candidato],
    semana_inicio: date,
    semana_fin: date,
    disponibilidad: list[DisponibilidadDia],
) -> list[ResultadoCandidato]:
    """Distribuye candidatos a lo largo de los días hábiles del rango (semanal o mensual).

    Algoritmo:
    1. Ordenar candidatos por RN-2 (prioridad + antigüedad).
    2. Para cada candidato, asignar el primer día hábil donde:
       a. El profesional tiene disponibilidad.
       b. El paciente no tiene reposo vigente ese día (RN-5).
       c. El cupo de ese día no está agotado (RN-3).
    3. Si el candidato tiene reposo en todos los días del rango, queda excluido
       con el motivo del primer reposo encontrado.
    4. El exceso de candidatos que no caben en ningún día del rango queda sin proponer
       (no se incluyen en el resultado — se diferirán a la siguiente semana/mes si el
       caller llama de nuevo con el rango extendido).

    Retorna la lista plana de ResultadoCandidato de todos los días del rango,
    incluyendo los excluidos por reposo.
    """
    dias = _dias_habiles_en_rango(semana_inicio, semana_fin)
    if not dias:
        return []

    # Cupo disponible por día
    cupo_restante: dict[date, int] = {}
    for d in dias:
        c = _cupo_para_dia(disponibilidad, d)
        if c > 0:
            cupo_restante[d] = c

    candidatos_ordenados = sorted(candidatos, key=_clave_orden)
    resultado: list[ResultadoCandidato] = []

    for c in candidatos_ordenados:
        asignado = False
        primer_reposo_fin: date | None = None

        for d in dias:
            if d not in cupo_restante:
                continue  # sin disponibilidad ese día

            fin_reposo = _reposo_vigente_hasta(c.reposos, d)
            if fin_reposo is not None:
                if primer_reposo_fin is None:
                    primer_reposo_fin = fin_reposo
                continue  # buscar otro día

            # Disponibilidad + sin reposo + cupo
            resultado.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=d,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=None,
            ))
            cupo_restante[d] -= 1
            if cupo_restante[d] == 0:
                del cupo_restante[d]
            asignado = True
            break

        if not asignado and primer_reposo_fin is not None:
            # Excluido por reposo en todos los días del rango donde había disponibilidad
            primer_dia_con_disp = next((d for d in dias if _cupo_para_dia(disponibilidad, d) > 0), dias[0])
            resultado.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=primer_dia_con_disp,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=f"reposo vigente hasta {primer_reposo_fin.isoformat()}",
            ))

    return resultado
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/agendamiento/test_scheduler.py -v`
Expected: todos los tests pasan (≥22 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/agendamiento/scheduler.py \
        backend/tests/agendamiento/test_scheduler.py
git commit -m "feat(agendamiento): scheduler puro con exclusión RN-1, priorización RN-2, cupo RN-3, días hábiles RN-4/5"
```

---

## Task 4: Servicio de agendamiento (orquesta BD + scheduler)

**Files:**
- Create: `backend/app/agendamiento/service.py`
- Test: `backend/tests/agendamiento/test_agendamiento_service.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/agendamiento/test_agendamiento_service.py`:

```python
"""Tests de integración del servicio de agendamiento (con BD real via db_session)."""

from datetime import date, timedelta

import pytest

from app.agendamiento.enums import EstadoCita, EstadoPropuesta, PrioridadCita, TipoPropuesta
from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda
from app.agendamiento.schemas import GenerarPropuestaRequest
from app.agendamiento.service import (
    confirmar_citas,
    crear_disponibilidad,
    generar_propuesta,
    obtener_propuesta,
)

HOY = date(2026, 7, 7)  # martes
PROF_ID = 101
PACIENTE_ID = 201


def _insertar_disponibilidad_completa(db):
    for dia in range(1, 6):
        db.add(DisponibilidadProf(
            profesional_id=PROF_ID, dia_semana=dia, cupo_diario=8, activo=True,
        ))
    db.flush()


def _insertar_control_proximo(db, paciente_id: int, fecha: date):
    """Simula un registro en tabla 'control' sin FK real (EPIC-06 no disponible en tests)."""
    from sqlalchemy import text
    db.execute(text(
        "INSERT INTO control (paciente_id, profesional_id, fecha_prox_control) "
        "VALUES (:pid, :prof, :fecha)"
    ), {"pid": paciente_id, "prof": PROF_ID, "fecha": fecha})
    db.flush()


def test_crear_disponibilidad(db_session):
    dp = crear_disponibilidad(
        db=db_session,
        profesional_id=PROF_ID,
        dia_semana=1,
        cupo_diario=6,
        actor="admin_test",
    )
    assert dp.id is not None
    assert dp.cupo_diario == 6
    assert dp.activo is True


def test_generar_propuesta_diaria_sin_candidatos(db_session):
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(
        db=db_session,
        req=req,
        actor="admin_test",
    )
    assert propuesta.id is not None
    assert propuesta.tipo == TipoPropuesta.DIARIA.value
    assert propuesta.estado == EstadoPropuesta.BORRADOR.value
    # Sin candidatos, la propuesta queda vacía
    citas = db_session.query(CitaPropuesta).filter_by(propuesta_id=propuesta.id).all()
    assert len(citas) == 0


def test_generar_propuesta_diaria_con_candidatos(db_session):
    """Integración: genera propuesta con candidatos de control próximo."""
    _insertar_disponibilidad_completa(db_session)
    # Pre-poblar control próximo
    _insertar_control_proximo(db_session, PACIENTE_ID, HOY + timedelta(days=2))

    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")
    citas = db_session.query(CitaPropuesta).filter_by(propuesta_id=propuesta.id).all()
    assert len(citas) >= 1
    assert citas[0].estado == EstadoCita.PROPUESTA.value


def test_confirmar_citas_cambia_estado(db_session):
    """CA-7: confirmar citas propuestas las marca como confirmadas."""
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")
    # Insertar manualmente una cita propuesta para confirmar
    cita = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=PACIENTE_ID,
        fecha_candidata=HOY,
        prioridad=PrioridadCita.CONTROL_PROXIMO.value,
        razon="control próximo",
        estado=EstadoCita.PROPUESTA.value,
    )
    db_session.add(cita)
    db_session.flush()

    confirmadas = confirmar_citas(
        db=db_session,
        propuesta_id=propuesta.id,
        cita_ids=[cita.id],
        actor="admin_test",
    )
    assert len(confirmadas) == 1
    assert confirmadas[0].estado == EstadoCita.CONFIRMADA.value


def test_confirmar_citas_estado_propuesta_pasa_a_confirmada(db_session):
    """CA-7: cuando al menos una cita se confirma, la propuesta cambia a 'confirmada'."""
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")
    cita = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=PACIENTE_ID,
        fecha_candidata=HOY,
        prioridad=PrioridadCita.CONTROL_PROXIMO.value,
        razon="control próximo",
        estado=EstadoCita.PROPUESTA.value,
    )
    db_session.add(cita)
    db_session.flush()

    confirmar_citas(db=db_session, propuesta_id=propuesta.id, cita_ids=[cita.id], actor="admin_test")
    db_session.refresh(propuesta)
    assert propuesta.estado == EstadoPropuesta.CONFIRMADA.value


def test_obtener_propuesta_inexistente_retorna_none(db_session):
    assert obtener_propuesta(db=db_session, propuesta_id=99999) is None
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/agendamiento/test_agendamiento_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.agendamiento.service'`.

- [ ] **Step 3: Crear `backend/app/agendamiento/service.py`**

```python
"""Servicio de agendamiento: orquesta la carga de BD y llama al scheduler puro.

La lógica algorítmica (exclusión por reposo, priorización, cupo) vive en scheduler.py.
Este módulo solo sabe de modelos SQLAlchemy y del patrón de repositorio.

Dependencias de otras épicas (EPIC-01, EPIC-02, EPIC-06, EPIC-07) se asumen en main:
  - tabla 'control'  (fecha_prox_control, paciente_id, profesional_id)
  - tabla 'licencia' (reposo_inicio, reposo_fin, paciente_id)
  - tabla 'receta'   (fecha_emision, fecha_revision, requiere_seguimiento, gestionada, paciente_id)
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento.enums import EstadoCita, EstadoPropuesta, PrioridadCita
from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
    proponer_agenda,
    proponer_agenda_semana,
)
from app.agendamiento.schemas import GenerarPropuestaRequest
from app.audit.service import record_audit

# ─── Ventana de seguimiento de receta (parametrizable — RN-6) ──────────────────
VENTANA_SEGUIMIENTO_RECETA_DIAS: int = 30


# ─── Disponibilidad ────────────────────────────────────────────────────────────

def crear_disponibilidad(
    db: Session,
    profesional_id: int,
    dia_semana: int,
    cupo_diario: int,
    actor: str,
) -> DisponibilidadProf:
    """Crea o reemplaza la disponibilidad diaria de un profesional."""
    dp = DisponibilidadProf(
        profesional_id=profesional_id,
        dia_semana=dia_semana,
        cupo_diario=cupo_diario,
        activo=True,
    )
    db.add(dp)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="CREATE",
        entity="disponibilidad_prof",
        entity_id=str(dp.id),
    )
    return dp


def _cargar_disponibilidad(db: Session, profesional_id: int) -> list[DisponibilidadDia]:
    rows = db.scalars(
        select(DisponibilidadProf).where(
            DisponibilidadProf.profesional_id == profesional_id,
            DisponibilidadProf.activo.is_(True),
        )
    ).all()
    return [DisponibilidadDia(dia_semana=r.dia_semana, cupo=r.cupo_diario) for r in rows]


# ─── Carga de candidatos desde BD ───────────────────────────────────────────────

def _cargar_reposos(db: Session, paciente_id: int, fecha_ini: date, fecha_fin: date) -> list[ReposoPaciente]:
    """Carga los reposos del paciente que se solapan con el rango de fechas."""
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT reposo_inicio, reposo_fin FROM licencia "
        "WHERE paciente_id = :pid "
        "  AND reposo_inicio <= :fin AND reposo_fin >= :ini"
    ), {"pid": paciente_id, "ini": fecha_ini, "fin": fecha_fin}).fetchall()
    return [ReposoPaciente(inicio=r[0], fin=r[1]) for r in rows]


def _cargar_candidatos(db: Session, profesional_id: int, fecha_ini: date, fecha_fin: date) -> list[Candidato]:
    """Construye la lista de candidatos a partir de controles y recetas.

    Orden de carga:
    1. Controles vencidos (fecha_prox_control < hoy) para el profesional.
    2. Controles próximos (hoy ≤ fecha_prox_control ≤ fecha_fin + 7 días) para el profesional.
    3. Recetas recientes con seguimiento pendiente de cualquier paciente del profesional.

    Las colisiones (mismo paciente en varias categorías) se resuelven conservando la
    prioridad más alta (control_vencido > control_proximo > seguimiento_receta).
    """
    from sqlalchemy import text
    hoy = date.today()

    vistos: dict[int, Candidato] = {}

    # 1. Controles vencidos
    ctrl_vencidos = db.execute(text(
        "SELECT paciente_id, fecha_prox_control FROM control "
        "WHERE profesional_id = :prof AND fecha_prox_control < :hoy"
    ), {"prof": profesional_id, "hoy": hoy}).fetchall()

    for row in ctrl_vencidos:
        pid, fecha_ctrl = row[0], row[1]
        reposos = _cargar_reposos(db, pid, fecha_ini, fecha_fin)
        vistos[pid] = Candidato(
            paciente_id=pid,
            prioridad=PrioridadCita.CONTROL_VENCIDO,
            razon=f"control vencido desde {fecha_ctrl}",
            fecha_ctrl=fecha_ctrl,
            reposos=reposos,
        )

    # 2. Controles próximos
    horizonte = fecha_fin + timedelta(days=7)
    ctrl_proximos = db.execute(text(
        "SELECT paciente_id, fecha_prox_control FROM control "
        "WHERE profesional_id = :prof AND fecha_prox_control >= :hoy "
        "  AND fecha_prox_control <= :horizonte"
    ), {"prof": profesional_id, "hoy": hoy, "horizonte": horizonte}).fetchall()

    for row in ctrl_proximos:
        pid, fecha_ctrl = row[0], row[1]
        if pid not in vistos:
            reposos = _cargar_reposos(db, pid, fecha_ini, fecha_fin)
            vistos[pid] = Candidato(
                paciente_id=pid,
                prioridad=PrioridadCita.CONTROL_PROXIMO,
                razon=f"control próximo el {fecha_ctrl}",
                fecha_ctrl=fecha_ctrl,
                reposos=reposos,
            )

    # 3. Recetas recientes con seguimiento pendiente (RN-6)
    limite_receta = hoy - timedelta(days=VENTANA_SEGUIMIENTO_RECETA_DIAS)
    recetas = db.execute(text(
        "SELECT DISTINCT r.paciente_id FROM receta r "
        "JOIN control c ON c.paciente_id = r.paciente_id "
        "WHERE c.profesional_id = :prof "
        "  AND r.requiere_seguimiento = TRUE "
        "  AND r.gestionada = FALSE "
        "  AND (r.fecha_revision >= :hoy OR r.fecha_emision >= :limite)"
    ), {"prof": profesional_id, "hoy": hoy, "limite": limite_receta}).fetchall()

    for row in recetas:
        pid = row[0]
        if pid not in vistos:
            reposos = _cargar_reposos(db, pid, fecha_ini, fecha_fin)
            vistos[pid] = Candidato(
                paciente_id=pid,
                prioridad=PrioridadCita.SEGUIMIENTO_RECETA,
                razon="seguimiento de receta",
                fecha_ctrl=None,
                reposos=reposos,
            )

    return list(vistos.values())


# ─── Generación de propuesta ────────────────────────────────────────────────────

def generar_propuesta(
    db: Session,
    req: GenerarPropuestaRequest,
    actor: str,
) -> PropuestaAgenda:
    """Genera y persiste una PropuestaAgenda con sus CitaPropuesta.

    Registra auditoría (RN-9). No hace commit — el caller (router) es responsable.
    """
    disponibilidad = _cargar_disponibilidad(db, req.profesional_id)
    candidatos = _cargar_candidatos(db, req.profesional_id, req.fecha_inicio, req.fecha_fin)

    propuesta = PropuestaAgenda(
        profesional_id=req.profesional_id,
        tipo=req.tipo.value,
        fecha_inicio=req.fecha_inicio,
        fecha_fin=req.fecha_fin,
        estado=EstadoPropuesta.BORRADOR.value,
        generado_por=actor,
    )
    db.add(propuesta)
    db.flush()

    if req.tipo.value == "diaria":
        resultados = proponer_agenda(
            candidatos=candidatos,
            fecha=req.fecha_inicio,
            disponibilidad=disponibilidad,
        )
    else:
        resultados = proponer_agenda_semana(
            candidatos=candidatos,
            semana_inicio=req.fecha_inicio,
            semana_fin=req.fecha_fin,
            disponibilidad=disponibilidad,
        )

    for r in resultados:
        cita = CitaPropuesta(
            propuesta_id=propuesta.id,
            paciente_id=r.paciente_id,
            fecha_candidata=r.fecha_candidata,
            prioridad=r.prioridad.value,
            razon=r.razon,
            estado=EstadoCita.PROPUESTA.value,
            excluida_por=r.excluida_por,
        )
        db.add(cita)

    record_audit(
        db,
        actor=actor,
        action="CREATE",
        entity="propuesta_agenda",
        entity_id=str(propuesta.id),
    )
    db.flush()
    return propuesta


# ─── Consulta ──────────────────────────────────────────────────────────────────

def obtener_propuesta(db: Session, propuesta_id: int) -> PropuestaAgenda | None:
    return db.get(PropuestaAgenda, propuesta_id)


# ─── Confirmación de citas (CA-7, RN-8, RN-9) ─────────────────────────────────

def confirmar_citas(
    db: Session,
    propuesta_id: int,
    cita_ids: list[int],
    actor: str,
) -> list[CitaPropuesta]:
    """Confirma las citas indicadas y actualiza el estado de la propuesta.

    Las citas confirmadas cuentan como 'citas agendadas' en el denominador de adherencia
    (RN-8). El cambio de estado se graba en auditoría (RN-9).
    """
    propuesta = db.get(PropuestaAgenda, propuesta_id)
    if propuesta is None:
        return []

    confirmadas: list[CitaPropuesta] = []
    for cita_id in cita_ids:
        cita = db.get(CitaPropuesta, cita_id)
        if cita is None or cita.propuesta_id != propuesta_id:
            continue
        if cita.estado == EstadoCita.PROPUESTA.value:
            cita.estado = EstadoCita.CONFIRMADA.value
            confirmadas.append(cita)

    if confirmadas:
        propuesta.estado = EstadoPropuesta.CONFIRMADA.value
        record_audit(
            db,
            actor=actor,
            action="UPDATE",
            entity="propuesta_agenda",
            entity_id=str(propuesta_id),
        )

    db.flush()
    return confirmadas
```

- [ ] **Step 4: Correr el test y verificar que pasa**

> Nota: los tests que invocan `_insertar_control_proximo` requieren que la tabla `control` exista (EPIC-06). Si EPIC-06 no está en `main` aún, esos tests específicos fallarán con un error de tabla inexistente — están marcados con esa dependencia. Los demás tests (crear disponibilidad, obtener propuesta, confirmar citas) pasan sin esa dependencia.

Run: `uv run pytest tests/agendamiento/test_agendamiento_service.py -v`
Expected: al menos `test_crear_disponibilidad`, `test_generar_propuesta_diaria_sin_candidatos`, `test_confirmar_citas_cambia_estado`, `test_confirmar_citas_estado_propuesta_pasa_a_confirmada`, `test_obtener_propuesta_inexistente_retorna_none` en verde. Los tests que usan `_insertar_control_proximo` pasan una vez que EPIC-06 esté en `main`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agendamiento/service.py \
        backend/tests/agendamiento/test_agendamiento_service.py
git commit -m "feat(agendamiento): servicio de agendamiento — generación, confirmación y auditoría (RN-8, RN-9)"
```

---

## Task 5: Router HTTP `/api/v1/propuestas-agenda` y permisos RBAC

**Files:**
- Create: `backend/app/agendamiento/router.py`
- Modify: `backend/app/main.py` (registrar el router)
- Test: `backend/tests/agendamiento/test_agendamiento_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/agendamiento/test_agendamiento_api.py`:

```python
"""Tests de API para el módulo de agendamiento.

Cubre CA-8 (permisos por rol), CA-1 (propuesta diaria), CA-7 (confirmación).
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient


HOY_HABIL = "2026-07-07"  # martes


def test_generar_propuesta_requiere_autenticacion(client: TestClient):
    """CA-8: sin token → 401."""
    resp = client.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 401


def test_generar_propuesta_auditor_denegado(as_auditor: TestClient):
    """CA-8: Auditor no puede generar propuesta → 403."""
    resp = as_auditor.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 403


def test_generar_propuesta_admin_permitido(as_admin: TestClient):
    """CA-8 / CA-1: Administrativo puede generar propuesta → 201."""
    resp = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 1, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipo"] == "diaria"
    assert body["estado"] == "borrador"
    assert "id" in body


def test_generar_propuesta_coordinacion_permitido(as_coordinacion: TestClient):
    """CA-8: Coordinacion puede generar propuesta → 201."""
    resp = as_coordinacion.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 2, "tipo": "semanal", "fecha_inicio": HOY_HABIL
    })
    assert resp.status_code == 201


def test_listar_propuestas_auditor_puede_leer(as_auditor: TestClient):
    """CA-8: Auditor puede listar propuestas (solo lectura) → 200."""
    resp = as_auditor.get("/api/v1/propuestas-agenda")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_obtener_propuesta_por_id_admin(as_admin: TestClient):
    """Crear y luego recuperar por ID."""
    create = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 3, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    assert create.status_code == 201
    pid = create.json()["id"]

    get_resp = as_admin.get(f"/api/v1/propuestas-agenda/{pid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == pid


def test_obtener_propuesta_inexistente_404(as_admin: TestClient):
    resp = as_admin.get("/api/v1/propuestas-agenda/999999")
    assert resp.status_code == 404


def test_confirmar_citas_auditor_denegado(as_admin: TestClient, as_auditor: TestClient):
    """CA-8: Auditor no puede confirmar citas → 403."""
    create = as_admin.post("/api/v1/propuestas-agenda", json={
        "profesional_id": 4, "tipo": "diaria", "fecha_inicio": HOY_HABIL
    })
    pid = create.json()["id"]
    resp = as_auditor.post(f"/api/v1/propuestas-agenda/{pid}/confirmar", json={"cita_ids": [1]})
    assert resp.status_code == 403


def test_confirmar_citas_propuesta_inexistente_404(as_admin: TestClient):
    resp = as_admin.post("/api/v1/propuestas-agenda/999999/confirmar", json={"cita_ids": [1]})
    assert resp.status_code == 404


def test_crear_disponibilidad_admin(as_admin: TestClient):
    """El Administrativo puede crear disponibilidad de profesional."""
    resp = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 10, "dia_semana": 1, "cupo_diario": 6
    })
    assert resp.status_code == 201
    assert resp.json()["cupo_diario"] == 6


def test_crear_disponibilidad_fin_de_semana_422(as_admin: TestClient):
    """dia_semana=6 (sábado) → error de validación 422."""
    resp = as_admin.post("/api/v1/disponibilidad-profesional", json={
        "profesional_id": 10, "dia_semana": 6, "cupo_diario": 5
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/agendamiento/test_agendamiento_api.py -v`
Expected: FAIL con `404 Not Found` (las rutas no existen todavía).

- [ ] **Step 3: Crear `backend/app/agendamiento/router.py`**

```python
"""Router de agendamiento — EPIC-08.

Endpoints:
  POST   /api/v1/disponibilidad-profesional          Administrativo | Coordinacion
  GET    /api/v1/disponibilidad-profesional/{prof_id} Todos los roles
  POST   /api/v1/propuestas-agenda                   Administrativo | Coordinacion
  GET    /api/v1/propuestas-agenda                   Todos los roles
  GET    /api/v1/propuestas-agenda/{id}              Todos los roles
  POST   /api/v1/propuestas-agenda/{id}/confirmar    Administrativo | Coordinacion
  GET    /api/v1/propuestas-agenda/{id}/citas        Todos los roles
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda
from app.agendamiento.schemas import (
    CitaPropuestaRead,
    ConfirmarCitasRequest,
    DisponibilidadProfCreate,
    DisponibilidadProfRead,
    GenerarPropuestaRequest,
    PropuestaAgendaRead,
)
from app.agendamiento.service import (
    confirmar_citas,
    crear_disponibilidad,
    generar_propuesta,
    obtener_propuesta,
)
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db

router = APIRouter(tags=["agendamiento"])

_writer = Depends(require_role("Administrativo", "Coordinacion"))
_reader = Depends(require_role("Administrativo", "Coordinacion", "Auditor"))


# ─── Disponibilidad ────────────────────────────────────────────────────────────

@router.post(
    "/api/v1/disponibilidad-profesional",
    response_model=DisponibilidadProfRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_writer],
)
def crear_disponibilidad_endpoint(
    payload: DisponibilidadProfCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DisponibilidadProf:
    return crear_disponibilidad(
        db=db,
        profesional_id=payload.profesional_id,
        dia_semana=payload.dia_semana.value,
        cupo_diario=payload.cupo_diario,
        actor=current_user.username,
    )


@router.get(
    "/api/v1/disponibilidad-profesional/{profesional_id}",
    response_model=list[DisponibilidadProfRead],
    dependencies=[_reader],
)
def listar_disponibilidad(
    profesional_id: int,
    db: Session = Depends(get_db),
) -> list[DisponibilidadProf]:
    return list(db.scalars(
        select(DisponibilidadProf)
        .where(DisponibilidadProf.profesional_id == profesional_id,
               DisponibilidadProf.activo.is_(True))
        .order_by(DisponibilidadProf.dia_semana)
    ))


# ─── Propuestas ────────────────────────────────────────────────────────────────

@router.post(
    "/api/v1/propuestas-agenda",
    response_model=PropuestaAgendaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_writer],
)
def crear_propuesta(
    payload: GenerarPropuestaRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PropuestaAgenda:
    propuesta = generar_propuesta(db=db, req=payload, actor=current_user.username)
    db.commit()
    db.refresh(propuesta)
    return propuesta


@router.get(
    "/api/v1/propuestas-agenda",
    response_model=list[PropuestaAgendaRead],
    dependencies=[_reader],
)
def listar_propuestas(
    profesional_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[PropuestaAgenda]:
    q = select(PropuestaAgenda).order_by(PropuestaAgenda.created_at.desc())
    if profesional_id is not None:
        q = q.where(PropuestaAgenda.profesional_id == profesional_id)
    return list(db.scalars(q))


@router.get(
    "/api/v1/propuestas-agenda/{propuesta_id}",
    response_model=PropuestaAgendaRead,
    dependencies=[_reader],
)
def obtener_propuesta_endpoint(
    propuesta_id: int,
    db: Session = Depends(get_db),
) -> PropuestaAgenda:
    propuesta = obtener_propuesta(db=db, propuesta_id=propuesta_id)
    if propuesta is None:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    return propuesta


@router.get(
    "/api/v1/propuestas-agenda/{propuesta_id}/citas",
    response_model=list[CitaPropuestaRead],
    dependencies=[_reader],
)
def listar_citas_de_propuesta(
    propuesta_id: int,
    db: Session = Depends(get_db),
) -> list[CitaPropuesta]:
    return list(db.scalars(
        select(CitaPropuesta)
        .where(CitaPropuesta.propuesta_id == propuesta_id)
        .order_by(CitaPropuesta.fecha_candidata, CitaPropuesta.prioridad)
    ))


@router.post(
    "/api/v1/propuestas-agenda/{propuesta_id}/confirmar",
    response_model=list[CitaPropuestaRead],
    dependencies=[_writer],
)
def confirmar_citas_endpoint(
    propuesta_id: int,
    payload: ConfirmarCitasRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CitaPropuesta]:
    propuesta = obtener_propuesta(db=db, propuesta_id=propuesta_id)
    if propuesta is None:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    confirmadas = confirmar_citas(
        db=db,
        propuesta_id=propuesta_id,
        cita_ids=payload.cita_ids,
        actor=current_user.username,
    )
    db.commit()
    return confirmadas
```

- [ ] **Step 4: Registrar el router en `backend/app/main.py`**

Agregar la importación y el `include_router`. El archivo actual termina con:

```python
from app.routers import audit_log
# ... (otros routers ya registrados)
```

Agregar al final de las importaciones:

```python
from app.agendamiento import router as agendamiento_router
```

Y en el cuerpo de la app, después de los includes existentes:

```python
app.include_router(agendamiento_router.router)
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/agendamiento/test_agendamiento_api.py -v`
Expected: todos los tests de API pasan.

- [ ] **Step 6: Suite completa verde**

Run: `uv run pytest -v`
Expected: toda la suite pasa (Fundación + EPIC-00 + EPIC-01 anteriores + los nuevos).

- [ ] **Step 7: Commit**

```bash
git add backend/app/agendamiento/router.py \
        backend/app/main.py \
        backend/tests/agendamiento/test_agendamiento_api.py
git commit -m "feat(agendamiento): router HTTP con RBAC — disponibilidad, propuesta y confirmación (CA-8)"
```

---

## Task 6: Prueba de rendimiento (TC-080-10) — propuesta mensual con volumen objetivo

**Files:**
- Test: `backend/tests/agendamiento/test_agendamiento_rendimiento.py`

> Este test corre con `pytest -m rendimiento` (marcador personalizado). No forma parte del CI obligatorio pero sí del DoD.

- [ ] **Step 1: Agregar el marcador en `backend/pyproject.toml`**

Agregar bajo `[tool.pytest.ini_options]`:

```toml
markers = [
    "rendimiento: pruebas de rendimiento con volúmenes reales (excluidas del CI rápido)",
]
```

- [ ] **Step 2: Escribir el test de rendimiento**

Crear `backend/tests/agendamiento/test_agendamiento_rendimiento.py`:

```python
"""TC-080-10: Propuesta mensual con volumen objetivo (< 2 s, PRD §9).

Requiere dataset poblado. Correr con:
    uv run pytest tests/agendamiento/test_agendamiento_rendimiento.py -m rendimiento -v
"""

import time
from datetime import date, timedelta

import pytest

from app.agendamiento.enums import PrioridadCita
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
    proponer_agenda_semana,
)


pytestmark = pytest.mark.rendimiento

LIMITE_SEGUNDOS = 2.0


def _generar_candidatos_volumen(n: int) -> list[Candidato]:
    """Genera n candidatos con reposos distribuidos aleatoriamente."""
    import random
    random.seed(42)
    hoy = date(2026, 7, 1)
    candidatos = []
    prioridades = list(PrioridadCita)
    for i in range(1, n + 1):
        prioridad = prioridades[i % len(prioridades)]
        reposos = []
        if random.random() < 0.15:  # ~15% tienen reposo
            ini = hoy + timedelta(days=random.randint(0, 15))
            fin = ini + timedelta(days=random.randint(3, 14))
            reposos = [ReposoPaciente(inicio=ini, fin=fin)]
        candidatos.append(Candidato(
            paciente_id=i,
            prioridad=prioridad,
            razon=f"razon_{i}",
            fecha_ctrl=hoy - timedelta(days=i % 30),
            reposos=reposos,
        ))
    return candidatos


def test_tc_080_10_propuesta_mensual_menos_de_2s():
    """TC-080-10: 800 candidatos (volumen objetivo), mes completo, 25 prof → < 2 s."""
    candidatos = _generar_candidatos_volumen(800)
    disponibilidad = [DisponibilidadDia(dia_semana=d, cupo=8) for d in range(1, 6)]
    mes_inicio = date(2026, 7, 1)
    mes_fin = date(2026, 7, 31)

    inicio = time.perf_counter()
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=mes_inicio,
        semana_fin=mes_fin,
        disponibilidad=disponibilidad,
    )
    elapsed = time.perf_counter() - inicio

    assert elapsed < LIMITE_SEGUNDOS, (
        f"La propuesta mensual tardó {elapsed:.3f} s (límite {LIMITE_SEGUNDOS} s). "
        "Revisar complejidad del scheduler."
    )
    assert len(resultado) > 0


def test_tc_080_10_reposo_evaluado_dia_a_dia_en_volumen():
    """RN-5 con volumen: la exclusión por reposo funciona correctamente a escala."""
    # Todos los candidatos tienen reposo en la primera semana del mes
    reposo_semana1 = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 5))]
    candidatos = [
        Candidato(
            paciente_id=i,
            prioridad=PrioridadCita.CONTROL_PROXIMO,
            razon=f"ctrl {i}",
            fecha_ctrl=date(2026, 7, 10),
            reposos=reposo_semana1,
        )
        for i in range(1, 101)
    ]
    disponibilidad = [DisponibilidadDia(dia_semana=d, cupo=8) for d in range(1, 6)]
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=date(2026, 7, 1),
        semana_fin=date(2026, 7, 31),
        disponibilidad=disponibilidad,
    )
    # Ningún propuesto debe tener fecha_candidata en la semana 1 (01–05 julio)
    for r in resultado:
        if r.excluida_por is None:
            assert r.fecha_candidata >= date(2026, 7, 6), (
                f"Cita propuesta en día con reposo: {r.fecha_candidata}"
            )
```

- [ ] **Step 3: Correr el test de rendimiento**

Run: `uv run pytest tests/agendamiento/test_agendamiento_rendimiento.py -m rendimiento -v`
Expected: `2 passed`; el tiempo reportado para la propuesta mensual con 800 candidatos debe estar **muy por debajo de 2 s** (el scheduler es O(n·d) donde n=candidatos, d=días hábiles del mes ~23).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agendamiento/test_agendamiento_rendimiento.py \
        backend/pyproject.toml
git commit -m "test(agendamiento): prueba de rendimiento TC-080-10 — propuesta mensual < 2 s"
```

---

## Task 7: Verificación final integral + lint

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa**

Run: `uv run pytest -v`
Expected: toda la suite en verde (incluyendo tasks 1–6 de esta épica).

- [ ] **Step 2: Lint**

Run: `uv run ruff check .`
Expected: sin errores.

- [ ] **Step 3: Smoke de migración desde cero**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: `base` → cero tablas; `head` → todas las tablas del sistema incluyendo las tres de agendamiento.

- [ ] **Step 4: Verificación de OpenAPI**

Run: `uv run uvicorn app.main:app` y en otra terminal:
```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
spec = json.load(sys.stdin)
rutas = list(spec['paths'].keys())
esperadas = [
    '/api/v1/disponibilidad-profesional',
    '/api/v1/propuestas-agenda',
]
for r in esperadas:
    assert r in rutas, f'Ruta faltante en OpenAPI: {r}'
print('OpenAPI OK —', len(rutas), 'rutas documentadas')
"
```
Expected: `OpenAPI OK` sin assertions fallidas. Detener con Ctrl-C.

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "feat(agendamiento): EPIC-08 completo — scheduler puro, servicio, API RBAC, migración 0801, rendimiento TC-080-10" \
  || echo "nada que commitear"
```

---

## Cobertura — CEPA-080 ↔ Tasks

| Historia | Criterios / Reglas | Task(s) |
|----------|--------------------|---------|
| CEPA-080 CA-1 — propuesta diaria | TC-080-01; `proponer_agenda`; cupo 8/día | Task 3, Task 4, Task 5 |
| CEPA-080 CA-2 — propuesta semanal | TC-080-02; `proponer_agenda_semana`; distribución lun–vie | Task 3, Task 4, Task 5 |
| CEPA-080 CA-3 — propuesta mensual | TC-080-03; rango mensual vía `proponer_agenda_semana` | Task 3, Task 5, Task 6 |
| CEPA-080 CA-4 — exclusión por reposo | TC-080-04, TC-080-07; RN-1, RN-5; mensaje "reposo vigente hasta …" | Task 3 |
| CEPA-080 CA-5 — priorización control vencido/próximo | TC-080-05; RN-2; `_clave_orden` | Task 3 |
| CEPA-080 CA-6 — inclusión por receta | TC-080-06; RN-6; `SEGUIMIENTO_RECETA`; carga en service | Task 3, Task 4 |
| CEPA-080 CA-7 — confirmación y adherencia | `confirmar_citas`; estado CONFIRMADA; RN-8 | Task 4, Task 5 |
| CEPA-080 CA-8 — permisos por rol | RN-7; `require_role`; Auditor 403 en escritura | Task 5 |
| CEPA-080 RN-9 — auditoría | `record_audit` en generar y confirmar | Task 4 |
| CEPA-080 TC-080-08 — desbordamiento difiere al día siguiente | `proponer_agenda_semana` con cupo excedido | Task 3 |
| CEPA-080 TC-080-09 — Auditor solo lectura | `as_auditor` en tests de API | Task 5 |
| CEPA-080 TC-080-10 — rendimiento < 2 s | `test_agendamiento_rendimiento.py`; marcador `rendimiento` | Task 6 |

---

## Notas de cierre

### Firmas que dependen de EPIC-00/Fundación — verificar contra código real antes del loop

- `from app.auth.deps import get_current_user, require_role`: verificar que `require_role` acepte `*roles: str` y que `get_current_user` retorne un objeto con atributo `.username`. Si la firma es distinta, ajustar `router.py`.
- `from app.audit.service import record_audit`: verificar que acepte `(db, actor, action, entity, entity_id)` exactamente. Si usa `keyword-only arguments` o un dataclass, ajustar las llamadas en `service.py`.
- Fixtures `as_admin`, `as_coordinacion`, `as_auditor` en `conftest.py`: verificar que sean `TestClient` con headers JWT ya configurados (no solo `client`).

### Dependencias suaves de otras épicas (Oleada 3) — declarar antes del loop

| Épica | Tabla | Columnas requeridas por EPIC-08 |
|-------|-------|-------------------------------|
| EPIC-06 Controles | `control` | `paciente_id`, `profesional_id`, `fecha_prox_control` |
| EPIC-07 Licencias | `licencia` | `paciente_id`, `reposo_inicio`, `reposo_fin` |
| EPIC-02 Fármacos | `receta` | `paciente_id`, `fecha_emision`, `fecha_revision`, `requiere_seguimiento`, `gestionada` |
| EPIC-01 Ingresos | `paciente` | `id`, `nombre` |

Los tests de servicio que usan SQL crudo (`_insertar_control_proximo`) fallarán si EPIC-06 no está en `main`. La solución es: **mergear EPIC-06 y EPIC-07 antes de ejecutar el loop de EPIC-08**, o bien crear fixtures de `conftest.py` que inserten directamente en esas tablas (requiere tener las migraciones de esas épicas aplicadas).

### Decisiones de negocio abiertas del spec

- **Reposo parcial (D8):** el spec pregunta si el reposo parcial excluye toda la jornada o solo ciertos bloques. Actualmente `tiene_reposo_vigente` excluye el día completo. Si se decide exclusión parcial, `ReposoPaciente` debe agregar campos de hora y el scheduler debe extenderse.
- **Ventana de "receta reciente"** `VENTANA_SEGUIMIENTO_RECETA_DIAS = 30`: confirmar umbral real con equipo CEPA (PRD §7.2.3 / D7). Es constante en `service.py`, fácil de mover a `Settings`.
- **Ventana de "control próximo":** actualmente `fecha_prox_control ≤ fecha_fin + 7 días`. Confirmar horizonte real.
- **Integración con SALUTEM (D12):** `confirmar_citas` actualmente solo persiste en CEPA. Si se decide bidireccionalidad (D12), agregar llamada a EPIC-12 (API de Integración) desde `confirmar_citas`. El aplicativo **no escribe sobre SALUTEM**, pero puede enviar notificaciones.
- **down_revision de 0801:** reemplazar `<RESOLVER: alembic heads>` por el valor real de `uv run alembic heads` en el momento del loop.

### Rendimiento

El scheduler puro (`proponer_agenda_semana`) es O(n·d) donde n = candidatos y d = días hábiles del rango. Para 800 candidatos y un mes (~23 días hábiles) son ~18 400 operaciones — trivialmente por debajo del límite de 2 s. La carga desde BD en `_cargar_candidatos` usa tres queries SQL directas con índices en `profesional_id`; si se añaden FK reales en versiones futuras, agregar índices compuestos en `(profesional_id, fecha_prox_control)` y `(paciente_id, gestionada)`.
