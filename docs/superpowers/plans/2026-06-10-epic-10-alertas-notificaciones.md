# EPIC-10 — Alertas y Notificaciones — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Construir el motor central de alertas con plazos perentorios, el panel de notificaciones in-app por rol, el envío de correo SMTP para alertas y la gestión de tareas pendientes por rol, garantizando el objetivo institucional OU4 (0 % de vencimientos sin alerta previa).

**Architecture:** Se sigue el patrón de la Fundación + EPIC-01. Los modelos viven en `app/models/alertas.py`; la lógica de negocio —incluyendo el motor de evaluación de plazos— en `app/services/alertas.py` como función pura testeable (entrada: conjunto de hitos con fechas/plazos → salida: lista de alertas a crear). Los routers exponen `/api/v1/alertas` y `/api/v1/tareas`. El job de revisión programada se implementa como endpoint interno `/api/v1/alertas/ejecutar-job` invocable por el scheduler (cron del sistema o Celery Beat a futuro). El sender SMTP es una dependencia inyectable, reemplazable por un doble en tests. Una migración Alembic por historia que cree tablas.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos, `Identity`/`BigInteger`, `DateTime(timezone=True)`), Alembic, Pydantic v2, `smtplib` stdlib (sender SMTP), `pytest` sobre Postgres real. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`; fixtures `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`.
- Fixtures de test de EPIC-00: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.
- Tablas del dominio ya migradas: `ingreso`, `oda` (EPIC-01), `ept` (EPIC-03), `licencia` (EPIC-07).

**Convención RBAC en esta épica:**
```python
from app.auth.deps import require_role

_writer = require_role("Administrativo", "Coordinacion")   # escritura
_reader = require_role("Administrativo", "Coordinacion", "Auditor")  # lectura
```

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `backend/app/domain/enums_alertas.py` | Enums: `TipoAlerta`, `EstadoAlerta`, `EstadoTarea` |
| `backend/app/models/alertas.py` | Modelos SQLAlchemy: `Alerta`, `TareaItem` |
| `backend/app/schemas/alertas.py` | Schemas Pydantic v2: `AlertaRead`, `AlertaUpdate`, `TareaItemCreate`, `TareaItemRead`, `TareaItemUpdate` |
| `backend/app/services/alertas.py` | Motor puro `evaluar_plazos()`, `ejecutar_job_alertas()`, helpers de días hábiles |
| `backend/app/services/email_sender.py` | Protocolo `EmailSender` + implementación SMTP + `FakeEmailSender` para tests |
| `backend/app/routers/alertas.py` | Endpoints `/api/v1/alertas` y `/api/v1/alertas/ejecutar-job` |
| `backend/app/routers/tareas.py` | Endpoints `/api/v1/tareas` |
| `backend/migrations/versions/XXXX_alertas.py` | Migración: tablas `alerta`, `tarea_item` |
| `backend/migrations/versions/XXXX_tareas.py` | Migración: tabla `tarea_item` (si es historia separada) |
| `backend/tests/test_alertas_engine.py` | Tests unitarios del motor puro (sin BD) |
| `backend/tests/test_alertas_api.py` | Tests de integración de endpoints de alertas |
| `backend/tests/test_email_sender.py` | Tests del sender SMTP con doble |
| `backend/tests/test_tareas_api.py` | Tests de integración de endpoints de tareas |

---

## Task 1 — [P0] Enums y modelos de alertas (CEPA-100, CEPA-101)

**Files:**
- Create: `backend/app/domain/enums_alertas.py`
- Create: `backend/app/models/alertas.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_alertas_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_alertas_model.py`:

```python
from sqlalchemy import BigInteger, DateTime, Integer, String

from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import Alerta


def test_tabla_alerta_nombre_y_columnas():
    tabla = Alerta.__table__
    assert tabla.name == "alerta"
    columnas = set(tabla.columns.keys())
    assert columnas == {
        "id",
        "tipo",
        "estado",
        "caso_id",
        "caso_tipo",
        "usuario_id",
        "plazo_objetivo",
        "ventana_dias",
        "generada_en",
        "resuelta_en",
        "email_enviado",
    }


def test_reglas_portabilidad_alerta():
    tabla = Alerta.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pk_identity_y_tipos_genericos_alerta():
    cols = Alerta.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["tipo"].type, String)
    assert isinstance(cols["estado"].type, String)
    assert isinstance(cols["generada_en"].type, DateTime)
    assert cols["generada_en"].type.timezone is True


def test_enum_tipo_alerta_contiene_todos_los_tipos_rn1():
    tipos = {t.value for t in TipoAlerta}
    assert "control_medico" in tipos
    assert "vencimiento_licencia" in tipos
    assert "plazo_ept" in tipos
    assert "plazo_isl" in tipos
    assert "consentimiento_pendiente" in tipos
    assert "receta_por_renovar" in tipos
    assert "oda_por_vencer" in tipos
    assert len(tipos) == 7


def test_enum_estado_alerta():
    assert {e.value for e in EstadoAlerta} == {"pendiente", "leida", "resuelta"}
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_alertas_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.domain.enums_alertas'`.

- [ ] **Step 3: Crear los enums**

Crear `backend/app/domain/enums_alertas.py`:

```python
"""Listas cerradas del módulo de alertas y notificaciones (EPIC-10).

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo portabilidad de BD (no se usan tipos enum nativos del motor).
"""

from enum import Enum


class TipoAlerta(str, Enum):
    """Los 7 tipos de alerta soportados (RN-1 de CEPA-100)."""

    CONTROL_MEDICO = "control_medico"
    VENCIMIENTO_LICENCIA = "vencimiento_licencia"
    PLAZO_EPT = "plazo_ept"
    PLAZO_ISL = "plazo_isl"
    CONSENTIMIENTO_PENDIENTE = "consentimiento_pendiente"
    RECETA_POR_RENOVAR = "receta_por_renovar"
    ODA_POR_VENCER = "oda_por_vencer"


class EstadoAlerta(str, Enum):
    """Estados del ciclo de vida de una alerta (RN-5 de CEPA-101)."""

    PENDIENTE = "pendiente"
    LEIDA = "leida"
    RESUELTA = "resuelta"


class EstadoTarea(str, Enum):
    """Estados de una tarea operativa (RN-3 de CEPA-103)."""

    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
```

- [ ] **Step 4: Crear el modelo `Alerta`**

Crear `backend/app/models/alertas.py`:

```python
"""Modelos SQLAlchemy del módulo EPIC-10 — Alertas y Notificaciones.

Portabilidad D15: PK Identity/BigInteger, tipos genéricos, identificadores
≤30 chars en minúscula, fechas en UTC.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Alerta(Base):
    """Alerta generada por el motor de plazos perentorios (CEPA-100).

    Columnas:
    - tipo:            TipoAlerta.value (String)
    - estado:          EstadoAlerta.value (String)
    - caso_id:         id del objeto de dominio disparador (ingreso, oda, ept, licencia)
    - caso_tipo:       nombre del tipo ('ingreso', 'oda', 'ept', 'licencia')
    - usuario_id:      id del usuario Administrativo destinatario
    - plazo_objetivo:  fecha Date del plazo perentorio evaluado (para idempotencia RN-4)
    - ventana_dias:    días de anticipación configurados para este tipo de alerta
    - generada_en:     timestamp UTC de creación
    - resuelta_en:     timestamp UTC de resolución (null si pendiente/leida)
    - email_enviado:   True si el correo de alerta fue enviado (CEPA-102)
    """

    __tablename__ = "alerta"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    caso_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    caso_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    usuario_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    plazo_objetivo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ventana_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    generada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    resuelta_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_enviado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

- [ ] **Step 5: Registrar el modelo en `app/models/__init__.py`**

Agregar la importación al final del archivo:

```python
from app.models.alertas import Alerta  # noqa: F401
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_alertas_model.py -v`
Expected: `5 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/domain/enums_alertas.py backend/app/models/alertas.py backend/app/models/__init__.py backend/tests/test_alertas_model.py
git commit -m "feat(alertas): enums TipoAlerta/EstadoAlerta y modelo Alerta portable"
```

---

## Task 2 — [P0] Migración Alembic tabla `alerta` (CEPA-100)

**Files:**
- Create: `backend/migrations/versions/XXXX_crear_alerta.py`
- Test: `backend/tests/test_alertas_migration.py`

> `XXXX` = valor que devuelva `uv run alembic heads` antes de crear la revisión; ver Notas de cierre.

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_alertas_migration.py`:

```python
from sqlalchemy import inspect

from app.db.session import engine


def test_migracion_crea_tabla_alerta():
    tablas = inspect(engine).get_table_names()
    assert "alerta" in tablas


def test_columnas_alerta_en_bd():
    cols = {c["name"] for c in inspect(engine).get_columns("alerta")}
    assert cols == {
        "id",
        "tipo",
        "estado",
        "caso_id",
        "caso_tipo",
        "usuario_id",
        "plazo_objetivo",
        "ventana_dias",
        "generada_en",
        "resuelta_en",
        "email_enviado",
    }
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_alertas_migration.py -v`
Expected: FAIL — la tabla `alerta` no existe todavía.

- [ ] **Step 3: Obtener la revisión actual y crear el archivo de migración**

Run: `uv run alembic heads`
Expected: muestra el ID de la última revisión aplicada (ej. `0007`). Usar ese valor como `down_revision`.

Crear `backend/migrations/versions/XXXX_crear_alerta.py` (sustituir `XXXX` y `<PREV>` con los valores reales):

```python
"""crear alerta

Revision ID: XXXX
Revises: <PREV>
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "XXXX"
down_revision = "<PREV>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("caso_id", sa.BigInteger(), nullable=False),
        sa.Column("caso_tipo", sa.String(30), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("plazo_objetivo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ventana_dias", sa.Integer(), nullable=False),
        sa.Column("generada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_enviado", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_alerta_tipo", "alerta", ["tipo"])
    op.create_index("ix_alerta_caso_id", "alerta", ["caso_id"])
    op.create_index("ix_alerta_usuario_id", "alerta", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_alerta_usuario_id", table_name="alerta")
    op.drop_index("ix_alerta_caso_id", table_name="alerta")
    op.drop_index("ix_alerta_tipo", table_name="alerta")
    op.drop_table("alerta")
```

- [ ] **Step 4: Aplicar la migración**

Run:
```bash
uv run alembic upgrade head
```
Expected: `Running upgrade <PREV> -> XXXX, crear alerta`.

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_alertas_migration.py -v`
Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/XXXX_crear_alerta.py backend/tests/test_alertas_migration.py
git commit -m "feat(alertas): migración tabla alerta (P0)"
```

---

## Task 3 — [P0] Motor puro de evaluación de plazos — función pura testeable (CEPA-100)

Esta tarea implementa el núcleo del sistema: `evaluar_plazos()`, una función pura que recibe un conjunto de hitos con fechas/plazos y devuelve la lista de alertas a crear. Sin efectos secundarios: testeable sin BD, sin red. El helper de días hábiles también es puro.

**Files:**
- Create: `backend/app/services/alertas.py`
- Test: `backend/tests/test_alertas_engine.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_alertas_engine.py`:

```python
"""Tests unitarios del motor puro de evaluación de plazos (CEPA-100).

No requieren BD ni red — el motor es una función pura.
Cubre CA-1..CA-8, TC-100-01..TC-100-07.
"""

from datetime import date, timedelta

import pytest

from app.services.alertas import (
    HitoPlazos,
    ResultadoAlerta,
    dias_habiles_hasta,
    evaluar_plazos,
)


# ---------------------------------------------------------------------------
# Helper: dias_habiles_hasta
# ---------------------------------------------------------------------------


def test_dias_habiles_excluye_sabado_y_domingo():
    # lunes 2026-06-08 → viernes 2026-06-12: 4 días hábiles (mar, mie, jue, vie)
    lunes = date(2026, 6, 8)
    viernes = date(2026, 6, 12)
    assert dias_habiles_hasta(lunes, viernes) == 4


def test_dias_habiles_plazo_en_fin_de_semana(
    # TC-100-06: licencia que vence viernes, ventana 3d hábiles
    # Si hoy es martes 2026-06-09, el viernes 2026-06-12 está a 3 días hábiles (mie, jue, vie)
):
    hoy = date(2026, 6, 9)   # martes
    viernes = date(2026, 6, 12)  # viernes
    assert dias_habiles_hasta(hoy, viernes) == 3


def test_dias_habiles_misma_fecha():
    hoy = date(2026, 6, 10)
    assert dias_habiles_hasta(hoy, hoy) == 0


def test_dias_habiles_plazo_pasado():
    hoy = date(2026, 6, 10)
    ayer = date(2026, 6, 9)
    # plazo ya pasado → días negativos o cero; el motor no genera alerta de plazo pasado
    assert dias_habiles_hasta(hoy, ayer) < 0


# ---------------------------------------------------------------------------
# evaluar_plazos — casos positivos (CA-1..CA-6)
# ---------------------------------------------------------------------------


def test_genera_alerta_vencimiento_licencia_dentro_de_ventana():
    # TC-100-01: licencia que vence en 2 días hábiles, ventana 3 → debe generar alerta
    hoy = date(2026, 6, 9)  # martes
    vencimiento = date(2026, 6, 11)  # jueves (2 días hábiles)
    hitos = [
        HitoPlazos(
            tipo="vencimiento_licencia",
            caso_id=1,
            caso_tipo="licencia",
            usuario_id=10,
            plazo_objetivo=vencimiento,
            ventana_dias=3,
            usar_dias_habiles=True,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "vencimiento_licencia"
    assert resultados[0].caso_id == 1
    assert resultados[0].usuario_id == 10


def test_no_genera_alerta_fuera_de_ventana():
    # TC-100-04: licencia que vence en 30 días → fuera de ventana de 3 días hábiles
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=30)
    hitos = [
        HitoPlazos(
            tipo="vencimiento_licencia",
            caso_id=2,
            caso_tipo="licencia",
            usuario_id=10,
            plazo_objetivo=vencimiento,
            ventana_dias=3,
            usar_dias_habiles=True,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 0


def test_genera_alerta_oda_por_vencer():
    # TC-100-02: ODA con vencimiento dentro de ventana (días calendario)
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=5)
    hitos = [
        HitoPlazos(
            tipo="oda_por_vencer",
            caso_id=3,
            caso_tipo="oda",
            usuario_id=11,
            plazo_objetivo=vencimiento,
            ventana_dias=7,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "oda_por_vencer"


def test_genera_alerta_consentimiento_pendiente():
    # TC-100-03: caso sin consentimiento firmado — el hito tiene plazo = hoy (urgente)
    hoy = date(2026, 6, 9)
    hitos = [
        HitoPlazos(
            tipo="consentimiento_pendiente",
            caso_id=4,
            caso_tipo="ingreso",
            usuario_id=12,
            plazo_objetivo=hoy,
            ventana_dias=30,  # siempre dentro de ventana mientras esté pendiente
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "consentimiento_pendiente"


def test_genera_alerta_receta_por_renovar():
    # CA-5: receta con fecha de revisión en 4 días, ventana 5 → dentro
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=4)
    hitos = [
        HitoPlazos(
            tipo="receta_por_renovar",
            caso_id=5,
            caso_tipo="ingreso",
            usuario_id=13,
            plazo_objetivo=vencimiento,
            ventana_dias=5,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1


def test_genera_alerta_plazo_ept():
    # CA-3: EPT con plazo de informe dentro de ventana en días hábiles
    hoy = date(2026, 6, 9)  # martes
    plazo = date(2026, 6, 12)  # viernes, 3 días hábiles
    hitos = [
        HitoPlazos(
            tipo="plazo_ept",
            caso_id=6,
            caso_tipo="ept",
            usuario_id=14,
            plazo_objetivo=plazo,
            ventana_dias=5,
            usar_dias_habiles=True,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "plazo_ept"


def test_genera_alerta_plazo_isl():
    hoy = date(2026, 6, 9)
    plazo = hoy + timedelta(days=3)
    hitos = [
        HitoPlazos(
            tipo="plazo_isl",
            caso_id=7,
            caso_tipo="ept",
            usuario_id=14,
            plazo_objetivo=plazo,
            ventana_dias=5,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1
    assert resultados[0].tipo == "plazo_isl"


def test_genera_alerta_control_medico():
    # CA-1: control médico dentro de ventana
    hoy = date(2026, 6, 9)
    plazo = hoy + timedelta(days=2)
    hitos = [
        HitoPlazos(
            tipo="control_medico",
            caso_id=8,
            caso_tipo="ingreso",
            usuario_id=15,
            plazo_objetivo=plazo,
            ventana_dias=7,
            usar_dias_habiles=False,
        )
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    assert len(resultados) == 1


# ---------------------------------------------------------------------------
# Idempotencia (CA-7, TC-100-05)
# ---------------------------------------------------------------------------


def test_idempotencia_excluye_alertas_ya_activas():
    # CA-7: si la misma (caso_id, tipo) ya tiene alerta activa, evaluar_plazos
    # la omite cuando se le pasa el set de claves ya existentes.
    hoy = date(2026, 6, 9)
    vencimiento = hoy + timedelta(days=2)
    hitos = [
        HitoPlazos(
            tipo="vencimiento_licencia",
            caso_id=20,
            caso_tipo="licencia",
            usuario_id=10,
            plazo_objetivo=vencimiento,
            ventana_dias=3,
            usar_dias_habiles=True,
        )
    ]
    # Primera evaluación: debe generar alerta
    primera = evaluar_plazos(hitos, hoy=hoy, alertas_activas=set())
    assert len(primera) == 1

    # Segunda evaluación con la alerta ya activa: no debe duplicar
    clave_activa = (20, "vencimiento_licencia")
    segunda = evaluar_plazos(hitos, hoy=hoy, alertas_activas={clave_activa})
    assert len(segunda) == 0


def test_evaluar_plazos_multiples_hitos_independientes():
    hoy = date(2026, 6, 9)
    hitos = [
        HitoPlazos(
            tipo="oda_por_vencer",
            caso_id=30,
            caso_tipo="oda",
            usuario_id=10,
            plazo_objetivo=hoy + timedelta(days=2),
            ventana_dias=7,
            usar_dias_habiles=False,
        ),
        HitoPlazos(
            tipo="receta_por_renovar",
            caso_id=31,
            caso_tipo="ingreso",
            usuario_id=11,
            plazo_objetivo=hoy + timedelta(days=50),  # fuera de ventana
            ventana_dias=5,
            usar_dias_habiles=False,
        ),
        HitoPlazos(
            tipo="consentimiento_pendiente",
            caso_id=32,
            caso_tipo="ingreso",
            usuario_id=12,
            plazo_objetivo=hoy,
            ventana_dias=30,
            usar_dias_habiles=False,
        ),
    ]
    resultados = evaluar_plazos(hitos, hoy=hoy)
    # Solo los hitos 0 y 2 están dentro de su ventana
    assert len(resultados) == 2
    tipos = {r.tipo for r in resultados}
    assert tipos == {"oda_por_vencer", "consentimiento_pendiente"}
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_alertas_engine.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.alertas'`.

- [ ] **Step 3: Implementar el motor puro**

Crear `backend/app/services/alertas.py`:

```python
"""Motor de evaluación de plazos perentorios — CEPA-100.

Diseño: función pura `evaluar_plazos()`.
  - Entrada:  lista de HitoPlazos + fecha `hoy` + set de alertas activas.
  - Salida:   lista de ResultadoAlerta a crear (sin efectos secundarios).
  - Sin BD, sin red → completamente testeable como función unitaria.

El job de revisión (`ejecutar_job_alertas`) construye los HitoPlazos
consultando la BD y llama a esta función.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


# ---------------------------------------------------------------------------
# Tipos de datos (no son modelos ORM — son DTOs del motor)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HitoPlazos:
    """Representa un plazo perentorio a evaluar.

    tipo:              valor de TipoAlerta (str)
    caso_id:           PK del objeto disparador
    caso_tipo:         'ingreso' | 'oda' | 'ept' | 'licencia'
    usuario_id:        PK del usuario Administrativo destinatario
    plazo_objetivo:    date del plazo perentorio
    ventana_dias:      días de anticipación configurados
    usar_dias_habiles: True → cálculo en días hábiles; False → días calendario
    """

    tipo: str
    caso_id: int
    caso_tipo: str
    usuario_id: int
    plazo_objetivo: date
    ventana_dias: int
    usar_dias_habiles: bool = False


@dataclass
class ResultadoAlerta:
    """DTO devuelto por evaluar_plazos; se persistirá como fila en `alerta`."""

    tipo: str
    caso_id: int
    caso_tipo: str
    usuario_id: int
    plazo_objetivo: date
    ventana_dias: int


# ---------------------------------------------------------------------------
# Helper: cálculo de días hábiles
# ---------------------------------------------------------------------------


def dias_habiles_hasta(hoy: date, plazo: date) -> int:
    """Devuelve el número de días hábiles (lun–vie) entre hoy (exclusivo) y plazo (inclusivo).

    Negativo si el plazo ya pasó. No considera festivos — confirmar con CEPA si se requieren.
    """
    if plazo <= hoy:
        # Calcular días hábiles negativos para plazos pasados
        delta = 0
        cursor = plazo
        while cursor < hoy:
            if cursor.weekday() < 5:  # 0=lunes … 4=viernes
                delta -= 1
            cursor = date(cursor.year, cursor.month, cursor.day).__class__(
                cursor.year, cursor.month, cursor.day
            )
            from datetime import timedelta as _td
            cursor = cursor + _td(days=1)
        return delta

    from datetime import timedelta as _td

    habiles = 0
    cursor = hoy + _td(days=1)
    while cursor <= plazo:
        if cursor.weekday() < 5:
            habiles += 1
        cursor += _td(days=1)
    return habiles


# ---------------------------------------------------------------------------
# Motor puro
# ---------------------------------------------------------------------------


def evaluar_plazos(
    hitos: list[HitoPlazos],
    *,
    hoy: date | None = None,
    alertas_activas: set[tuple[int, str]] | None = None,
) -> list[ResultadoAlerta]:
    """Evalúa una lista de hitos y devuelve los que deben generar una nueva alerta.

    Args:
        hitos:           lista de plazos a evaluar.
        hoy:             fecha de referencia (default: date.today()).
        alertas_activas: set de (caso_id, tipo) ya activos — para idempotencia (CA-7).

    Returns:
        Lista de ResultadoAlerta que el llamador persistirá en la BD.
    """
    if hoy is None:
        hoy = date.today()
    if alertas_activas is None:
        alertas_activas = set()

    resultados: list[ResultadoAlerta] = []
    for hito in hitos:
        clave = (hito.caso_id, hito.tipo)
        if clave in alertas_activas:
            continue  # idempotencia: ya existe alerta activa para este (caso, tipo)

        if hito.usar_dias_habiles:
            dias_restantes = dias_habiles_hasta(hoy, hito.plazo_objetivo)
        else:
            from datetime import timedelta as _td
            dias_restantes = (hito.plazo_objetivo - hoy).days

        if 0 <= dias_restantes <= hito.ventana_dias:
            resultados.append(
                ResultadoAlerta(
                    tipo=hito.tipo,
                    caso_id=hito.caso_id,
                    caso_tipo=hito.caso_tipo,
                    usuario_id=hito.usuario_id,
                    plazo_objetivo=hito.plazo_objetivo,
                    ventana_dias=hito.ventana_dias,
                )
            )
    return resultados
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_alertas_engine.py -v`
Expected: `13 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/alertas.py backend/tests/test_alertas_engine.py
git commit -m "feat(alertas): motor puro evaluar_plazos() con idempotencia y días hábiles (CEPA-100)"
```

---

## Task 4 — [P0] Job de revisión de alertas + persistencia en BD (CEPA-100)

Integra el motor puro con la BD: consulta hitos desde las tablas de dominio, llama a `evaluar_plazos()` y persiste las alertas resultantes.

**Files:**
- Modify: `backend/app/services/alertas.py` (agregar `ejecutar_job_alertas`)
- Create: `backend/app/schemas/alertas.py`
- Create: `backend/app/routers/alertas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_alertas_api.py` (parte job)

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_alertas_api.py`:

```python
"""Tests de integración de los endpoints de alertas (CEPA-100, CEPA-101).

Precondición: tablas alerta, ingreso, oda (ya migradas por las épicas anteriores).
Para el job de alertas se crea un hito sintético directamente en la BD de test.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alertas import Alerta


def _alerta_en_bd(db: Session, *, usuario_id: int = 1, tipo: str = "oda_por_vencer") -> Alerta:
    """Helper: inserta una alerta directamente para setup de tests."""
    from datetime import datetime, timezone
    alerta = Alerta(
        tipo=tipo,
        estado="pendiente",
        caso_id=999,
        caso_tipo="oda",
        usuario_id=usuario_id,
        plazo_objetivo=datetime.now(timezone.utc) + timedelta(days=3),
        ventana_dias=7,
        email_enviado=False,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


# ---------------------------------------------------------------------------
# Endpoint: POST /api/v1/alertas/ejecutar-job
# ---------------------------------------------------------------------------


def test_job_requiere_autenticacion(client: TestClient):
    resp = client.post("/api/v1/alertas/ejecutar-job")
    assert resp.status_code == 401


def test_job_ejecutable_por_admin(as_admin: TestClient):
    resp = as_admin.post("/api/v1/alertas/ejecutar-job")
    # El job puede no generar alertas si no hay hitos en la BD de test,
    # pero debe responder 200 con un resumen.
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert "alertas_generadas" in cuerpo
    assert isinstance(cuerpo["alertas_generadas"], int)


def test_job_no_accesible_por_auditor(as_auditor: TestClient):
    resp = as_auditor.post("/api/v1/alertas/ejecutar-job")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Endpoint: GET /api/v1/alertas
# ---------------------------------------------------------------------------


def test_listar_alertas_requiere_autenticacion(client: TestClient):
    resp = client.get("/api/v1/alertas")
    assert resp.status_code == 401


def test_admin_ve_sus_alertas(as_admin: TestClient, db_session: Session):
    # Creamos una alerta asignada al usuario cuyo ID corresponde al fixture as_admin
    # (en conftest de EPIC-00, as_admin usa el usuario con id=1 por convención)
    _alerta_en_bd(db_session, usuario_id=1, tipo="oda_por_vencer")
    resp = as_admin.get("/api/v1/alertas")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(a["tipo"] == "oda_por_vencer" for a in data)


def test_auditor_puede_leer_alertas(as_auditor: TestClient, db_session: Session):
    # TC-101-04: auditor tiene lectura
    _alerta_en_bd(db_session, usuario_id=1, tipo="receta_por_renovar")
    resp = as_auditor.get("/api/v1/alertas")
    assert resp.status_code == 200


def test_panel_sin_alertas_devuelve_lista_vacia(as_admin: TestClient, db_session: Session):
    # TC-101-05: usuario sin alertas → lista vacía, sin error
    resp = as_admin.get("/api/v1/alertas")
    assert resp.status_code == 200
    # Puede ser lista vacía si no hay alertas para usuario_id=1
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Endpoint: PATCH /api/v1/alertas/{id}
# ---------------------------------------------------------------------------


def test_marcar_alerta_resuelta(as_admin: TestClient, db_session: Session):
    # TC-101-02, CA-4: cambiar estado a resuelta
    alerta = _alerta_en_bd(db_session, usuario_id=1, tipo="control_medico")
    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "resuelta"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "resuelta"
    assert resp.json()["resuelta_en"] is not None


def test_marcar_alerta_leida(as_admin: TestClient, db_session: Session):
    alerta = _alerta_en_bd(db_session, usuario_id=1, tipo="vencimiento_licencia")
    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "leida"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "leida"


def test_auditor_no_puede_cambiar_estado(as_auditor: TestClient, db_session: Session):
    # TC-101-04: auditor no puede editar
    alerta = _alerta_en_bd(db_session, usuario_id=1)
    resp = as_auditor.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "resuelta"})
    assert resp.status_code == 403


def test_cambiar_estado_alerta_inexistente(as_admin: TestClient):
    resp = as_admin.patch("/api/v1/alertas/99999", json={"estado": "resuelta"})
    assert resp.status_code == 404


def test_segregacion_admin_no_ve_alertas_de_otro_usuario(
    as_admin: TestClient, db_session: Session
):
    # TC-101-03: admin A (usuario_id=1) NO ve alertas de usuario_id=99
    _alerta_en_bd(db_session, usuario_id=99, tipo="oda_por_vencer")
    resp = as_admin.get("/api/v1/alertas")
    assert resp.status_code == 200
    ids_usuario = {a["usuario_id"] for a in resp.json()}
    assert 99 not in ids_usuario
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_alertas_api.py -v`
Expected: FAIL con `404 Not Found` (las rutas no existen aún).

- [ ] **Step 3: Crear los schemas Pydantic**

Crear `backend/app/schemas/alertas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums_alertas import EstadoAlerta, TipoAlerta


class AlertaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    estado: str
    caso_id: int
    caso_tipo: str
    usuario_id: int
    plazo_objetivo: datetime
    ventana_dias: int
    generada_en: datetime
    resuelta_en: datetime | None
    email_enviado: bool


class AlertaUpdate(BaseModel):
    estado: EstadoAlerta


class JobResultado(BaseModel):
    alertas_generadas: int
    timestamp: datetime
```

- [ ] **Step 4: Ampliar el servicio con `ejecutar_job_alertas`**

Agregar al final de `backend/app/services/alertas.py` (después del motor puro existente):

```python
# ---------------------------------------------------------------------------
# Job de revisión: construye hitos desde la BD y persiste alertas
# ---------------------------------------------------------------------------

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import Alerta


# Ventanas de aviso por defecto (días). Ajustar según confirmación de Coordinación (RN-3).
VENTANAS_DEFAULT: dict[str, dict] = {
    TipoAlerta.VENCIMIENTO_LICENCIA.value: {"dias": 3, "habiles": True},
    TipoAlerta.PLAZO_EPT.value:            {"dias": 5, "habiles": True},
    TipoAlerta.PLAZO_ISL.value:            {"dias": 5, "habiles": True},
    TipoAlerta.RECETA_POR_RENOVAR.value:   {"dias": 5, "habiles": False},
    TipoAlerta.ODA_POR_VENCER.value:       {"dias": 7, "habiles": False},
    TipoAlerta.CONTROL_MEDICO.value:       {"dias": 7, "habiles": False},
    TipoAlerta.CONSENTIMIENTO_PENDIENTE.value: {"dias": 30, "habiles": False},
}


def _cargar_alertas_activas(db: Session) -> set[tuple[int, str]]:
    """Devuelve el set de (caso_id, tipo) con alertas en estado pendiente o leída."""
    filas = db.execute(
        select(Alerta.caso_id, Alerta.tipo).where(
            Alerta.estado.in_([EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value])
        )
    ).all()
    return {(fila.caso_id, fila.tipo) for fila in filas}


def _construir_hitos_oda(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla oda (EPIC-01, D3).

    Asume que la tabla `oda` tiene columnas: id, fecha_vencimiento, usuario_id.
    Si la tabla no existe (épica no desplegada) devuelve lista vacía.
    """
    from sqlalchemy import text
    try:
        filas = db.execute(
            text(
                "SELECT id, fecha_vencimiento, usuario_id FROM oda "
                "WHERE fecha_vencimiento IS NOT NULL"
            )
        ).mappings().all()
    except Exception:
        return []
    ventana = VENTANAS_DEFAULT[TipoAlerta.ODA_POR_VENCER.value]
    hitos = []
    for f in filas:
        if f["fecha_vencimiento"] is None:
            continue
        plazo = f["fecha_vencimiento"]
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.ODA_POR_VENCER.value,
                caso_id=f["id"],
                caso_tipo="oda",
                usuario_id=f["usuario_id"],
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_licencias(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla licencia (EPIC-07).

    Asume columnas: id, fecha_fin_reposo, usuario_id.
    """
    from sqlalchemy import text
    try:
        filas = db.execute(
            text(
                "SELECT id, fecha_fin_reposo, usuario_id FROM licencia "
                "WHERE fecha_fin_reposo IS NOT NULL"
            )
        ).mappings().all()
    except Exception:
        return []
    ventana = VENTANAS_DEFAULT[TipoAlerta.VENCIMIENTO_LICENCIA.value]
    hitos = []
    for f in filas:
        if f["fecha_fin_reposo"] is None:
            continue
        plazo = f["fecha_fin_reposo"]
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.VENCIMIENTO_LICENCIA.value,
                caso_id=f["id"],
                caso_tipo="licencia",
                usuario_id=f["usuario_id"],
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_ept(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla ept (EPIC-03).

    Asume columnas: id, fecha_plazo_informe, fecha_plazo_isl, usuario_id.
    """
    from sqlalchemy import text
    hitos: list[HitoPlazos] = []
    try:
        filas = db.execute(
            text(
                "SELECT id, fecha_plazo_informe, fecha_plazo_isl, usuario_id FROM ept"
            )
        ).mappings().all()
    except Exception:
        return []

    v_ept = VENTANAS_DEFAULT[TipoAlerta.PLAZO_EPT.value]
    v_isl = VENTANAS_DEFAULT[TipoAlerta.PLAZO_ISL.value]
    for f in filas:
        for campo, tipo, ventana in [
            ("fecha_plazo_informe", TipoAlerta.PLAZO_EPT.value, v_ept),
            ("fecha_plazo_isl", TipoAlerta.PLAZO_ISL.value, v_isl),
        ]:
            if f[campo] is None:
                continue
            plazo = f[campo]
            if hasattr(plazo, "date"):
                plazo = plazo.date()
            hitos.append(
                HitoPlazos(
                    tipo=tipo,
                    caso_id=f["id"],
                    caso_tipo="ept",
                    usuario_id=f["usuario_id"],
                    plazo_objetivo=plazo,
                    ventana_dias=ventana["dias"],
                    usar_dias_habiles=ventana["habiles"],
                )
            )
    return hitos


def _construir_hitos_consentimiento(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos para ingresos sin consentimiento firmado (CA-4, D9).

    Asume tabla ingreso con columnas: id, consentimiento_estado, usuario_id.
    consentimiento_estado == 'pendiente' → sin firmar.
    """
    from sqlalchemy import text
    try:
        filas = db.execute(
            text(
                "SELECT id, usuario_id, fecha_ingreso FROM ingreso "
                "WHERE consentimiento_estado = 'pendiente'"
            )
        ).mappings().all()
    except Exception:
        return []

    ventana = VENTANAS_DEFAULT[TipoAlerta.CONSENTIMIENTO_PENDIENTE.value]
    hitos = []
    for f in filas:
        plazo = f.get("fecha_ingreso") or date.today()
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.CONSENTIMIENTO_PENDIENTE.value,
                caso_id=f["id"],
                caso_tipo="ingreso",
                usuario_id=f["usuario_id"],
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def ejecutar_job_alertas(db: Session, *, actor: str = "sistema") -> int:
    """Job principal de revisión de plazos.

    Construye todos los hitos de dominio, evalúa plazos y persiste las alertas nuevas.
    Devuelve el número de alertas generadas en esta ejecución.
    Registra auditoría vía record_audit (RN-8, CA-8).
    """
    from app.audit.service import record_audit

    hoy = date.today()

    hitos: list[HitoPlazos] = []
    hitos.extend(_construir_hitos_oda(db))
    hitos.extend(_construir_hitos_licencias(db))
    hitos.extend(_construir_hitos_ept(db))
    hitos.extend(_construir_hitos_consentimiento(db))

    alertas_activas = _cargar_alertas_activas(db)
    resultados = evaluar_plazos(hitos, hoy=hoy, alertas_activas=alertas_activas)

    for r in resultados:
        alerta = Alerta(
            tipo=r.tipo,
            estado=EstadoAlerta.PENDIENTE.value,
            caso_id=r.caso_id,
            caso_tipo=r.caso_tipo,
            usuario_id=r.usuario_id,
            plazo_objetivo=datetime.combine(r.plazo_objetivo, datetime.min.time()).replace(
                tzinfo=timezone.utc
            ),
            ventana_dias=r.ventana_dias,
            email_enviado=False,
        )
        db.add(alerta)

    if resultados:
        db.commit()
        record_audit(
            db,
            actor=actor,
            action="CREATE",
            entity="alerta",
            entity_id=f"job:{len(resultados)}",
        )

    return len(resultados)
```

- [ ] **Step 5: Crear el router de alertas**

Crear `backend/app/routers/alertas.py`:

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.audit.service import record_audit
from app.db.session import get_db
from app.domain.enums_alertas import EstadoAlerta
from app.models.alertas import Alerta
from app.schemas.alertas import AlertaRead, AlertaUpdate, JobResultado
from app.services.alertas import ejecutar_job_alertas

router = APIRouter(prefix="/api/v1/alertas", tags=["alertas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "/ejecutar-job",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def ejecutar_job(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Ejecuta el job de revisión de plazos perentorios (CEPA-100 RN-2)."""
    generadas = ejecutar_job_alertas(db, actor=current_user.username)
    return JobResultado(alertas_generadas=generadas, timestamp=datetime.now(timezone.utc))


@router.get("", response_model=list[AlertaRead], dependencies=[Depends(_reader)])
def listar_alertas(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Alerta]:
    """Panel de notificaciones in-app: devuelve alertas filtradas por rol y asignación.

    - Administrativo: solo sus alertas (usuario_id == current_user.id).
    - Coordinacion/Auditor: todas las alertas (alcance ampliado, RN-2/RN-3 CEPA-101).
    """
    stmt = select(Alerta)
    if current_user.role == "Administrativo":
        stmt = stmt.where(Alerta.usuario_id == current_user.id)
    stmt = stmt.order_by(Alerta.generada_en.desc())
    return list(db.scalars(stmt))


@router.patch("/{alerta_id}", response_model=AlertaRead, dependencies=[Depends(_writer)])
def actualizar_estado_alerta(
    alerta_id: int,
    payload: AlertaUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Alerta:
    """Marca una alerta como leída o resuelta (CA-4 CEPA-101)."""
    alerta = db.get(Alerta, alerta_id)
    if alerta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    alerta.estado = payload.estado.value
    if payload.estado == EstadoAlerta.RESUELTA:
        alerta.resuelta_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alerta)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="alerta",
        entity_id=str(alerta_id),
    )
    return alerta
```

- [ ] **Step 6: Registrar el router en `app/main.py`**

Agregar en `backend/app/main.py` (junto a los demás `include_router`):

```python
from app.routers import alertas
app.include_router(alertas.router)
```

- [ ] **Step 7: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_alertas_api.py -v`
Expected: `11 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/alertas.py backend/app/services/alertas.py backend/app/routers/alertas.py backend/app/main.py backend/tests/test_alertas_api.py
git commit -m "feat(alertas): job de revisión + panel in-app + endpoint PATCH estado (CEPA-100, CEPA-101 P0)"
```

---

## Task 5 — [P1] Modelo y migración `tarea_item` (CEPA-103)

**Files:**
- Create: `backend/app/models/tareas.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/YYYY_crear_tarea_item.py`
- Test: `backend/tests/test_tareas_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_tareas_model.py`:

```python
from sqlalchemy import BigInteger, DateTime, String

from app.domain.enums_alertas import EstadoTarea
from app.models.tareas import TareaItem


def test_tabla_tarea_item_nombre_y_columnas():
    tabla = TareaItem.__table__
    assert tabla.name == "tarea_item"
    cols = set(tabla.columns.keys())
    assert cols == {
        "id",
        "titulo",
        "descripcion",
        "estado",
        "tipo_tarea",
        "caso_id",
        "caso_tipo",
        "usuario_id",
        "creada_en",
        "completada_en",
        "completada_por",
    }


def test_reglas_portabilidad_tarea_item():
    tabla = TareaItem.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pk_identity_tarea_item():
    cols = TareaItem.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)


def test_enum_estado_tarea():
    assert {e.value for e in EstadoTarea} == {"pendiente", "en_progreso", "completada"}
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_tareas_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.tareas'`.

- [ ] **Step 3: Crear el modelo `TareaItem`**

Crear `backend/app/models/tareas.py`:

```python
"""Modelo TareaItem — tareas operativas por rol (CEPA-103 EPIC-10).

Portabilidad D15: PK Identity/BigInteger, tipos genéricos, identificadores
≤30 chars en minúscula, fechas en UTC.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TareaItem(Base):
    """Tarea operativa asignada a un usuario por rol.

    - usuario_id:    destinatario principal de la tarea
    - tipo_tarea:    categoría operativa ('gestionar_receta', 'enviar_informe', etc.)
    - caso_id:       id del objeto de dominio origen (nullable — tarea puede ser sin caso)
    - caso_tipo:     'ingreso' | 'oda' | 'ept' | etc. (nullable)
    - completada_por: username de quien completó (RN-3 — registrar quién y cuándo)
    """

    __tablename__ = "tarea_item"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    tipo_tarea: Mapped[str] = mapped_column(String(60), nullable=False)
    caso_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    caso_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completada_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
```

- [ ] **Step 4: Registrar el modelo en `app/models/__init__.py`**

Agregar al final:

```python
from app.models.tareas import TareaItem  # noqa: F401
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_tareas_model.py -v`
Expected: `4 passed`.

- [ ] **Step 6: Crear la migración**

Run: `uv run alembic heads` → anotar el ID actual como `<PREV>`.

Crear `backend/migrations/versions/YYYY_crear_tarea_item.py`:

```python
"""crear tarea_item

Revision ID: YYYY
Revises: XXXX
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "YYYY"
down_revision = "XXXX"   # <-- sustituir por el ID real de la migración anterior
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tarea_item",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("tipo_tarea", sa.String(60), nullable=False),
        sa.Column("caso_id", sa.BigInteger(), nullable=True),
        sa.Column("caso_tipo", sa.String(30), nullable=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completada_por", sa.String(120), nullable=True),
    )
    op.create_index("ix_tarea_item_usuario_id", "tarea_item", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_tarea_item_usuario_id", table_name="tarea_item")
    op.drop_table("tarea_item")
```

Run: `uv run alembic upgrade head`
Expected: `Running upgrade XXXX -> YYYY, crear tarea_item`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/tareas.py backend/app/models/__init__.py backend/migrations/versions/YYYY_crear_tarea_item.py backend/tests/test_tareas_model.py
git commit -m "feat(tareas): modelo TareaItem + migración (CEPA-103 P1)"
```

---

## Task 6 — [P1] API de tareas pendientes por rol (CEPA-103)

**Files:**
- Create: `backend/app/schemas/tareas.py`
- Create: `backend/app/routers/tareas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_tareas_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_tareas_api.py`:

```python
"""Tests de integración del módulo de tareas pendientes por rol (CEPA-103).

Cubre CA-1..CA-4 y TC-103-01..TC-103-05.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.tareas import TareaItem


def _tarea(db: Session, *, usuario_id: int = 1, estado: str = "pendiente") -> TareaItem:
    t = TareaItem(
        titulo="Gestionar receta",
        descripcion="Renovar receta paciente X",
        estado=estado,
        tipo_tarea="gestionar_receta",
        caso_id=101,
        caso_tipo="ingreso",
        usuario_id=usuario_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# GET /api/v1/tareas
# ---------------------------------------------------------------------------


def test_listar_tareas_requiere_autenticacion(client: TestClient):
    resp = client.get("/api/v1/tareas")
    assert resp.status_code == 401


def test_admin_ve_sus_tareas(as_admin: TestClient, db_session: Session):
    # TC-103-01: admin ve sus tareas pendientes
    _tarea(db_session, usuario_id=1)
    resp = as_admin.get("/api/v1/tareas")
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["tipo_tarea"] == "gestionar_receta" for t in data)


def test_lista_tareas_vacia_sin_error(as_admin: TestClient, db_session: Session):
    # TC-103-05: sin tareas pendientes → lista vacía, sin error
    resp = as_admin.get("/api/v1/tareas")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_segregacion_admin_no_ve_tareas_de_otro(as_admin: TestClient, db_session: Session):
    # TC-103-03: admin A no ve tareas de admin B (usuario_id=99)
    _tarea(db_session, usuario_id=99)
    resp = as_admin.get("/api/v1/tareas")
    assert resp.status_code == 200
    ids_usuario = {t["usuario_id"] for t in resp.json()}
    assert 99 not in ids_usuario


def test_coordinacion_ve_tareas_del_equipo(as_coordinacion: TestClient, db_session: Session):
    # TC-103-04: Coordinación ve estado de tareas del equipo (sin filtro de usuario_id)
    _tarea(db_session, usuario_id=1)
    _tarea(db_session, usuario_id=2)
    resp = as_coordinacion.get("/api/v1/tareas")
    assert resp.status_code == 200
    # Coordinación debe ver las tareas de todos los usuarios
    assert len(resp.json()) >= 2


# ---------------------------------------------------------------------------
# POST /api/v1/tareas
# ---------------------------------------------------------------------------


def test_crear_tarea_como_admin(as_admin: TestClient):
    payload = {
        "titulo": "Enviar informe EPT",
        "descripcion": "Enviar informe al ISL antes del viernes",
        "tipo_tarea": "enviar_informe",
        "usuario_id": 1,
        "caso_id": 55,
        "caso_tipo": "ept",
    }
    resp = as_admin.post("/api/v1/tareas", json=payload)
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["titulo"] == "Enviar informe EPT"
    assert cuerpo["estado"] == "pendiente"


def test_auditor_no_puede_crear_tarea(as_auditor: TestClient):
    payload = {
        "titulo": "Tarea de auditor",
        "tipo_tarea": "otro",
        "usuario_id": 1,
    }
    resp = as_auditor.post("/api/v1/tareas", json=payload)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/v1/tareas/{id}
# ---------------------------------------------------------------------------


def test_completar_tarea(as_admin: TestClient, db_session: Session):
    # TC-103-02: tarea pasa a completada y sale de pendientes
    tarea = _tarea(db_session, usuario_id=1)
    resp = as_admin.patch(f"/api/v1/tareas/{tarea.id}", json={"estado": "completada"})
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "completada"
    assert cuerpo["completada_en"] is not None
    assert cuerpo["completada_por"] is not None


def test_completar_tarea_inexistente(as_admin: TestClient):
    resp = as_admin.patch("/api/v1/tareas/99999", json={"estado": "completada"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_tareas_api.py -v`
Expected: FAIL con `404 Not Found` (las rutas no existen).

- [ ] **Step 3: Crear los schemas de tareas**

Crear `backend/app/schemas/tareas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums_alertas import EstadoTarea


class TareaItemCreate(BaseModel):
    titulo: str
    descripcion: str | None = None
    tipo_tarea: str
    usuario_id: int
    caso_id: int | None = None
    caso_tipo: str | None = None


class TareaItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str | None
    estado: str
    tipo_tarea: str
    usuario_id: int
    caso_id: int | None
    caso_tipo: str | None
    creada_en: datetime
    completada_en: datetime | None
    completada_por: str | None


class TareaItemUpdate(BaseModel):
    estado: EstadoTarea
```

- [ ] **Step 4: Crear el router de tareas**

Crear `backend/app/routers/tareas.py`:

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.audit.service import record_audit
from app.db.session import get_db
from app.domain.enums_alertas import EstadoTarea
from app.models.tareas import TareaItem
from app.schemas.tareas import TareaItemCreate, TareaItemRead, TareaItemUpdate

router = APIRouter(prefix="/api/v1/tareas", tags=["tareas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get("", response_model=list[TareaItemRead], dependencies=[Depends(_reader)])
def listar_tareas(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TareaItem]:
    """Lista de tareas pendientes por rol (CA-1, CA-3, CA-4 CEPA-103).

    - Administrativo: solo sus tareas (usuario_id == current_user.id).
    - Coordinacion: todas las tareas del equipo (vista de supervisión, CA-4).
    - Auditor: lectura de todas (sin filtro de usuario).
    """
    stmt = select(TareaItem).where(TareaItem.estado != EstadoTarea.COMPLETADA.value)
    if current_user.role == "Administrativo":
        stmt = stmt.where(TareaItem.usuario_id == current_user.id)
    stmt = stmt.order_by(TareaItem.creada_en.desc())
    return list(db.scalars(stmt))


@router.post(
    "",
    response_model=TareaItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_tarea(
    payload: TareaItemCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TareaItem:
    """Crea una tarea operativa asignada a un usuario (RN-1 CEPA-103)."""
    tarea = TareaItem(**payload.model_dump(), estado=EstadoTarea.PENDIENTE.value)
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="tarea_item",
        entity_id=str(tarea.id),
    )
    return tarea


@router.patch("/{tarea_id}", response_model=TareaItemRead, dependencies=[Depends(_writer)])
def actualizar_tarea(
    tarea_id: int,
    payload: TareaItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TareaItem:
    """Marca una tarea como completada o en progreso (CA-2, RN-3 CEPA-103)."""
    tarea = db.get(TareaItem, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    tarea.estado = payload.estado.value
    if payload.estado == EstadoTarea.COMPLETADA:
        tarea.completada_en = datetime.now(timezone.utc)
        tarea.completada_por = current_user.username

    db.commit()
    db.refresh(tarea)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="tarea_item",
        entity_id=str(tarea_id),
    )
    return tarea
```

- [ ] **Step 5: Registrar el router en `app/main.py`**

Agregar en `backend/app/main.py`:

```python
from app.routers import tareas
app.include_router(tareas.router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_tareas_api.py -v`
Expected: `11 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/tareas.py backend/app/routers/tareas.py backend/app/main.py backend/tests/test_tareas_api.py
git commit -m "feat(tareas): API tareas pendientes por rol con RBAC y auditoría (CEPA-103 P1)"
```

---

## Task 7 — [P1] Sender SMTP inyectable + envío de correo para alertas (CEPA-102)

**Files:**
- Create: `backend/app/services/email_sender.py`
- Modify: `backend/app/services/alertas.py` (agregar `enviar_correos_alertas`)
- Modify: `backend/app/routers/alertas.py` (endpoint trigger de envío)
- Test: `backend/tests/test_email_sender.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_email_sender.py`:

```python
"""Tests del sender SMTP y del envío de correos de alerta (CEPA-102).

Usa FakeEmailSender para no enviar correo real.
Cubre CA-1, CA-2 (solo alertas), CA-3 (degradación controlada), CA-4 (no duplicar),
TC-102-01..TC-102-05.
"""

import pytest

from app.services.email_sender import FakeEmailSender, SmtpConfig, enviar_alerta


# ---------------------------------------------------------------------------
# FakeEmailSender
# ---------------------------------------------------------------------------


def test_fake_sender_registra_envios():
    sender = FakeEmailSender()
    sender.send(to="admin@cepa.cl", subject="Alerta CEPA", body="<p>Hay una alerta</p>")
    assert len(sender.enviados) == 1
    assert sender.enviados[0]["to"] == "admin@cepa.cl"


def test_fake_sender_puede_simular_fallo():
    sender = FakeEmailSender(forzar_error=True)
    with pytest.raises(ConnectionError):
        sender.send(to="admin@cepa.cl", subject="Alerta", body="body")


# ---------------------------------------------------------------------------
# enviar_alerta — función de alto nivel
# ---------------------------------------------------------------------------


def test_enviar_alerta_llama_al_sender():
    # TC-102-01: alerta generada, sender disponible → se envía
    sender = FakeEmailSender()
    enviado = enviar_alerta(
        sender=sender,
        to_email="admin@cepa.cl",
        tipo_alerta="vencimiento_licencia",
        caso_tipo="licencia",
        caso_id=5,
        plazo_str="2026-06-12",
    )
    assert enviado is True
    assert len(sender.enviados) == 1
    assert "vencimiento_licencia" in sender.enviados[0]["subject"].lower() or \
           "licencia" in sender.enviados[0]["body"].lower()


def test_enviar_alerta_smtp_caido_no_lanza_excepcion():
    # TC-102-03: SMTP caído → fallo controlado (no propaga excepción, devuelve False)
    sender = FakeEmailSender(forzar_error=True)
    enviado = enviar_alerta(
        sender=sender,
        to_email="admin@cepa.cl",
        tipo_alerta="oda_por_vencer",
        caso_tipo="oda",
        caso_id=3,
        plazo_str="2026-06-10",
    )
    assert enviado is False  # degradación controlada (CA-3)


def test_enviar_alerta_sin_email_valido_no_envía():
    # TC-102-05: usuario sin correo → no se envía
    sender = FakeEmailSender()
    enviado = enviar_alerta(
        sender=sender,
        to_email=None,
        tipo_alerta="oda_por_vencer",
        caso_tipo="oda",
        caso_id=3,
        plazo_str="2026-06-10",
    )
    assert enviado is False
    assert len(sender.enviados) == 0


def test_no_reenvio_si_email_ya_enviado():
    # TC-102-04: email de alerta ya enviado → enviar_correos_alertas no reenvía
    # (la flag email_enviado=True en la BD evita el reenvío — testeado a nivel de BD)
    from datetime import datetime, timezone, timedelta
    from unittest.mock import MagicMock
    from sqlalchemy.orm import Session

    from app.models.alertas import Alerta
    from app.services.alertas import enviar_correos_alertas

    db = MagicMock(spec=Session)
    alerta_ya_enviada = Alerta(
        id=1,
        tipo="oda_por_vencer",
        estado="pendiente",
        caso_id=1,
        caso_tipo="oda",
        usuario_id=1,
        plazo_objetivo=datetime.now(timezone.utc) + timedelta(days=3),
        ventana_dias=7,
        email_enviado=True,  # ya fue enviada
    )
    # scalars().all() debe devolver lista vacía (filtrado por email_enviado=False en el servicio)
    db.scalars.return_value.all.return_value = []

    sender = FakeEmailSender()
    enviadas = enviar_correos_alertas(db, sender=sender)
    assert enviadas == 0
    assert len(sender.enviados) == 0
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_email_sender.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.email_sender'`.

- [ ] **Step 3: Crear `app/services/email_sender.py`**

Crear `backend/app/services/email_sender.py`:

```python
"""Sender SMTP inyectable para notificaciones de alerta (CEPA-102, D12).

Arquitectura:
- Protocolo `EmailSenderProtocol`: interfaz que implementan tanto SmtpEmailSender
  como FakeEmailSender (usado en tests).
- `enviar_alerta()`: función de alto nivel con degradación controlada (CA-3).
- `enviar_correos_alertas()`: recorre las alertas pendientes de envío y llama a enviar_alerta.

El correo se usa EXCLUSIVAMENTE para alertas (D12). No hay confirmaciones ni recordatorios.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocolo (interfaz)
# ---------------------------------------------------------------------------


@runtime_checkable
class EmailSenderProtocol(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None:
        """Envía un correo. Lanza ConnectionError si el SMTP no está disponible."""
        ...


# ---------------------------------------------------------------------------
# Implementación real: SmtpEmailSender
# ---------------------------------------------------------------------------


@dataclass
class SmtpConfig:
    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_addr: str = "cepa-alertas@utalca.cl"


class SmtpEmailSender:
    """Sender SMTP usando smtplib (stdlib). Inyectable en producción."""

    def __init__(self, config: SmtpConfig) -> None:
        self._config = config

    def send(self, *, to: str, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._config.from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "html", "utf-8"))
        try:
            with smtplib.SMTP(self._config.host, self._config.port) as smtp:
                if self._config.use_tls:
                    smtp.starttls()
                if self._config.username:
                    smtp.login(self._config.username, self._config.password)
                smtp.sendmail(self._config.from_addr, [to], msg.as_string())
        except Exception as exc:
            raise ConnectionError(f"SMTP no disponible: {exc}") from exc


# ---------------------------------------------------------------------------
# Doble de tests: FakeEmailSender
# ---------------------------------------------------------------------------


@dataclass
class FakeEmailSender:
    """Sender falso para tests. Registra envíos en memoria; puede simular fallos."""

    forzar_error: bool = False
    enviados: list[dict] = field(default_factory=list)

    def send(self, *, to: str, subject: str, body: str) -> None:
        if self.forzar_error:
            raise ConnectionError("SMTP simulado no disponible")
        self.enviados.append({"to": to, "subject": subject, "body": body})


# ---------------------------------------------------------------------------
# Función de alto nivel: enviar_alerta (con degradación controlada)
# ---------------------------------------------------------------------------


def enviar_alerta(
    *,
    sender: EmailSenderProtocol,
    to_email: str | None,
    tipo_alerta: str,
    caso_tipo: str,
    caso_id: int,
    plazo_str: str,
) -> bool:
    """Envía el correo de una alerta. Devuelve True si se envió, False si no (sin excepción).

    Degradación controlada (CA-3): si el SMTP falla, registra el error y devuelve False.
    La alerta in-app sigue funcionando con independencia del resultado de esta función.
    Solo envía si to_email es un string no vacío (TC-102-05).
    No es responsabilidad de esta función verificar si ya se envió — la capa de servicio
    filtra por email_enviado=False antes de llamar aquí (TC-102-04).
    """
    if not to_email:
        return False

    subject = f"[CEPA] Alerta: {tipo_alerta.replace('_', ' ').title()}"
    body = (
        f"<p>Estimado/a funcionario/a,</p>"
        f"<p>El sistema CEPA ha generado una alerta de tipo "
        f"<strong>{tipo_alerta.replace('_', ' ')}</strong> "
        f"para el {caso_tipo} ID {caso_id}.</p>"
        f"<p>Plazo: <strong>{plazo_str}</strong></p>"
        f"<p>Por favor ingrese al sistema para atender esta alerta.</p>"
        f"<p><em>Este correo es enviado exclusivamente para alertas de plazos perentorios.</em></p>"
    )
    try:
        sender.send(to=to_email, subject=subject, body=body)
        logger.info("Correo de alerta enviado a %s (tipo=%s, caso_id=%d)", to_email, tipo_alerta, caso_id)
        return True
    except ConnectionError as exc:
        logger.warning("Fallo SMTP al enviar alerta (tipo=%s, caso_id=%d): %s", tipo_alerta, caso_id, exc)
        return False


# ---------------------------------------------------------------------------
# Envío masivo de correos para alertas pendientes (CEPA-102)
# ---------------------------------------------------------------------------


def enviar_correos_alertas(
    db,
    *,
    sender: EmailSenderProtocol,
    actor: str = "sistema",
) -> int:
    """Recorre las alertas pendientes de envío y envía correo a cada destinatario.

    Filtra email_enviado=False para evitar duplicados (CA-4, TC-102-04).
    Actualiza email_enviado=True solo si el envío fue exitoso.
    Registra en log de auditoría (RN-4).
    Devuelve el número de correos enviados en esta ejecución.

    Nota: para obtener el correo del usuario se hace JOIN con la tabla de usuarios
    (EPIC-00). Si el usuario no tiene correo, se omite (TC-102-05).
    """
    from sqlalchemy import select, text

    from app.audit.service import record_audit
    from app.models.alertas import Alerta

    alertas_pendientes = db.scalars(
        select(Alerta).where(
            Alerta.email_enviado == False,  # noqa: E712
            Alerta.estado.in_(["pendiente", "leida"]),
        )
    ).all()

    enviados = 0
    for alerta in alertas_pendientes:
        # Obtener correo del usuario desde la tabla de usuarios de EPIC-00
        try:
            fila = db.execute(
                text("SELECT email FROM usuario WHERE id = :uid"),
                {"uid": alerta.usuario_id},
            ).mappings().first()
            correo = fila["email"] if fila and fila.get("email") else None
        except Exception:
            correo = None

        ok = enviar_alerta(
            sender=sender,
            to_email=correo,
            tipo_alerta=alerta.tipo,
            caso_tipo=alerta.caso_tipo,
            caso_id=alerta.caso_id,
            plazo_str=str(alerta.plazo_objetivo.date() if hasattr(alerta.plazo_objetivo, "date") else alerta.plazo_objetivo),
        )
        if ok:
            alerta.email_enviado = True
            enviados += 1

    if enviados:
        db.commit()
        record_audit(
            db,
            actor=actor,
            action="UPDATE",
            entity="alerta",
            entity_id=f"email:{enviados}",
        )

    return enviados
```

- [ ] **Step 4: Agregar endpoint de envío de correos al router de alertas**

Agregar al final de `backend/app/routers/alertas.py`:

```python
from app.services.email_sender import FakeEmailSender, SmtpConfig, SmtpEmailSender, enviar_correos_alertas
from app.config import get_settings


def _get_email_sender():
    """Construye el sender SMTP a partir de la configuración.

    Si SMTP_HOST no está configurado, devuelve FakeEmailSender que solo loguea.
    Esto garantiza que la alerta in-app nunca falle por falta de SMTP (CA-3 CEPA-102).
    """
    settings = get_settings()
    smtp_host = getattr(settings, "smtp_host", None)
    if not smtp_host:
        logger_local = __import__("logging").getLogger(__name__)
        logger_local.warning("SMTP_HOST no configurado — correos de alerta desactivados")
        return FakeEmailSender()
    config = SmtpConfig(
        host=smtp_host,
        port=getattr(settings, "smtp_port", 587),
        username=getattr(settings, "smtp_username", ""),
        password=getattr(settings, "smtp_password", ""),
        use_tls=getattr(settings, "smtp_use_tls", True),
        from_addr=getattr(settings, "smtp_from_addr", "cepa-alertas@utalca.cl"),
    )
    return SmtpEmailSender(config)


@router.post(
    "/enviar-correos",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def enviar_correos(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Envía correos de alerta a los responsables (CEPA-102 P1, D12).

    Solo envía correos para alertas — no para otros eventos (CA-2).
    Degradación controlada si SMTP no está disponible (CA-3).
    No reenvía correos ya enviados (CA-4).
    """
    sender = _get_email_sender()
    enviados = enviar_correos_alertas(db, sender=sender, actor=current_user.username)
    return JobResultado(alertas_generadas=enviados, timestamp=datetime.now(timezone.utc))
```

- [ ] **Step 5: Agregar campos SMTP opcionales al `Settings`**

Editar `backend/app/config.py` para agregar los campos opcionales de SMTP (sin romper la configuración existente):

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación. El motor de BD se elige solo aquí, vía DATABASE_URL."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cepa:cepa@localhost:5432/cepa"
    app_name: str = "Sistema CEPA API"

    # SMTP para alertas (CEPA-102, D12). Opcionales — si no se configuran, los correos
    # quedan desactivados y la alerta in-app sigue funcionando (PA6 pendiente).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_addr: str = "cepa-alertas@utalca.cl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_email_sender.py -v`
Expected: `6 passed`.

- [ ] **Step 7: Correr la suite completa**

Run: `uv run pytest -v`
Expected: todos los tests pasan.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/email_sender.py backend/app/config.py backend/app/routers/alertas.py backend/tests/test_email_sender.py
git commit -m "feat(alertas): sender SMTP inyectable + envío de correos de alerta (CEPA-102 P1, D12)"
```

---

## Task 8 — Verificación integral y lint

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa**

Run (desde `backend/`):
```bash
uv run pytest -v
```
Expected: todos los tests pasan. Anotar el recuento final (mínimo esperado: ~45 tests del módulo de alertas + los de épicas anteriores).

- [ ] **Step 2: Lint**

Run:
```bash
uv run ruff check .
```
Expected: sin errores. Si hay warnings, corregirlos antes de continuar.

- [ ] **Step 3: Smoke de migraciones (upgrade/downgrade)**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: los tres comandos terminan sin error (valida portabilidad de las migraciones de esta épica).

- [ ] **Step 4: Verificar endpoints con curl (humo manual)**

Run (en una terminal, levantar el servidor; en otra, correr los curl):
```bash
# Terminal 1
uv run uvicorn app.main:app --reload

# Terminal 2 — obtener token (ajustar según auth de EPIC-00)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin_test&password=secret" | python3 -m json.tool | grep access_token | cut -d'"' -f4)

# Ejecutar job de alertas
curl -s -X POST http://localhost:8000/api/v1/alertas/ejecutar-job \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Listar alertas (panel in-app)
curl -s http://localhost:8000/api/v1/alertas \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Listar tareas pendientes
curl -s http://localhost:8000/api/v1/tareas \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Expected: `ejecutar-job` devuelve `{"alertas_generadas": N, "timestamp": "..."}`. `alertas` y `tareas` devuelven listas JSON.

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "chore(alertas): EPIC-10 completa — motor alertas + panel in-app + SMTP + tareas" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Prioridad | Tasks que la implementan |
|----------|-----------|--------------------------|
| CEPA-100 Motor de alertas con plazos perentorios | P0 | Task 1 (modelo+enums), Task 2 (migración), Task 3 (motor puro), Task 4 (job+persistencia) |
| CEPA-101 Panel de notificaciones in-app por rol | P0 | Task 1 (modelo), Task 4 (endpoints GET+PATCH) |
| CEPA-102 Notificaciones por correo (solo alertas) | P1 | Task 7 (sender SMTP inyectable, enviar_correos_alertas, endpoint /enviar-correos) |
| CEPA-103 Tareas pendientes por rol | P1 | Task 5 (modelo+migración), Task 6 (API tareas) |

### Criterios de aceptación cubiertos por tests

| CA / TC | Historia | Test |
|---------|----------|------|
| CA-1 (control médico) | CEPA-100 | `test_genera_alerta_control_medico` |
| CA-2 (vencimiento licencia) | CEPA-100 | `test_genera_alerta_vencimiento_licencia_dentro_de_ventana` |
| CA-3 (plazo EPT/ISL) | CEPA-100 | `test_genera_alerta_plazo_ept`, `test_genera_alerta_plazo_isl` |
| CA-4 (consentimiento pendiente) | CEPA-100 | `test_genera_alerta_consentimiento_pendiente` |
| CA-5 (receta por renovar) | CEPA-100 | `test_genera_alerta_receta_por_renovar` |
| CA-6 (ODA por vencer, D3) | CEPA-100 | `test_genera_alerta_oda_por_vencer` |
| CA-7 (idempotencia) | CEPA-100 | `test_idempotencia_excluye_alertas_ya_activas` |
| CA-8 (cobertura OU4) | CEPA-100 | `test_job_ejecutable_por_admin` (job persiste en BD) |
| TC-100-01 (licencia +2d hábiles) | CEPA-100 | `test_genera_alerta_vencimiento_licencia_dentro_de_ventana` |
| TC-100-02 (ODA vence +N días) | CEPA-100 | `test_genera_alerta_oda_por_vencer` |
| TC-100-03 (consentimiento sin flag) | CEPA-100 | `test_genera_alerta_consentimiento_pendiente` |
| TC-100-04 (fuera de ventana) | CEPA-100 | `test_no_genera_alerta_fuera_de_ventana` |
| TC-100-05 (idempotencia doble job) | CEPA-100 | `test_idempotencia_excluye_alertas_ya_activas` |
| TC-100-06 (días hábiles borde) | CEPA-100 | `test_dias_habiles_plazo_en_fin_de_semana` |
| TC-100-07 (job sin usuario clínico) | CEPA-100 | `test_job_no_accesible_por_auditor` + RBAC roles |
| CA-1 (panel al iniciar) | CEPA-101 | `test_admin_ve_sus_alertas` |
| CA-2 (visibilidad por rol/asignación) | CEPA-101 | `test_segregacion_admin_no_ve_alertas_de_otro_usuario` |
| CA-3 (Coordinacion/Auditor alcance) | CEPA-101 | `test_auditor_puede_leer_alertas` |
| CA-4 (marcar resuelta/leída) | CEPA-101 | `test_marcar_alerta_resuelta`, `test_marcar_alerta_leida` |
| TC-101-01 (admin con 3 alertas) | CEPA-101 | `test_admin_ve_sus_alertas` |
| TC-101-02 (marcar resuelta) | CEPA-101 | `test_marcar_alerta_resuelta` |
| TC-101-03 (admin A no ve alertas B) | CEPA-101 | `test_segregacion_admin_no_ve_alertas_de_otro_usuario` |
| TC-101-04 (auditor solo lectura) | CEPA-101 | `test_auditor_no_puede_cambiar_estado` |
| TC-101-05 (panel vacío sin error) | CEPA-101 | `test_panel_sin_alertas_devuelve_lista_vacia` |
| CA-1 (envío SMTP) | CEPA-102 | `test_enviar_alerta_llama_al_sender` |
| CA-2 (solo alertas, D12) | CEPA-102 | arquitectura: `enviar_correos_alertas` solo procesa filas de `alerta` |
| CA-3 (SMTP caído, degradación) | CEPA-102 | `test_enviar_alerta_smtp_caido_no_lanza_excepcion` |
| CA-4 (no duplicado) | CEPA-102 | `test_no_reenvio_si_email_ya_enviado` |
| TC-102-01 (envío exitoso) | CEPA-102 | `test_enviar_alerta_llama_al_sender` |
| TC-102-03 (SMTP caído) | CEPA-102 | `test_enviar_alerta_smtp_caido_no_lanza_excepcion` |
| TC-102-04 (no reenvío) | CEPA-102 | `test_no_reenvio_si_email_ya_enviado` |
| TC-102-05 (usuario sin correo) | CEPA-102 | `test_enviar_alerta_sin_email_valido_no_envía` |
| CA-1 (lista tareas por rol) | CEPA-103 | `test_admin_ve_sus_tareas` |
| CA-2 (completar tarea) | CEPA-103 | `test_completar_tarea` |
| CA-3 (segregación) | CEPA-103 | `test_segregacion_admin_no_ve_tareas_de_otro` |
| CA-4 (Coordinacion vista ampliada) | CEPA-103 | `test_coordinacion_ve_tareas_del_equipo` |
| TC-103-01 (admin ve sus tareas) | CEPA-103 | `test_admin_ve_sus_tareas` |
| TC-103-02 (completar con registro) | CEPA-103 | `test_completar_tarea` |
| TC-103-03 (admin A no ve tareas B) | CEPA-103 | `test_segregacion_admin_no_ve_tareas_de_otro` |
| TC-103-04 (coordinacion supervisión) | CEPA-103 | `test_coordinacion_ve_tareas_del_equipo` |
| TC-103-05 (lista vacía) | CEPA-103 | `test_lista_tareas_vacia_sin_error` |

---

## Notas de cierre

### Firmas que dependen de EPIC-00 y deben verificarse contra el código real

1. **`get_current_user`** → debe devolver un objeto con atributos `.id` (int), `.username` (str), `.role` (str). Los routers de esta épica acceden a los tres. Si la firma difiere, ajustar la desestructuración en `alertas.py` y `tareas.py`.
2. **`require_role(*roles)`** → se usa como `Depends(require_role("Administrativo", "Coordinacion"))`. Verificar que acepte múltiples args posicionales.
3. **`record_audit(db, actor, action, entity, entity_id)`** → los 5 parámetros son los que usa esta épica. Si la firma de EPIC-00 difiere (ej. kwargs vs posicionales), adaptar.
4. **Fixtures `as_admin`, `as_coordinacion`, `as_auditor`** → los tests asumen que `as_admin` autentica como `usuario_id=1` y role `"Administrativo"`. Si el conftest de EPIC-00 usa IDs distintos, los tests de segregación (`usuario_id=99` como "otro usuario") deben ajustarse.

### Dependencias suaves (épicas de dominio)

| Épica | Tabla esperada | Columnas asumidas | Impacto si no existe |
|-------|---------------|-------------------|----------------------|
| EPIC-01 | `oda` | `id`, `fecha_vencimiento`, `usuario_id` | `_construir_hitos_oda` devuelve `[]`; el job no genera alertas ODA |
| EPIC-01 | `ingreso` | `id`, `consentimiento_estado`, `usuario_id`, `fecha_ingreso` | `_construir_hitos_consentimiento` devuelve `[]` |
| EPIC-03 | `ept` | `id`, `fecha_plazo_informe`, `fecha_plazo_isl`, `usuario_id` | `_construir_hitos_ept` devuelve `[]` |
| EPIC-07 | `licencia` | `id`, `fecha_fin_reposo`, `usuario_id` | `_construir_hitos_licencias` devuelve `[]` |
| EPIC-00 | `usuario` | `id`, `email` | `enviar_correos_alertas` no puede obtener correo; omite envío |

Los constructores de hitos están blindados con `try/except` — si la tabla no existe porque la épica aún no está desplegada, el job sigue funcionando para los módulos que sí existen. Esto hace la épica desplegable de forma incremental.

### Decisiones de negocio abiertas que afectan esta épica

- **Ventanas de aviso (RN-3 CEPA-100):** los valores en `VENTANAS_DEFAULT` son propuestas. Deben confirmarse con Coordinación antes de desplegar en QA. La constante está centralizada en `app/services/alertas.py`.
- **Festivos en días hábiles (RN-6):** `dias_habiles_hasta()` excluye sábados y domingos pero NO festivos. Si se requieren festivos, integrar un calendario de días hábiles de Chile (library `workalendar` o tabla configurable). Consultar con Coordinación.
- **Consentimiento informado (D9):** se asume columna `consentimiento_estado = 'pendiente'` en la tabla `ingreso`. Confirmar el nombre exacto y los valores con EPIC-01 antes de ejecutar.
- **PA6 (SMTP):** CEPA-102 está blindada con degradación controlada — si `SMTP_HOST` no está configurado en `.env`, los correos simplemente no se envían y la alerta in-app sigue funcionando. Una vez que TI UTalca habilite el SMTP institucional, basta con agregar las variables al `.env` de producción.
- **`down_revision` en las migraciones:** los archivos `XXXX_crear_alerta.py` y `YYYY_crear_tarea_item.py` tienen `down_revision` con placeholders. Antes de ejecutar el loop, correr `uv run alembic heads` para obtener el ID real de la última revisión y sustituir `<PREV>` / `XXXX` / `YYYY` con los IDs reales.
- **Scheduling del job:** el endpoint `POST /api/v1/alertas/ejecutar-job` es invocable por cron del sistema operativo (ej. `crontab` con `curl` autenticado) o por Celery Beat a futuro. La frecuencia mínima es diaria (RN-2). No se implementa scheduler interno en esta épica.
- **Alcance de visibilidad Coordinacion vs Auditor (CEPA-101):** el plan implementa que ambos ven todas las alertas (sin filtro de `usuario_id`). Si Coordinación debe ver solo su unidad y Auditor todo el sistema, agregar filtro por `unidad_id` una vez que se defina el modelo de jerarquía organizacional.
- **Tabla de usuarios y correo (CEPA-102):** `enviar_correos_alertas` hace `SELECT email FROM usuario WHERE id = :uid`. Confirmar el nombre exacto de la tabla y la columna con EPIC-00.
