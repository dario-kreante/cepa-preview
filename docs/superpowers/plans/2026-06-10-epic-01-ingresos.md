# EPIC-01 — Ingresos y Gestión de Pacientes — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar el módulo raíz del dominio CEPA — paciente, ingreso (con folio), seguimiento clínico, cierre/alta, ODAS con alerta de vencimiento, consentimiento informado y búsqueda 360° — sobre la Fundación FastAPI + SQLAlchemy portable y EPIC-00 (auth/RBAC/auditoría) ya en `main`. Cubre las historias CEPA-010 a CEPA-016 con sus Criterios de Aceptación y Test Cases.

**Architecture:** Se sigue el patrón de la Fundación: modelos en `app/models/<modulo>.py`, schemas Pydantic v2 en `app/schemas/<modulo>.py`, lógica de negocio en `app/services/<modulo>.py`, routers `APIRouter` con prefijo `/api/v1/...` en `app/routers/<modulo>.py`, y una migración Alembic por historia que toque el esquema. El util compartido `app/util/rut.py` (validación dígito verificador módulo 11) lo crea esta épica; el resto de épicas lo importan. Tipos de derivación, estados de caso, tipos de alta y estados de evaluación se modelan como **listas cerradas** validadas en la capa de aplicación (Enums Python + validación Pydantic), no como tipos nativos de motor (regla de portabilidad D15). Toda escritura registra auditoría vía `record_audit` y exige rol `Administrativo`/`Coordinacion`; el `Auditor` accede solo a lectura.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos, `Identity`/`BigInteger`, `DateTime(timezone=True)`), Alembic, Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`; fixtures `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`, `action ∈ {CREATE, UPDATE, DELETE}`.
- Fixtures de test de EPIC-00: `as_admin`, `as_coordinacion`, `as_auditor` (clientes autenticados con headers JWT), `db_session`, `client`.

**Convención de dependencias RBAC usada en los routers de esta épica:**
```python
from app.auth.deps import get_current_user, require_role

# escritura (Administrativo o Coordinacion):
_writer = require_role("Administrativo", "Coordinacion")
# lectura (los tres roles, incluido Auditor):
_reader = require_role("Administrativo", "Coordinacion", "Auditor")
```

---

## Convenciones de modelado de esta épica

- **PK subrogada:** `id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)`.
- **Fechas/tiempos:** `DateTime(timezone=True)` con helper `_utcnow()` (importado del patrón de la Fundación, lo redeclaramos local en cada modelo para evitar acoplamiento — mismo cuerpo `datetime.now(timezone.utc)`).
- **Fechas de calendario sin hora** (fecha de ingreso, fecha de vencimiento de ODA): `Date`.
- **Listas cerradas (D4, D6):** Enums Python `str, Enum`; columna `String(40)`; validación en Pydantic con el Enum. Nunca `CHECK`/tipos enum de motor.
- **Identificadores de tabla/columna:** minúscula y ≤30 caracteres.

Tablas que crea esta épica: `paciente`, `ingreso`, `seguimiento`, `oda`, `consentimiento`.

---

## Task 1: Util compartido `app/util/rut.py` (validación dígito verificador módulo 11)

Lo crea EPIC-01; lo importan todas las épicas. Da soporte a RN-1 de CEPA-010 (RUT obligatorio y validado).

**Files:**
- Create: `backend/app/util/__init__.py` (vacío)
- Create: `backend/app/util/rut.py`
- Test: `backend/tests/test_rut.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_rut.py`:

```python
import pytest

from app.util.rut import RutInvalidoError, formatear_rut, normalizar_rut, validar_rut


def test_rut_valido_con_dv_numerico():
    assert validar_rut("12.345.678-5") is True


def test_rut_valido_con_dv_k():
    # 7.876.543-K es un RUT con dígito verificador K
    assert validar_rut("7.876.543-k") is True
    assert validar_rut("7876543K") is True


def test_rut_invalido_dv_erroneo():
    assert validar_rut("12.345.678-0") is False


def test_rut_invalido_no_numerico():
    assert validar_rut("abc-1") is False
    assert validar_rut("") is False
    assert validar_rut("-5") is False


def test_normalizar_quita_puntos_guion_y_pone_dv_mayuscula():
    assert normalizar_rut("12.345.678-5") == "123456785"
    assert normalizar_rut("7.876.543-k") == "7876543K"


def test_normalizar_rechaza_rut_invalido():
    with pytest.raises(RutInvalidoError):
        normalizar_rut("12.345.678-0")


def test_formatear_agrega_puntos_y_guion():
    assert formatear_rut("123456785") == "12.345.678-5"
    assert formatear_rut("7876543K") == "7.876.543-K"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_rut.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.util.rut'`.

- [ ] **Step 3: Implementar `app/util/rut.py`**

Crear `backend/app/util/__init__.py` vacío.

Crear `backend/app/util/rut.py`:

```python
"""Validación, normalización y formateo de RUT chileno (dígito verificador módulo 11).

Este util lo crea EPIC-01 y lo importan las demás épicas. El RUT normalizado
(sin puntos ni guion, DV en mayúscula) es la forma canónica que se persiste.
"""

import re


class RutInvalidoError(ValueError):
    """Se lanza cuando un RUT no supera la validación de dígito verificador."""


_LIMPIEZA = re.compile(r"[.\-\s]")


def _calcular_dv(cuerpo: str) -> str:
    """Calcula el dígito verificador (módulo 11) de un cuerpo numérico de RUT."""
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def _separar(rut: str) -> tuple[str, str] | None:
    """Devuelve (cuerpo, dv_mayuscula) limpio, o None si el formato es inválido."""
    if not rut:
        return None
    limpio = _LIMPIEZA.sub("", rut).upper()
    if len(limpio) < 2:
        return None
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return None
    if not (dv.isdigit() or dv == "K"):
        return None
    return cuerpo, dv


def validar_rut(rut: str) -> bool:
    """True si el RUT es válido (dígito verificador correcto)."""
    partes = _separar(rut)
    if partes is None:
        return False
    cuerpo, dv = partes
    return _calcular_dv(cuerpo) == dv


def normalizar_rut(rut: str) -> str:
    """Devuelve la forma canónica `<cuerpo><DV>` (sin puntos ni guion, DV en mayúscula).

    Lanza RutInvalidoError si el RUT no es válido.
    """
    partes = _separar(rut)
    if partes is None or _calcular_dv(partes[0]) != partes[1]:
        raise RutInvalidoError(f"RUT inválido: {rut!r}")
    cuerpo, dv = partes
    return f"{cuerpo}{dv}"


def formatear_rut(rut: str) -> str:
    """Devuelve el RUT con puntos de miles y guion: `12.345.678-5`.

    Acepta tanto la forma canónica como una con separadores.
    """
    partes = _separar(rut)
    if partes is None:
        raise RutInvalidoError(f"RUT inválido: {rut!r}")
    cuerpo, dv = partes
    miles = f"{int(cuerpo):,}".replace(",", ".")
    return f"{miles}-{dv}"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_rut.py -v`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/util/ backend/tests/test_rut.py
git commit -m "feat(ingresos): util compartido de RUT (validación módulo 11)"
```

---

## Task 2: Catálogos de dominio (Enums de listas cerradas D4/D6)

Listas cerradas reutilizadas por modelos y schemas: tipos de derivación (D4), tipos de ingreso, estados de caso, tipos de alta, estados de evaluación, estado de consentimiento, sexo.

**Files:**
- Create: `backend/app/domain/__init__.py` (vacío)
- Create: `backend/app/domain/enums.py`
- Test: `backend/tests/test_domain_enums.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_domain_enums.py`:

```python
from app.domain.enums import (
    EstadoCaso,
    EstadoConsentimiento,
    EstadoEvaluacion,
    Sexo,
    TipoAlta,
    TipoDerivacion,
    TipoIngreso,
)


def test_tipos_de_derivacion_son_la_lista_cerrada_v4_d4():
    valores = {d.value for d in TipoDerivacion}
    assert valores == {
        "DIEP",
        "DIAT",
        "PAPT a flujo AT",
        "Reingreso FUMP",
        "Reingreso SUSESO",
        "Convenio U.Clinica",
        "Proyecto",
        "Particular",
        "PAPT",
    }
    # El antiguo convenio SOCORRO ya no es válido (D4)
    assert "SOCORRO" not in valores


def test_estados_de_caso():
    assert {e.value for e in EstadoCaso} == {"activo", "cerrado", "derivado"}


def test_tipos_de_alta_v4_d6():
    assert {t.value for t in TipoAlta} == {
        "terapeutica",
        "medica",
        "psicologica",
        "abandono",
        "derivacion",
    }


def test_estados_de_evaluacion():
    assert {e.value for e in EstadoEvaluacion} == {"realizada", "pendiente", "no_aplica"}


def test_estado_consentimiento():
    assert {e.value for e in EstadoConsentimiento} == {"firmado", "pendiente"}


def test_sexo_y_tipo_ingreso_existen():
    assert "F" in {s.value for s in Sexo}
    assert "M" in {s.value for s in Sexo}
    assert len(list(TipoIngreso)) >= 1
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_domain_enums.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.domain.enums'`.

- [ ] **Step 3: Implementar `app/domain/enums.py`**

Crear `backend/app/domain/__init__.py` vacío.

Crear `backend/app/domain/enums.py`:

```python
"""Listas cerradas del dominio CEPA (Decisiones v4 D4, D6).

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo la portabilidad de BD (no se usan tipos enum nativos del motor).
"""

from enum import Enum


class TipoDerivacion(str, Enum):
    """Tipos de derivación permitidos (v4 D4). 'SOCORRO' ya no es válido."""

    DIEP = "DIEP"
    DIAT = "DIAT"
    PAPT_FLUJO_AT = "PAPT a flujo AT"
    REINGRESO_FUMP = "Reingreso FUMP"
    REINGRESO_SUSESO = "Reingreso SUSESO"
    CONVENIO_U_CLINICA = "Convenio U.Clinica"
    PROYECTO = "Proyecto"
    PARTICULAR = "Particular"
    PAPT = "PAPT"


class TipoIngreso(str, Enum):
    """Tipo de ingreso (v4 D6 / dashboard D5)."""

    CONSULTA_ESPONTANEA = "consulta_espontanea"
    CONVENIO = "convenio"
    PROYECTO = "proyecto"
    PARTICULAR = "particular"


class Sexo(str, Enum):
    F = "F"
    M = "M"
    OTRO = "otro"


class EstadoCaso(str, Enum):
    """Estados de caso válidos (§7.1.3)."""

    ACTIVO = "activo"
    CERRADO = "cerrado"
    DERIVADO = "derivado"


class TipoAlta(str, Enum):
    """Tipos de alta válidos (§7.1.3, v4 D6)."""

    TERAPEUTICA = "terapeutica"
    MEDICA = "medica"
    PSICOLOGICA = "psicologica"
    ABANDONO = "abandono"
    DERIVACION = "derivacion"


class EstadoEvaluacion(str, Enum):
    """Estados de evaluación médica/psicológica (§7.1.2 RN-2)."""

    REALIZADA = "realizada"
    PENDIENTE = "pendiente"
    NO_APLICA = "no_aplica"


class EstadoConsentimiento(str, Enum):
    """Estado del consentimiento informado (CEPA-016 RN-2)."""

    FIRMADO = "firmado"
    PENDIENTE = "pendiente"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_domain_enums.py -v`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/ backend/tests/test_domain_enums.py
git commit -m "feat(ingresos): catálogos de dominio (tipos derivación/alta/estados) D4/D6"
```

---

## Task 3: Modelo `Paciente` + migración

Soporta CEPA-010 (datos del paciente) y CEPA-012 (búsqueda por RUT/nombre). El RUT se persiste normalizado (forma canónica del util de Task 1) y es único por paciente; un paciente puede tener varios ingresos.

**Files:**
- Create: `backend/app/models/paciente.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0010_crear_paciente.py`
- Test: `backend/tests/test_paciente_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_paciente_model.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, String

from app.models.paciente import Paciente


def test_tabla_y_columnas():
    tabla = Paciente.__table__
    assert tabla.name == "paciente"
    assert set(tabla.columns.keys()) == {
        "id",
        "rut",
        "nombre",
        "sexo",
        "edad",
        "region",
        "comuna",
        "telefono",
        "correo",
        "created_at",
        "updated_at",
    }


def test_reglas_portabilidad_identificadores():
    tabla = Paciente.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30


def test_pk_identity_y_tipos():
    cols = Paciente.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["rut"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_rut_es_unico():
    assert Paciente.__table__.columns["rut"].unique is True


def test_default_created_at_utc():
    default = Paciente.__table__.columns["created_at"].default
    valor = default.arg()
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_paciente_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.paciente'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/paciente.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Paciente(Base):
    """Paciente del CEPA. El RUT se guarda normalizado (forma canónica) y es único.

    Un paciente puede tener varios ingresos (reingresos / denuncias distintas).
    """

    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    sexo: Mapped[str] = mapped_column(String(10), nullable=False)
    edad: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    comuna: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingresos: Mapped[list["Ingreso"]] = relationship(  # noqa: F821
        back_populates="paciente", cascade="all, delete-orphan"
    )
```

> Nota: la importación de `Date` se deja preparada para tablas relacionadas; se usa en `ingreso`. Si `ruff` marca import sin uso aquí, retirar `Date` de esta línea (la migración no depende de ello).

Modificar `backend/app/models/__init__.py` para registrar el modelo (añadir la línea, conservando lo existente):

```python
from app.models.paciente import Paciente  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0010_crear_paciente.py`**

```python
"""crear paciente

Revision ID: 0010
Revises: <ULTIMA_REVISION_DE_EPIC_00>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "<ULTIMA_REVISION_DE_EPIC_00>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paciente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("rut", sa.String(length=12), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("sexo", sa.String(length=10), nullable=False),
        sa.Column("edad", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("comuna", sa.String(length=80), nullable=True),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column("correo", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_paciente_rut", "paciente", ["rut"])
    op.create_index("ix_paciente_rut", "paciente", ["rut"])
    op.create_index("ix_paciente_nombre", "paciente", ["nombre"])


def downgrade() -> None:
    op.drop_index("ix_paciente_nombre", table_name="paciente")
    op.drop_index("ix_paciente_rut", table_name="paciente")
    op.drop_constraint("uq_paciente_rut", "paciente", type_="unique")
    op.drop_table("paciente")
```

> **Acción del agente antes de correr:** reemplazar `<ULTIMA_REVISION_DE_EPIC_00>` por la última revisión real en `backend/migrations/versions/` (verificar con `uv run alembic heads`). Si EPIC-00 dejó como head `0001` u otra, ese es el `down_revision`.

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run: `uv run pytest tests/test_paciente_model.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Verificar que la migración aplica (upgrade/downgrade)**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: crea, baja y vuelve a crear `paciente` sin error.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/paciente.py backend/app/models/__init__.py backend/migrations/versions/0010_crear_paciente.py backend/tests/test_paciente_model.py
git commit -m "feat(ingresos): modelo y migración de paciente"
```

---

## Task 4: Modelo `Ingreso` (con folio) + migración

Soporta CEPA-010 (ingreso en formulario único) y CEPA-011 (folio). El folio es único globalmente entre ingresos distintos, salvo reingreso explícito del mismo paciente (se valida en servicio, Task 6). Se guarda `numero_siniestro` para diferenciar reingreso de nueva denuncia (CEPA-011 RN-4).

**Files:**
- Create: `backend/app/models/ingreso.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0011_crear_ingreso.py`
- Test: `backend/tests/test_ingreso_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_ingreso_model.py`:

```python
from sqlalchemy import BigInteger, Boolean, Date, DateTime, String

from app.models.ingreso import Ingreso


def test_tabla_y_columnas():
    tabla = Ingreso.__table__
    assert tabla.name == "ingreso"
    assert set(tabla.columns.keys()) == {
        "id",
        "paciente_id",
        "folio",
        "folio_manual",
        "numero_siniestro",
        "fecha_ingreso",
        "fecha_diep_diat",
        "tipo_derivacion",
        "tipo_ingreso",
        "modelo_tratamiento",
        "diagnostico",
        "razon_social",
        "estado",
        "tipo_alta",
        "fecha_alta",
        "flag_revision",
        "observaciones",
        "tratamiento_iniciado",
        "created_at",
        "updated_at",
    }


def test_portabilidad_identificadores():
    tabla = Ingreso.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30


def test_tipos_y_pk():
    cols = Ingreso.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["folio"].type, String)
    assert isinstance(cols["fecha_ingreso"].type, Date)
    assert isinstance(cols["folio_manual"].type, Boolean)
    assert isinstance(cols["flag_revision"].type, Boolean)
    assert isinstance(cols["tratamiento_iniciado"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_folio_unico_y_fk_paciente():
    tabla = Ingreso.__table__
    assert tabla.columns["folio"].unique is True
    fks = list(tabla.columns["paciente_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "paciente"


def test_estado_no_nullable_default_activo():
    # estado por defecto 'activo' a nivel de modelo
    assert Ingreso.__table__.columns["estado"].nullable is False
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_ingreso_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.ingreso'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/ingreso.py`:

```python
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import EstadoCaso


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ingreso(Base):
    """Ingreso de un paciente al CEPA. Lleva el folio (único entre ingresos distintos).

    El campo `estado` evoluciona activo→cerrado/derivado (CEPA-014). `tipo_alta`,
    `fecha_alta`, `flag_revision` y `observaciones` se completan al cierre.
    """

    __tablename__ = "ingreso"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    paciente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("paciente.id"), nullable=False, index=True
    )
    folio: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    folio_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    numero_siniestro: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_diep_diat: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_derivacion: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo_ingreso: Mapped[str] = mapped_column(String(40), nullable=False)
    modelo_tratamiento: Mapped[str] = mapped_column(String(80), nullable=False)
    diagnostico: Mapped[str] = mapped_column(String(200), nullable=False)
    razon_social: Mapped[str | None] = mapped_column(String(160), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default=EstadoCaso.ACTIVO.value, nullable=False)
    tipo_alta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha_alta: Mapped[date | None] = mapped_column(Date, nullable=True)
    flag_revision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamiento_iniciado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    paciente: Mapped["Paciente"] = relationship(back_populates="ingresos")  # noqa: F821
    seguimiento: Mapped["Seguimiento | None"] = relationship(  # noqa: F821
        back_populates="ingreso", uselist=False, cascade="all, delete-orphan"
    )
    odas: Mapped[list["Oda"]] = relationship(  # noqa: F821
        back_populates="ingreso", cascade="all, delete-orphan"
    )
    consentimiento: Mapped["Consentimiento | None"] = relationship(  # noqa: F821
        back_populates="ingreso", uselist=False, cascade="all, delete-orphan"
    )
```

Modificar `backend/app/models/__init__.py` (añadir línea):

```python
from app.models.ingreso import Ingreso  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0011_crear_ingreso.py`**

```python
"""crear ingreso

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingreso",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("paciente_id", sa.BigInteger(), nullable=False),
        sa.Column("folio", sa.String(length=30), nullable=False),
        sa.Column("folio_manual", sa.Boolean(), nullable=False),
        sa.Column("numero_siniestro", sa.String(length=40), nullable=True),
        sa.Column("fecha_ingreso", sa.Date(), nullable=False),
        sa.Column("fecha_diep_diat", sa.Date(), nullable=True),
        sa.Column("tipo_derivacion", sa.String(length=40), nullable=False),
        sa.Column("tipo_ingreso", sa.String(length=40), nullable=False),
        sa.Column("modelo_tratamiento", sa.String(length=80), nullable=False),
        sa.Column("diagnostico", sa.String(length=200), nullable=False),
        sa.Column("razon_social", sa.String(length=160), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("tipo_alta", sa.String(length=20), nullable=True),
        sa.Column("fecha_alta", sa.Date(), nullable=True),
        sa.Column("flag_revision", sa.Boolean(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("tratamiento_iniciado", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paciente_id"], ["paciente.id"], name="fk_ingreso_paciente"),
    )
    op.create_unique_constraint("uq_ingreso_folio", "ingreso", ["folio"])
    op.create_index("ix_ingreso_folio", "ingreso", ["folio"])
    op.create_index("ix_ingreso_paciente_id", "ingreso", ["paciente_id"])
    op.create_index("ix_ingreso_num_siniestro", "ingreso", ["numero_siniestro"])


def downgrade() -> None:
    op.drop_index("ix_ingreso_num_siniestro", table_name="ingreso")
    op.drop_index("ix_ingreso_paciente_id", table_name="ingreso")
    op.drop_index("ix_ingreso_folio", table_name="ingreso")
    op.drop_constraint("uq_ingreso_folio", "ingreso", type_="unique")
    op.drop_table("ingreso")
```

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run: `uv run pytest tests/test_ingreso_model.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Verificar la migración**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: aplica y revierte `ingreso` sin error.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ingreso.py backend/app/models/__init__.py backend/migrations/versions/0011_crear_ingreso.py backend/tests/test_ingreso_model.py
git commit -m "feat(ingresos): modelo y migración de ingreso (folio único, estado, alta)"
```

---

## Task 5: Generador de folio secuencial (servicio + tabla contador)

Implementa CEPA-011 RN-1/RN-5: folio secuencial automático, único, sin saltos no controlados tras un manual. Se usa una tabla contador `folio_seq` con bloqueo de fila (`with_for_update`) — portable, sin secuencias específicas de motor.

**Files:**
- Create: `backend/app/models/folio_seq.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/__init__.py` (vacío, si no existe)
- Create: `backend/app/services/folio.py`
- Create: `backend/migrations/versions/0012_crear_folio_seq.py`
- Test: `backend/tests/test_folio_service.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_folio_service.py`:

```python
from app.services.folio import folio_existe, siguiente_folio


def test_folios_secuenciales_consecutivos(db_session):
    f1 = siguiente_folio(db_session)
    f2 = siguiente_folio(db_session)
    db_session.flush()
    # mismo año, secuencia +1
    assert f1 != f2
    num1 = int(f1.split("-")[-1])
    num2 = int(f2.split("-")[-1])
    assert num2 == num1 + 1


def test_formato_folio(db_session):
    f = siguiente_folio(db_session)
    # formato F-<anio>-<correlativo de 4+ dígitos>
    partes = f.split("-")
    assert partes[0] == "F"
    assert len(partes[1]) == 4  # año
    assert partes[2].isdigit()


def test_folio_existe_detecta_colision(db_session):
    from app.models.ingreso import Ingreso
    from app.models.paciente import Paciente

    p = Paciente(rut="111111111", nombre="Test", sexo="F", edad=30, region="Maule")
    db_session.add(p)
    db_session.flush()
    ing = Ingreso(
        paciente_id=p.id,
        folio="F-2026-9999",
        folio_manual=True,
        fecha_ingreso=__import__("datetime").date(2026, 6, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="x",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()
    assert folio_existe(db_session, "F-2026-9999") is True
    assert folio_existe(db_session, "F-2026-0001") is False
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_folio_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.folio'`.

- [ ] **Step 3: Implementar el modelo contador**

Crear `backend/app/models/folio_seq.py`:

```python
from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FolioSeq(Base):
    """Contador de folios por año (portable). Una fila por año; se bloquea para incrementar.

    No se usa SERIAL ni secuencias nativas para mantener la portabilidad (D15); el
    correlativo se gestiona en la capa de aplicación con SELECT ... FOR UPDATE.
    """

    __tablename__ = "folio_seq"

    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    ultimo: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
```

Modificar `backend/app/models/__init__.py` (añadir línea):

```python
from app.models.folio_seq import FolioSeq  # noqa: F401
```

- [ ] **Step 4: Implementar el servicio**

Crear `backend/app/services/__init__.py` vacío (si no existe).

Crear `backend/app/services/folio.py`:

```python
"""Generación de folios secuenciales portables (CEPA-011 RN-1/RN-5).

El correlativo se reserva con un SELECT ... FOR UPDATE sobre `folio_seq`,
evitando secuencias específicas de motor. Formato: F-<anio>-<correlativo 4 díg.>.
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.folio_seq import FolioSeq
from app.models.ingreso import Ingreso


def _anio_actual() -> int:
    return datetime.now(timezone.utc).year


def siguiente_folio(db, anio: int | None = None) -> str:
    """Reserva y devuelve el siguiente folio secuencial para el año dado (UTC).

    Bloquea la fila del contador del año para evitar correlativos duplicados bajo
    concurrencia. El caller hace commit junto con el ingreso.
    """
    anio = anio or _anio_actual()
    fila = db.execute(
        select(FolioSeq).where(FolioSeq.anio == anio).with_for_update()
    ).scalar_one_or_none()
    if fila is None:
        fila = FolioSeq(anio=anio, ultimo=0)
        db.add(fila)
        db.flush()
        fila = db.execute(
            select(FolioSeq).where(FolioSeq.anio == anio).with_for_update()
        ).scalar_one()
    fila.ultimo += 1
    db.flush()
    return f"F-{anio}-{fila.ultimo:04d}"


def folio_existe(db, folio: str) -> bool:
    """True si ya existe un ingreso con ese folio."""
    return db.execute(
        select(Ingreso.id).where(Ingreso.folio == folio)
    ).scalar_one_or_none() is not None
```

- [ ] **Step 5: Crear la migración `backend/migrations/versions/0012_crear_folio_seq.py`**

```python
"""crear folio_seq

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "folio_seq",
        sa.Column("anio", sa.Integer(), primary_key=True),
        sa.Column("ultimo", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("folio_seq")
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_folio_service.py -v
```
Expected: migración aplica; `3 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/folio_seq.py backend/app/models/__init__.py backend/app/services/ backend/migrations/versions/0012_crear_folio_seq.py backend/tests/test_folio_service.py
git commit -m "feat(ingresos): generador de folio secuencial portable (FOR UPDATE)"
```

---

## Task 6: Servicio y API de ingreso — crear (CEPA-010 + CEPA-011)

Endpoint `POST /api/v1/ingresos` que: valida RUT (RN-1), exige campos obligatorios (RN-2/D6) vía Pydantic, valida tipo de derivación como lista cerrada (RN-6/D4), crea o reutiliza paciente por RUT (RN-3), genera folio automático o acepta manual con validación de colisión (CEPA-011 RN-1/RN-2/RN-3), registra auditoría, y exige rol escritor (Auditor → 403).

**Files:**
- Create: `backend/app/schemas/ingreso.py`
- Create: `backend/app/services/ingreso.py`
- Create: `backend/app/routers/ingresos.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ingreso_crear_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_ingreso_crear_api.py`:

```python
def _payload(**over):
    base = {
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
    }
    base.update(over)
    return base


# TC-010-01
def test_crear_ingreso_genera_folio_y_es_buscable(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload())
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["folio"].startswith("F-")
    assert cuerpo["estado"] == "activo"
    # visible de inmediato en búsqueda por RUT
    b = as_admin.get("/api/v1/pacientes/buscar", params={"q": "12.345.678-5"})
    assert b.status_code == 200
    assert any(p["rut"] == "123456785" for p in b.json())


# TC-010-02: RUT ya existente reutiliza paciente y crea nuevo ingreso
def test_rut_existente_reutiliza_paciente(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(numero_siniestro="S-1"))
    r2 = as_admin.post(
        "/api/v1/ingresos",
        json=_payload(numero_siniestro="S-2", nombre="Juan Pérez Actualizado"),
    )
    assert r2.status_code == 201
    # un solo paciente con ese RUT
    b = as_admin.get("/api/v1/pacientes/buscar", params={"q": "123456785"})
    assert len([p for p in b.json() if p["rut"] == "123456785"]) == 1


# TC-010-03: RUT inválido -> 422, sin crear nada
def test_rut_invalido_rechazado(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(rut="12.345.678-0"))
    assert r.status_code == 422
    assert "rut" in r.text.lower()


# TC-010-04: faltan obligatorios -> 422
def test_campos_obligatorios_faltantes(as_admin):
    incompleto = _payload()
    del incompleto["sexo"]
    del incompleto["diagnostico"]
    r = as_admin.post("/api/v1/ingresos", json=incompleto)
    assert r.status_code == 422


# TC-010-05: tipo de derivación fuera de lista cerrada -> 422
def test_tipo_derivacion_invalido(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload(tipo_derivacion="SOCORRO"))
    assert r.status_code == 422


# TC-010-06 / TC-011-06: Auditor no puede crear (solo lectura) -> 403
def test_auditor_no_puede_crear(as_auditor):
    r = as_auditor.post("/api/v1/ingresos", json=_payload())
    assert r.status_code == 403


# TC-011-01: sin folio -> secuencial automático
def test_folio_automatico_cuando_no_se_indica(as_admin):
    r = as_admin.post("/api/v1/ingresos", json=_payload())
    assert r.json()["folio_manual"] is False


# TC-011-02: reingreso con folio manual del mismo paciente (nuevo siniestro)
def test_reingreso_folio_manual_mismo_paciente(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(folio="F-001", numero_siniestro="S-1"))
    r2 = as_admin.post(
        "/api/v1/ingresos",
        json=_payload(folio="F-001", numero_siniestro="S-1", es_reingreso=True),
    )
    assert r2.status_code == 201
    assert r2.json()["folio"] == "F-001"
    assert r2.json()["folio_manual"] is True


# TC-011-04: folio manual colisiona con otro paciente -> 409
def test_folio_manual_colision_otro_paciente(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(rut="12.345.678-5", folio="F-100"))
    r = as_admin.post(
        "/api/v1/ingresos",
        json=_payload(rut="7.876.543-K", nombre="Otra Persona", folio="F-100"),
    )
    assert r.status_code == 409
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_ingreso_crear_api.py -v`
Expected: FAIL con `404` (ruta inexistente) o `ModuleNotFoundError`.

- [ ] **Step 3: Implementar los schemas**

Crear `backend/app/schemas/ingreso.py`:

```python
from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.enums import (
    EstadoCaso,
    Sexo,
    TipoAlta,
    TipoDerivacion,
    TipoIngreso,
)
from app.util.rut import RutInvalidoError, normalizar_rut


class IngresoCreate(BaseModel):
    """Alta de ingreso en formulario único (CEPA-010). Campos obligatorios = D6."""

    rut: str
    nombre: str
    sexo: Sexo
    edad: int
    region: str
    diagnostico: str
    tipo_derivacion: TipoDerivacion
    tipo_ingreso: TipoIngreso
    modelo_tratamiento: str
    fecha_ingreso: date
    # opcionales
    comuna: str | None = None
    telefono: str | None = None
    correo: str | None = None
    fecha_diep_diat: date | None = None
    razon_social: str | None = None
    numero_siniestro: str | None = None
    # folio manual (CEPA-011)
    folio: str | None = None
    es_reingreso: bool = False

    @field_validator("rut")
    @classmethod
    def _rut_valido(cls, v: str) -> str:
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v}") from exc

    @field_validator("edad")
    @classmethod
    def _edad_positiva(cls, v: int) -> int:
        if v <= 0 or v > 130:
            raise ValueError("edad fuera de rango")
        return v


class PacienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rut: str
    nombre: str
    sexo: str
    edad: int
    region: str
    comuna: str | None
    telefono: str | None
    correo: str | None


class IngresoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    folio: str
    folio_manual: bool
    numero_siniestro: str | None
    fecha_ingreso: date
    fecha_diep_diat: date | None
    tipo_derivacion: TipoDerivacion
    tipo_ingreso: TipoIngreso
    modelo_tratamiento: str
    diagnostico: str
    razon_social: str | None
    estado: EstadoCaso
    tipo_alta: TipoAlta | None
    fecha_alta: date | None
    flag_revision: bool
    observaciones: str | None
    tratamiento_iniciado: bool
```

- [ ] **Step 4: Implementar el servicio**

Crear `backend/app/services/ingreso.py`:

```python
"""Lógica de creación de ingresos (CEPA-010 + CEPA-011)."""

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.ingreso import IngresoCreate
from app.services.folio import folio_existe, siguiente_folio


def _obtener_o_crear_paciente(db, data: IngresoCreate) -> Paciente:
    """Reutiliza el paciente si el RUT ya existe (RN-3); si no, lo crea.

    Si existe, actualiza los datos de contacto/demográficos con lo enviado
    (confirmar/actualizar del formulario).
    """
    paciente = db.execute(
        select(Paciente).where(Paciente.rut == data.rut)
    ).scalar_one_or_none()
    if paciente is None:
        paciente = Paciente(
            rut=data.rut,
            nombre=data.nombre,
            sexo=data.sexo.value,
            edad=data.edad,
            region=data.region,
            comuna=data.comuna,
            telefono=data.telefono,
            correo=data.correo,
        )
        db.add(paciente)
        db.flush()
        return paciente
    # actualizar datos del paciente existente
    paciente.nombre = data.nombre
    paciente.sexo = data.sexo.value
    paciente.edad = data.edad
    paciente.region = data.region
    paciente.comuna = data.comuna
    paciente.telefono = data.telefono
    paciente.correo = data.correo
    db.flush()
    return paciente


def _resolver_folio(db, data: IngresoCreate, paciente: Paciente) -> tuple[str, bool]:
    """Devuelve (folio, folio_manual).

    - Sin folio: secuencial automático (RN-1).
    - Con folio manual: válido si no colisiona, salvo reingreso explícito del mismo
      paciente (RN-2/RN-3). Una colisión con otro paciente -> 409.
    """
    if data.folio is None:
        return siguiente_folio(db), False

    if folio_existe(db, data.folio):
        existente = db.execute(
            select(Ingreso).where(Ingreso.folio == data.folio)
        ).scalar_one()
        es_reingreso_valido = data.es_reingreso and existente.paciente_id == paciente.id
        if not es_reingreso_valido:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El folio {data.folio} ya está emitido para otro ingreso.",
            )
        # reingreso válido: se permite reutilizar el folio en el nuevo ingreso
    return data.folio, True


def crear_ingreso(db, data: IngresoCreate) -> Ingreso:
    paciente = _obtener_o_crear_paciente(db, data)
    folio, folio_manual = _resolver_folio(db, data, paciente)
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio=folio,
        folio_manual=folio_manual,
        numero_siniestro=data.numero_siniestro,
        fecha_ingreso=data.fecha_ingreso,
        fecha_diep_diat=data.fecha_diep_diat,
        tipo_derivacion=data.tipo_derivacion.value,
        tipo_ingreso=data.tipo_ingreso.value,
        modelo_tratamiento=data.modelo_tratamiento,
        diagnostico=data.diagnostico,
        razon_social=data.razon_social,
    )
    db.add(ingreso)
    db.flush()
    return ingreso
```

- [ ] **Step 5: Implementar el router**

Crear `backend/app/routers/ingresos.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.ingreso import IngresoCreate, IngresoRead
from app.services.ingreso import crear_ingreso

router = APIRouter(prefix="/api/v1/ingresos", tags=["ingresos"])

_writer = require_role("Administrativo", "Coordinacion")


@router.post(
    "",
    response_model=IngresoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: IngresoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = crear_ingreso(db, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso
```

- [ ] **Step 6: Conectar el router en `app/main.py`**

Añadir el import y el `include_router` (conservando lo existente de la Fundación/EPIC-00):

```python
from app.routers import ingresos

app.include_router(ingresos.router)
```

> Nota: el endpoint `GET /api/v1/pacientes/buscar` usado por los tests TC-010-01/02 se implementa en la Task 7. Hasta entonces, esos asserts de búsqueda fallarán; ejecutar la suite de esta Task con `-k "not buscable and not reutiliza_paciente"` para validar el alta aisladamente, y dejar los dos tests de búsqueda activos una vez completada la Task 7.

- [ ] **Step 7: Correr el test y verificar que pasa (alta sin búsqueda)**

Run: `uv run pytest tests/test_ingreso_crear_api.py -v -k "not buscable and not reutiliza_paciente"`
Expected: pasan los tests de RUT inválido, obligatorios, derivación inválida, Auditor 403, folio automático, reingreso manual y colisión 409.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/ingreso.py backend/app/services/ingreso.py backend/app/routers/ingresos.py backend/app/main.py backend/tests/test_ingreso_crear_api.py
git commit -m "feat(ingresos): alta de ingreso (RUT, obligatorios, folio auto/manual, RBAC, auditoría)"
```

---

## Task 7: Búsqueda 360° del paciente (CEPA-012)

Endpoints de búsqueda por RUT/nombre/folio (`GET /api/v1/pacientes/buscar`) y vista consolidada (`GET /api/v1/pacientes/{id}/vista-360`). La vista consolida ingresos y deja "ranuras" para las dimensiones de otras épicas (fármacos, licencias, controles, reintegro) como listas vacías por ahora, vinculadas por folio/RUT cuando esas épicas existan. Lectura abierta a los tres roles (incluido Auditor, RN-4).

**Files:**
- Create: `backend/app/schemas/busqueda.py`
- Create: `backend/app/services/busqueda.py`
- Create: `backend/app/routers/pacientes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_busqueda_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_busqueda_api.py`:

```python
def _payload(**over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-10",
    }
    base.update(over)
    return base


# TC-012-01: buscar por RUT
def test_buscar_por_rut(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload())
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "11.111.111-1"})
    assert r.status_code == 200
    assert any(p["rut"] == "111111111" for p in r.json())


# TC-012-02: buscar por folio
def test_buscar_por_folio(as_admin):
    creado = as_admin.post("/api/v1/ingresos", json=_payload(folio="F-555")).json()
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "F-555"})
    assert r.status_code == 200
    assert any(p["id"] == creado["paciente_id"] for p in r.json())


# TC-012-04: sin coincidencias -> lista vacía, sin error
def test_buscar_sin_resultados(as_admin):
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "99.999.999-9"})
    assert r.status_code == 200
    assert r.json() == []


# TC-012-05: nombre parcial con coincidencias múltiples
def test_buscar_por_nombre_parcial(as_admin):
    as_admin.post("/api/v1/ingresos", json=_payload(rut="11.111.111-1", nombre="Ana González"))
    as_admin.post("/api/v1/ingresos", json=_payload(rut="7.876.543-K", nombre="Pedro González"))
    r = as_admin.get("/api/v1/pacientes/buscar", params={"q": "González"})
    assert r.status_code == 200
    nombres = {p["nombre"] for p in r.json()}
    assert {"Ana González", "Pedro González"} <= nombres


# CA-1: vista 360 consolida dimensiones
def test_vista_360_consolida(as_admin):
    creado = as_admin.post("/api/v1/ingresos", json=_payload()).json()
    r = as_admin.get(f"/api/v1/pacientes/{creado['paciente_id']}/vista-360")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["paciente"]["rut"] == "111111111"
    assert len(cuerpo["ingresos"]) == 1
    # ranuras de otras épicas presentes (aún vacías)
    for dim in ("farmacos", "licencias", "controles", "reintegro"):
        assert cuerpo[dim] == []


# CA-3: vista 360 de paciente inexistente -> 404
def test_vista_360_inexistente(as_admin):
    r = as_admin.get("/api/v1/pacientes/999999/vista-360")
    assert r.status_code == 404


# TC-012-06: Auditor accede a búsqueda y vista (solo lectura)
def test_auditor_puede_leer(as_admin, as_auditor):
    creado = as_admin.post("/api/v1/ingresos", json=_payload()).json()
    assert as_auditor.get("/api/v1/pacientes/buscar", params={"q": "111111111"}).status_code == 200
    assert as_auditor.get(f"/api/v1/pacientes/{creado['paciente_id']}/vista-360").status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_busqueda_api.py -v`
Expected: FAIL con `404` (rutas inexistentes).

- [ ] **Step 3: Implementar los schemas**

Crear `backend/app/schemas/busqueda.py`:

```python
from typing import Any

from pydantic import BaseModel

from app.schemas.ingreso import IngresoRead, PacienteRead


class Vista360(BaseModel):
    """Estado consolidado del paciente (CEPA-012).

    `ingresos` ya se llena en EPIC-01. Las demás dimensiones son ranuras que las
    épicas de Oleada 3 (Fármacos, Licencias, Controles, Reintegro) poblarán por
    folio/RUT; hoy se devuelven como listas vacías.
    """

    paciente: PacienteRead
    ingresos: list[IngresoRead]
    farmacos: list[Any] = []
    licencias: list[Any] = []
    controles: list[Any] = []
    reintegro: list[Any] = []
```

- [ ] **Step 4: Implementar el servicio**

Crear `backend/app/services/busqueda.py`:

```python
"""Búsqueda 360° de pacientes (CEPA-012).

Criterios: RUT (normalizado), nombre (parcial, case-insensitive) y folio. La
búsqueda nunca lanza error por término inexistente: devuelve lista vacía (RN-5).
"""

from sqlalchemy import func, select

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.util.rut import RutInvalidoError, normalizar_rut


def buscar_pacientes(db, q: str) -> list[Paciente]:
    """Devuelve pacientes que matchean por RUT exacto, nombre parcial o folio."""
    q = (q or "").strip()
    if not q:
        return []
    ids: set[int] = set()

    # 1) por RUT (si el término normaliza a un RUT válido)
    try:
        rut_norm = normalizar_rut(q)
        for p in db.execute(select(Paciente).where(Paciente.rut == rut_norm)).scalars():
            ids.add(p.id)
    except RutInvalidoError:
        pass

    # 2) por folio exacto -> paciente del ingreso
    for ing in db.execute(select(Ingreso).where(Ingreso.folio == q)).scalars():
        ids.add(ing.paciente_id)

    # 3) por nombre parcial (case-insensitive, portable con lower())
    patron = f"%{q.lower()}%"
    for p in db.execute(
        select(Paciente).where(func.lower(Paciente.nombre).like(patron))
    ).scalars():
        ids.add(p.id)

    if not ids:
        return []
    return list(
        db.execute(
            select(Paciente).where(Paciente.id.in_(ids)).order_by(Paciente.nombre)
        ).scalars()
    )


def obtener_paciente(db, paciente_id: int) -> Paciente | None:
    return db.get(Paciente, paciente_id)


def vista_360(db, paciente: Paciente) -> dict:
    """Consolida los ingresos del paciente. Otras dimensiones quedan como ranuras."""
    ingresos = list(
        db.execute(
            select(Ingreso).where(Ingreso.paciente_id == paciente.id).order_by(Ingreso.id)
        ).scalars()
    )
    return {
        "paciente": paciente,
        "ingresos": ingresos,
        "farmacos": [],
        "licencias": [],
        "controles": [],
        "reintegro": [],
    }
```

- [ ] **Step 5: Implementar el router**

Crear `backend/app/routers/pacientes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.busqueda import Vista360
from app.schemas.ingreso import PacienteRead
from app.services.busqueda import buscar_pacientes, obtener_paciente, vista_360

router = APIRouter(prefix="/api/v1/pacientes", tags=["pacientes"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get("/buscar", response_model=list[PacienteRead], dependencies=[Depends(_reader)])
def buscar(q: str, db: Session = Depends(get_db)) -> list[PacienteRead]:
    return buscar_pacientes(db, q)


@router.get("/{paciente_id}/vista-360", response_model=Vista360, dependencies=[Depends(_reader)])
def vista_360_endpoint(paciente_id: int, db: Session = Depends(get_db)) -> Vista360:
    paciente = obtener_paciente(db, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return vista_360(db, paciente)
```

- [ ] **Step 6: Conectar el router en `app/main.py`**

```python
from app.routers import pacientes

app.include_router(pacientes.router)
```

- [ ] **Step 7: Correr la suite de búsqueda y la de alta (ya completa)**

Run:
```bash
uv run pytest tests/test_busqueda_api.py tests/test_ingreso_crear_api.py -v
```
Expected: ambas suites en verde (incluidos ahora los dos tests de búsqueda de la Task 6).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/busqueda.py backend/app/services/busqueda.py backend/app/routers/pacientes.py backend/app/main.py backend/tests/test_busqueda_api.py
git commit -m "feat(ingresos): búsqueda 360 por RUT/nombre/folio + vista consolidada (CEPA-012)"
```

---

## Task 8: Seguimiento del proceso clínico + validador de plazos (CEPA-013)

Modelo `seguimiento` (1:1 con ingreso), tabla `plazo_programa` para el validador (D10) y endpoint `PUT /api/v1/ingresos/{id}/seguimiento`. Hitos: primera acogida, estados de evaluación médica/psicológica, obstaculización, plazo/fecha de informe, RECA EP/EC. El validador calcula "en plazo"/"fuera de plazo" comparando la fecha de evaluación contra el plazo del programa.

**Files:**
- Create: `backend/app/models/seguimiento.py`
- Create: `backend/app/models/plazo_programa.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/seguimiento.py`
- Create: `backend/app/services/seguimiento.py`
- Modify: `backend/app/routers/ingresos.py`
- Create: `backend/migrations/versions/0013_crear_seguimiento.py`
- Test: `backend/tests/test_seguimiento_model.py`
- Test: `backend/tests/test_seguimiento_api.py`

- [ ] **Step 1: Escribir el test de modelo que falla**

Crear `backend/tests/test_seguimiento_model.py`:

```python
from sqlalchemy import Boolean, Date, String

from app.models.plazo_programa import PlazoPrograma
from app.models.seguimiento import Seguimiento


def test_columnas_seguimiento():
    cols = set(Seguimiento.__table__.columns.keys())
    assert cols == {
        "id",
        "ingreso_id",
        "fecha_acogida",
        "programa",
        "eval_medica_estado",
        "eval_medica_medico",
        "eval_medica_fecha",
        "eval_psico_estado",
        "eval_psico_psicologo",
        "eval_psico_fecha",
        "obstaculizacion",
        "plazo_informe",
        "fecha_envio_informe",
        "reca_ep_ec",
        "created_at",
        "updated_at",
    }


def test_portabilidad_y_tipos_seguimiento():
    tabla = Seguimiento.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30
    assert isinstance(tabla.columns["eval_medica_estado"].type, String)
    assert isinstance(tabla.columns["fecha_acogida"].type, Date)
    assert isinstance(tabla.columns["obstaculizacion"].type, Boolean)


def test_fk_ingreso_unica():
    cols = Seguimiento.__table__.columns
    assert cols["ingreso_id"].unique is True  # 1:1 con ingreso
    fks = list(cols["ingreso_id"].foreign_keys)
    assert fks[0].column.table.name == "ingreso"


def test_plazo_programa_columnas():
    assert set(PlazoPrograma.__table__.columns.keys()) == {"programa", "dias_plazo_informe"}
```

- [ ] **Step 2: Correr y ver fallar**

Run: `uv run pytest tests/test_seguimiento_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.seguimiento'`.

- [ ] **Step 3: Implementar los modelos**

Crear `backend/app/models/plazo_programa.py`:

```python
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlazoPrograma(Base):
    """Plazo (en días) para el informe de evaluación por programa (v4 D10)."""

    __tablename__ = "plazo_programa"

    programa: Mapped[str] = mapped_column(String(80), primary_key=True)
    dias_plazo_informe: Mapped[int] = mapped_column(Integer, nullable=False)
```

Crear `backend/app/models/seguimiento.py`:

```python
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Seguimiento(Base):
    """Hitos del proceso clínico de un ingreso (§7.1.2). 1:1 con `ingreso`."""

    __tablename__ = "seguimiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), unique=True, nullable=False
    )
    fecha_acogida: Mapped[date | None] = mapped_column(Date, nullable=True)
    programa: Mapped[str | None] = mapped_column(String(80), nullable=True)
    eval_medica_estado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    eval_medica_medico: Mapped[str | None] = mapped_column(String(120), nullable=True)
    eval_medica_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    eval_psico_estado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    eval_psico_psicologo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    eval_psico_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    obstaculizacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    plazo_informe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_envio_informe: Mapped[date | None] = mapped_column(Date, nullable=True)
    reca_ep_ec: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="seguimiento")  # noqa: F821
```

Modificar `backend/app/models/__init__.py` (añadir líneas):

```python
from app.models.plazo_programa import PlazoPrograma  # noqa: F401
from app.models.seguimiento import Seguimiento  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0013_crear_seguimiento.py`**

```python
"""crear seguimiento y plazo_programa

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plazo_programa",
        sa.Column("programa", sa.String(length=80), primary_key=True),
        sa.Column("dias_plazo_informe", sa.Integer(), nullable=False),
    )
    op.create_table(
        "seguimiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_acogida", sa.Date(), nullable=True),
        sa.Column("programa", sa.String(length=80), nullable=True),
        sa.Column("eval_medica_estado", sa.String(length=20), nullable=True),
        sa.Column("eval_medica_medico", sa.String(length=120), nullable=True),
        sa.Column("eval_medica_fecha", sa.Date(), nullable=True),
        sa.Column("eval_psico_estado", sa.String(length=20), nullable=True),
        sa.Column("eval_psico_psicologo", sa.String(length=120), nullable=True),
        sa.Column("eval_psico_fecha", sa.Date(), nullable=True),
        sa.Column("obstaculizacion", sa.Boolean(), nullable=False),
        sa.Column("plazo_informe", sa.Integer(), nullable=True),
        sa.Column("fecha_envio_informe", sa.Date(), nullable=True),
        sa.Column("reca_ep_ec", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingreso_id"], ["ingreso.id"], name="fk_seguimiento_ingreso"),
    )
    op.create_unique_constraint("uq_seguimiento_ingreso", "seguimiento", ["ingreso_id"])


def downgrade() -> None:
    op.drop_constraint("uq_seguimiento_ingreso", "seguimiento", type_="unique")
    op.drop_table("seguimiento")
    op.drop_table("plazo_programa")
```

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_seguimiento_model.py -v
```
Expected: migración aplica; `4 passed`.

- [ ] **Step 6: Escribir el test de API que falla**

Crear `backend/tests/test_seguimiento_api.py`:

```python
def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


def _set_plazo(db_session, programa="PROG-A", dias=10):
    from app.models.plazo_programa import PlazoPrograma

    db_session.merge(PlazoPrograma(programa=programa, dias_plazo_informe=dias))
    db_session.commit()


# TC-013-01: acogida + consentimiento (estado de consentimiento vive en CEPA-016; aquí acogida)
def test_registrar_acogida(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"fecha_acogida": "2026-06-02", "programa": "PROG-A"},
    )
    assert r.status_code == 200
    assert r.json()["fecha_acogida"] == "2026-06-02"


# TC-013-02: evaluaciones con estados
def test_registrar_evaluaciones(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={
            "programa": "PROG-A",
            "eval_medica_estado": "realizada",
            "eval_medica_medico": "Dr. Soto",
            "eval_medica_fecha": "2026-06-05",
            "eval_psico_estado": "pendiente",
        },
    )
    assert r.status_code == 200
    assert r.json()["eval_medica_estado"] == "realizada"


# TC-013-03: evaluación dentro de plazo -> validador "en_plazo"
def test_validador_en_plazo(as_admin, db_session):
    _set_plazo(db_session, "PROG-A", dias=10)
    ing = _ingreso(as_admin, fecha_ingreso="2026-06-01")
    as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"programa": "PROG-A", "eval_medica_estado": "realizada", "eval_medica_fecha": "2026-06-05"},
    )
    r = as_admin.get(f"/api/v1/ingresos/{ing['id']}/seguimiento/validacion-plazo")
    assert r.status_code == 200
    assert r.json()["cumplimiento"] == "en_plazo"


# TC-013-04: evaluación fuera de plazo -> "fuera_de_plazo"
def test_validador_fuera_de_plazo(as_admin, db_session):
    _set_plazo(db_session, "PROG-B", dias=3)
    ing = _ingreso(as_admin, rut="7.876.543-K", fecha_ingreso="2026-06-01")
    as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"programa": "PROG-B", "eval_medica_estado": "realizada", "eval_medica_fecha": "2026-06-20"},
    )
    r = as_admin.get(f"/api/v1/ingresos/{ing['id']}/seguimiento/validacion-plazo")
    assert r.json()["cumplimiento"] == "fuera_de_plazo"


# TC-013-05: estado "no_aplica" no exige médico/diagnóstico
def test_no_aplica_sin_medico(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"eval_medica_estado": "no_aplica"},
    )
    assert r.status_code == 200


# borde: estado de evaluación inválido -> 422
def test_estado_evaluacion_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento",
        json={"eval_medica_estado": "quizas"},
    )
    assert r.status_code == 422


# TC-013-06: Auditor no puede editar seguimiento -> 403
def test_auditor_no_edita_seguimiento(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = as_auditor.put(
        f"/api/v1/ingresos/{ing['id']}/seguimiento", json={"fecha_acogida": "2026-06-02"}
    )
    assert r.status_code == 403
```

- [ ] **Step 7: Correr y ver fallar**

Run: `uv run pytest tests/test_seguimiento_api.py -v`
Expected: FAIL con `404` (rutas inexistentes).

- [ ] **Step 8: Implementar schemas**

Crear `backend/app/schemas/seguimiento.py`:

```python
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.enums import EstadoEvaluacion


class SeguimientoUpdate(BaseModel):
    """Actualización parcial de hitos del seguimiento (§7.1.2). Todos opcionales."""

    fecha_acogida: date | None = None
    programa: str | None = None
    eval_medica_estado: EstadoEvaluacion | None = None
    eval_medica_medico: str | None = None
    eval_medica_fecha: date | None = None
    eval_psico_estado: EstadoEvaluacion | None = None
    eval_psico_psicologo: str | None = None
    eval_psico_fecha: date | None = None
    obstaculizacion: bool | None = None
    plazo_informe: int | None = None
    fecha_envio_informe: date | None = None
    reca_ep_ec: str | None = None


class SeguimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    fecha_acogida: date | None
    programa: str | None
    eval_medica_estado: EstadoEvaluacion | None
    eval_medica_medico: str | None
    eval_medica_fecha: date | None
    eval_psico_estado: EstadoEvaluacion | None
    eval_psico_psicologo: str | None
    eval_psico_fecha: date | None
    obstaculizacion: bool
    plazo_informe: int | None
    fecha_envio_informe: date | None
    reca_ep_ec: str | None


class ValidacionPlazo(BaseModel):
    cumplimiento: str  # "en_plazo" | "fuera_de_plazo" | "sin_datos"
    detalle: str
```

- [ ] **Step 9: Implementar el servicio**

Crear `backend/app/services/seguimiento.py`:

```python
"""Seguimiento del proceso clínico y validador de plazos por programa (CEPA-013, D10)."""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.ingreso import Ingreso
from app.models.plazo_programa import PlazoPrograma
from app.models.seguimiento import Seguimiento
from app.schemas.seguimiento import SeguimientoUpdate


def _obtener_ingreso(db, ingreso_id: int) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    return ingreso


def upsert_seguimiento(db, ingreso_id: int, data: SeguimientoUpdate) -> Seguimiento:
    """Crea o actualiza (parcialmente) el seguimiento del ingreso."""
    _obtener_ingreso(db, ingreso_id)
    seg = db.execute(
        select(Seguimiento).where(Seguimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if seg is None:
        seg = Seguimiento(ingreso_id=ingreso_id)
        db.add(seg)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        # los Enum se persisten como su .value
        if hasattr(valor, "value"):
            valor = valor.value
        setattr(seg, campo, valor)
    db.flush()
    return seg


def validar_plazo(db, ingreso_id: int) -> dict:
    """Compara la fecha de la evaluación (la más temprana realizada) contra el plazo
    del programa, medido desde la fecha de ingreso (D10).

    Devuelve cumplimiento: en_plazo / fuera_de_plazo / sin_datos.
    """
    ingreso = _obtener_ingreso(db, ingreso_id)
    seg = db.execute(
        select(Seguimiento).where(Seguimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if seg is None or seg.programa is None:
        return {"cumplimiento": "sin_datos", "detalle": "No hay seguimiento o programa definido."}

    plazo = db.get(PlazoPrograma, seg.programa)
    if plazo is None:
        return {"cumplimiento": "sin_datos", "detalle": f"Programa {seg.programa} sin plazo configurado."}

    fechas = [f for f in (seg.eval_medica_fecha, seg.eval_psico_fecha) if f is not None]
    if not fechas:
        return {"cumplimiento": "sin_datos", "detalle": "No hay fecha de evaluación registrada."}

    fecha_eval = max(fechas)  # la última evaluación define el cumplimiento
    limite = ingreso.fecha_ingreso + timedelta(days=plazo.dias_plazo_informe)
    if fecha_eval <= limite:
        return {"cumplimiento": "en_plazo", "detalle": f"Evaluación al {fecha_eval} (límite {limite})."}
    return {"cumplimiento": "fuera_de_plazo", "detalle": f"Evaluación al {fecha_eval} (límite {limite})."}
```

- [ ] **Step 10: Añadir endpoints al router de ingresos**

Modificar `backend/app/routers/ingresos.py` (añadir imports y endpoints, conservando lo de la Task 6):

```python
from app.schemas.seguimiento import SeguimientoRead, SeguimientoUpdate, ValidacionPlazo
from app.services.seguimiento import upsert_seguimiento, validar_plazo

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.put(
    "/{ingreso_id}/seguimiento",
    response_model=SeguimientoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_seguimiento(
    ingreso_id: int,
    payload: SeguimientoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SeguimientoRead:
    seg = upsert_seguimiento(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="seguimiento", entity_id=str(seg.id)
    )
    db.commit()
    db.refresh(seg)
    return seg


@router.get(
    "/{ingreso_id}/seguimiento/validacion-plazo",
    response_model=ValidacionPlazo,
    dependencies=[Depends(_reader)],
)
def validacion_plazo(ingreso_id: int, db: Session = Depends(get_db)) -> ValidacionPlazo:
    return validar_plazo(db, ingreso_id)
```

- [ ] **Step 11: Correr el test de API y verificar que pasa**

Run: `uv run pytest tests/test_seguimiento_api.py -v`
Expected: `7 passed`.

- [ ] **Step 12: Commit**

```bash
git add backend/app/models/seguimiento.py backend/app/models/plazo_programa.py backend/app/models/__init__.py backend/app/schemas/seguimiento.py backend/app/services/seguimiento.py backend/app/routers/ingresos.py backend/migrations/versions/0013_crear_seguimiento.py backend/tests/test_seguimiento_model.py backend/tests/test_seguimiento_api.py
git commit -m "feat(ingresos): seguimiento clínico + validador de plazos por programa (CEPA-013)"
```

---

## Task 9: Cierre y alta del caso (CEPA-014)

Endpoint `POST /api/v1/ingresos/{id}/cierre` que cambia estado (cerrado/derivado), registra tipo de alta (lista cerrada, 409/422 si fuera de catálogo), fecha de alta (única = última atención, D11), flag de revisión y observaciones. Audita. Auditor → 403.

**Files:**
- Modify: `backend/app/schemas/ingreso.py`
- Create: `backend/app/services/cierre.py`
- Modify: `backend/app/routers/ingresos.py`
- Test: `backend/tests/test_cierre_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_cierre_api.py`:

```python
def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


# TC-014-01: cerrar con alta terapéutica
def test_cerrar_con_alta_terapeutica(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "tipo_alta": "terapeutica", "fecha_alta": "2026-06-20"},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "cerrado"
    assert cuerpo["tipo_alta"] == "terapeutica"
    assert cuerpo["fecha_alta"] == "2026-06-20"


# TC-014-02: derivar con observaciones
def test_derivar_con_observaciones(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "derivado", "observaciones": "Derivado a red pública"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "derivado"
    assert r.json()["observaciones"] == "Derivado a red pública"


# TC-014-04: tipo de alta fuera de catálogo -> 422
def test_tipo_alta_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "tipo_alta": "otro"},
    )
    assert r.status_code == 422


# TC-014-05: cerrar conservando flag de revisión
def test_cerrar_con_flag_revision(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "tipo_alta": "medica", "flag_revision": True},
    )
    assert r.status_code == 200
    assert r.json()["flag_revision"] is True


# CA-1: estado fuera de catálogo -> 422
def test_estado_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "pausado"}
    )
    assert r.status_code == 422


# TC-014-06: Auditor no puede cerrar -> 403
def test_auditor_no_cierra(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = as_auditor.post(
        f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "cerrado"}
    )
    assert r.status_code == 403


def test_cierre_ingreso_inexistente(as_admin):
    r = as_admin.post("/api/v1/ingresos/999999/cierre", json={"estado": "cerrado"})
    assert r.status_code == 404
```

- [ ] **Step 2: Correr y ver fallar**

Run: `uv run pytest tests/test_cierre_api.py -v`
Expected: FAIL con `404` (ruta inexistente).

- [ ] **Step 3: Añadir el schema de cierre**

Modificar `backend/app/schemas/ingreso.py` (añadir al final, conservando lo existente):

```python
from app.domain.enums import EstadoCaso, TipoAlta  # ya importados arriba si aplica


class IngresoCierre(BaseModel):
    """Cierre/alta del caso (CEPA-014). Solo se permite estado cerrado o derivado."""

    estado: EstadoCaso
    tipo_alta: TipoAlta | None = None
    fecha_alta: date | None = None
    flag_revision: bool | None = None
    observaciones: str | None = None

    @field_validator("estado")
    @classmethod
    def _solo_cierre_o_derivacion(cls, v: EstadoCaso) -> EstadoCaso:
        if v not in (EstadoCaso.CERRADO, EstadoCaso.DERIVADO):
            raise ValueError("El cierre solo admite estado 'cerrado' o 'derivado'.")
        return v
```

> Nota: `field_validator`, `EstadoCaso`, `TipoAlta` y `date` ya están importados en este archivo desde la Task 6; no duplicar imports.

- [ ] **Step 4: Implementar el servicio**

Crear `backend/app/services/cierre.py`:

```python
"""Cierre y alta del caso (CEPA-014)."""

from fastapi import HTTPException, status

from app.models.ingreso import Ingreso
from app.schemas.ingreso import IngresoCierre


def cerrar_ingreso(db, ingreso_id: int, data: IngresoCierre) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")

    ingreso.estado = data.estado.value
    if data.tipo_alta is not None:
        ingreso.tipo_alta = data.tipo_alta.value
    if data.fecha_alta is not None:
        ingreso.fecha_alta = data.fecha_alta
    if data.flag_revision is not None:
        ingreso.flag_revision = data.flag_revision
    if data.observaciones is not None:
        ingreso.observaciones = data.observaciones
    db.flush()
    return ingreso
```

- [ ] **Step 5: Añadir el endpoint al router de ingresos**

Modificar `backend/app/routers/ingresos.py` (añadir):

```python
from app.schemas.ingreso import IngresoCierre
from app.services.cierre import cerrar_ingreso


@router.post(
    "/{ingreso_id}/cierre",
    response_model=IngresoRead,
    dependencies=[Depends(_writer)],
)
def cerrar(
    ingreso_id: int,
    payload: IngresoCierre,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = cerrar_ingreso(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_cierre_api.py -v`
Expected: `7 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/ingreso.py backend/app/services/cierre.py backend/app/routers/ingresos.py backend/tests/test_cierre_api.py
git commit -m "feat(ingresos): cierre y alta del caso (estado, tipo alta, fecha única D11)"
```

---

## Task 10: ODAS con vencimiento y alerta (CEPA-015)

Modelo `oda` (N:1 con ingreso), endpoints de registro y de consulta de alertas. Fecha de vencimiento obligatoria (422 si falta). Registrar una ODA actualizada no elimina las anteriores (historial). El proceso de alertas lista ODAS que vencen dentro de una ventana (default 5 días) incluyendo las que vencen hoy.

**Files:**
- Create: `backend/app/models/oda.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/oda.py`
- Create: `backend/app/services/oda.py`
- Create: `backend/app/routers/odas.py`
- Modify: `backend/app/main.py`
- Create: `backend/migrations/versions/0014_crear_oda.py`
- Test: `backend/tests/test_oda_model.py`
- Test: `backend/tests/test_oda_api.py`

- [ ] **Step 1: Escribir el test de modelo que falla**

Crear `backend/tests/test_oda_model.py`:

```python
from sqlalchemy import BigInteger, Date, String

from app.models.oda import Oda


def test_columnas_oda():
    assert set(Oda.__table__.columns.keys()) == {
        "id",
        "ingreso_id",
        "identificador",
        "fecha_vencimiento",
        "vigente",
        "created_at",
    }


def test_portabilidad_y_tipos_oda():
    tabla = Oda.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30
    assert isinstance(tabla.columns["id"].type, BigInteger)
    assert isinstance(tabla.columns["fecha_vencimiento"].type, Date)
    assert isinstance(tabla.columns["identificador"].type, String)


def test_fk_ingreso():
    fks = list(Oda.__table__.columns["ingreso_id"].foreign_keys)
    assert fks[0].column.table.name == "ingreso"
```

- [ ] **Step 2: Correr y ver fallar**

Run: `uv run pytest tests/test_oda_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.oda'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/oda.py`:

```python
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Oda(Base):
    """Orden de Primera Atención (v4 D3). Documento administrativo con vencimiento.

    Vinculada al ingreso (folio del paciente). Varias ODAS por ingreso: registrar una
    actualizada no borra las anteriores; `vigente` marca la activa.
    """

    __tablename__ = "oda"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), nullable=False, index=True
    )
    identificador: Mapped[str] = mapped_column(String(60), nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="odas")  # noqa: F821
```

Modificar `backend/app/models/__init__.py` (añadir línea):

```python
from app.models.oda import Oda  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0014_crear_oda.py`**

```python
"""crear oda

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("identificador", sa.String(length=60), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingreso_id"], ["ingreso.id"], name="fk_oda_ingreso"),
    )
    op.create_index("ix_oda_ingreso_id", "oda", ["ingreso_id"])
    op.create_index("ix_oda_fecha_venc", "oda", ["fecha_vencimiento"])


def downgrade() -> None:
    op.drop_index("ix_oda_fecha_venc", table_name="oda")
    op.drop_index("ix_oda_ingreso_id", table_name="oda")
    op.drop_table("oda")
```

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_oda_model.py -v
```
Expected: migración aplica; `3 passed`.

- [ ] **Step 6: Escribir el test de API que falla**

Crear `backend/tests/test_oda_api.py`:

```python
from datetime import date, timedelta


def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


# TC-015-01: registrar ODA con vencimiento
def test_registrar_oda(as_admin):
    ing = _ingreso(as_admin)
    venc = (date.today() + timedelta(days=20)).isoformat()
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/odas",
        json={"identificador": "ODA-1", "fecha_vencimiento": venc},
    )
    assert r.status_code == 201
    assert r.json()["fecha_vencimiento"] == venc
    assert r.json()["vigente"] is True


# TC-015-04: ODA sin fecha de vencimiento -> 422
def test_oda_sin_vencimiento(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-1"}
    )
    assert r.status_code == 422


# TC-015-05: ODA actualizada conserva historial y marca vigente la nueva
def test_oda_actualizada_conserva_historial(as_admin):
    ing = _ingreso(as_admin)
    v1 = (date.today() + timedelta(days=10)).isoformat()
    v2 = (date.today() + timedelta(days=40)).isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-1", "fecha_vencimiento": v1})
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-2", "fecha_vencimiento": v2})
    listado = as_admin.get(f"/api/v1/ingresos/{ing['id']}/odas").json()
    assert len(listado) == 2  # historial conservado
    vigentes = [o for o in listado if o["vigente"]]
    assert len(vigentes) == 1 and vigentes[0]["identificador"] == "ODA-2"


# TC-015-02: alerta de ODAS por vencer (ventana 5 días)
def test_alerta_oda_por_vencer(as_admin):
    ing = _ingreso(as_admin)
    venc = (date.today() + timedelta(days=3)).isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-1", "fecha_vencimiento": venc})
    r = as_admin.get("/api/v1/odas/alertas")
    assert r.status_code == 200
    assert any(o["identificador"] == "ODA-1" for o in r.json())


# TC-015-03: ODA que vence hoy entra en la alerta (límite)
def test_alerta_oda_vence_hoy(as_admin):
    ing = _ingreso(as_admin, rut="7.876.543-K")
    hoy = date.today().isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-HOY", "fecha_vencimiento": hoy})
    r = as_admin.get("/api/v1/odas/alertas")
    assert any(o["identificador"] == "ODA-HOY" for o in r.json())


# ODA lejana NO entra en la alerta
def test_oda_lejana_no_alerta(as_admin):
    ing = _ingreso(as_admin, rut="5.126.663-3")
    venc = (date.today() + timedelta(days=60)).isoformat()
    as_admin.post(f"/api/v1/ingresos/{ing['id']}/odas", json={"identificador": "ODA-LEJOS", "fecha_vencimiento": venc})
    r = as_admin.get("/api/v1/odas/alertas")
    assert not any(o["identificador"] == "ODA-LEJOS" for o in r.json())


# TC-015-06: Auditor no puede registrar ODA -> 403
def test_auditor_no_registra_oda(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    venc = (date.today() + timedelta(days=10)).isoformat()
    r = as_auditor.post(
        f"/api/v1/ingresos/{ing['id']}/odas",
        json={"identificador": "ODA-1", "fecha_vencimiento": venc},
    )
    assert r.status_code == 403
```

- [ ] **Step 7: Correr y ver fallar**

Run: `uv run pytest tests/test_oda_api.py -v`
Expected: FAIL con `404`.

- [ ] **Step 8: Implementar schemas**

Crear `backend/app/schemas/oda.py`:

```python
from datetime import date

from pydantic import BaseModel, ConfigDict


class OdaCreate(BaseModel):
    """Registro de ODA. La fecha de vencimiento es obligatoria (CEPA-015 RN-2)."""

    identificador: str
    fecha_vencimiento: date


class OdaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    identificador: str
    fecha_vencimiento: date
    vigente: bool


class OdaAlerta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    identificador: str
    fecha_vencimiento: date
```

- [ ] **Step 9: Implementar el servicio**

Crear `backend/app/services/oda.py`:

```python
"""Registro de ODAS y alerta de vencimiento (CEPA-015, v4 D3)."""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update

from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.schemas.oda import OdaCreate

VENTANA_ALERTA_DIAS = 5  # ventana por defecto de "ODA por vencer"


def registrar_oda(db, ingreso_id: int, data: OdaCreate) -> Oda:
    """Registra una ODA. La nueva queda vigente; las previas del ingreso pasan a no vigentes
    (se conserva el historial, RN-5)."""
    if db.get(Ingreso, ingreso_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    db.execute(update(Oda).where(Oda.ingreso_id == ingreso_id).values(vigente=False))
    oda = Oda(
        ingreso_id=ingreso_id,
        identificador=data.identificador,
        fecha_vencimiento=data.fecha_vencimiento,
        vigente=True,
    )
    db.add(oda)
    db.flush()
    return oda


def listar_odas(db, ingreso_id: int) -> list[Oda]:
    return list(
        db.execute(
            select(Oda).where(Oda.ingreso_id == ingreso_id).order_by(Oda.id)
        ).scalars()
    )


def odas_por_vencer(db, ventana_dias: int = VENTANA_ALERTA_DIAS) -> list[Oda]:
    """ODAS vigentes que vencen entre hoy y hoy+ventana (inclusive ambos extremos)."""
    hoy = date.today()
    limite = hoy + timedelta(days=ventana_dias)
    return list(
        db.execute(
            select(Oda)
            .where(Oda.vigente.is_(True))
            .where(Oda.fecha_vencimiento >= hoy)
            .where(Oda.fecha_vencimiento <= limite)
            .order_by(Oda.fecha_vencimiento)
        ).scalars()
    )
```

- [ ] **Step 10: Implementar el router**

Crear `backend/app/routers/odas.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.oda import OdaAlerta, OdaCreate, OdaRead
from app.services.oda import listar_odas, odas_por_vencer, registrar_oda

router = APIRouter(prefix="/api/v1", tags=["odas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "/ingresos/{ingreso_id}/odas",
    response_model=OdaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_oda(
    ingreso_id: int,
    payload: OdaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OdaRead:
    oda = registrar_oda(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="oda", entity_id=str(oda.id)
    )
    db.commit()
    db.refresh(oda)
    return oda


@router.get(
    "/ingresos/{ingreso_id}/odas",
    response_model=list[OdaRead],
    dependencies=[Depends(_reader)],
)
def listar(ingreso_id: int, db: Session = Depends(get_db)) -> list[OdaRead]:
    return listar_odas(db, ingreso_id)


@router.get("/odas/alertas", response_model=list[OdaAlerta], dependencies=[Depends(_reader)])
def alertas(db: Session = Depends(get_db)) -> list[OdaAlerta]:
    return odas_por_vencer(db)
```

- [ ] **Step 11: Conectar el router en `app/main.py`**

```python
from app.routers import odas

app.include_router(odas.router)
```

- [ ] **Step 12: Correr el test de API y verificar que pasa**

Run: `uv run pytest tests/test_oda_api.py -v`
Expected: `7 passed`.

- [ ] **Step 13: Commit**

```bash
git add backend/app/models/oda.py backend/app/models/__init__.py backend/app/schemas/oda.py backend/app/services/oda.py backend/app/routers/odas.py backend/app/main.py backend/migrations/versions/0014_crear_oda.py backend/tests/test_oda_model.py backend/tests/test_oda_api.py
git commit -m "feat(ingresos): ODAS con vencimiento, historial y alerta por vencer (CEPA-015)"
```

---

## Task 11: Validador de consentimiento informado (CEPA-016)

Modelo `consentimiento` (1:1 con ingreso), endpoint para registrar estado (firmado/pendiente) con evidencia opcional, endpoint `POST /api/v1/ingresos/{id}/iniciar-tratamiento` que bloquea (409) si el consentimiento no está firmado (D9), y endpoint de alertas de consentimientos pendientes.

**Files:**
- Create: `backend/app/models/consentimiento.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/consentimiento.py`
- Create: `backend/app/services/consentimiento.py`
- Modify: `backend/app/routers/ingresos.py`
- Create: `backend/migrations/versions/0015_crear_consentimiento.py`
- Test: `backend/tests/test_consentimiento_model.py`
- Test: `backend/tests/test_consentimiento_api.py`

- [ ] **Step 1: Escribir el test de modelo que falla**

Crear `backend/tests/test_consentimiento_model.py`:

```python
from sqlalchemy import DateTime, String

from app.models.consentimiento import Consentimiento


def test_columnas_consentimiento():
    assert set(Consentimiento.__table__.columns.keys()) == {
        "id",
        "ingreso_id",
        "estado",
        "evidencia_ref",
        "fecha_firma",
        "created_at",
        "updated_at",
    }


def test_portabilidad_y_tipos():
    tabla = Consentimiento.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30
    assert isinstance(tabla.columns["estado"].type, String)
    assert isinstance(tabla.columns["created_at"].type, DateTime)
    assert tabla.columns["created_at"].type.timezone is True


def test_fk_ingreso_unica():
    cols = Consentimiento.__table__.columns
    assert cols["ingreso_id"].unique is True
    fks = list(cols["ingreso_id"].foreign_keys)
    assert fks[0].column.table.name == "ingreso"
```

- [ ] **Step 2: Correr y ver fallar**

Run: `uv run pytest tests/test_consentimiento_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.consentimiento'`.

- [ ] **Step 3: Implementar el modelo**

Crear `backend/app/models/consentimiento.py`:

```python
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import EstadoConsentimiento


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Consentimiento(Base):
    """Consentimiento informado del ingreso (CEPA-016, v4 D9). 1:1 con `ingreso`.

    `evidencia_ref` es una referencia opcional (URL de archivo o id en ficha clínica);
    el mecanismo de origen está por definir (nota abierta D9).
    """

    __tablename__ = "consentimiento"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    ingreso_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingreso.id"), unique=True, nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(20), default=EstadoConsentimiento.PENDIENTE.value, nullable=False
    )
    evidencia_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_firma: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    ingreso: Mapped["Ingreso"] = relationship(back_populates="consentimiento")  # noqa: F821
```

Modificar `backend/app/models/__init__.py` (añadir línea):

```python
from app.models.consentimiento import Consentimiento  # noqa: F401
```

- [ ] **Step 4: Crear la migración `backend/migrations/versions/0015_crear_consentimiento.py`**

```python
"""crear consentimiento

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consentimiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("evidencia_ref", sa.String(length=255), nullable=True),
        sa.Column("fecha_firma", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingreso_id"], ["ingreso.id"], name="fk_consent_ingreso"),
    )
    op.create_unique_constraint("uq_consent_ingreso", "consentimiento", ["ingreso_id"])


def downgrade() -> None:
    op.drop_constraint("uq_consent_ingreso", "consentimiento", type_="unique")
    op.drop_table("consentimiento")
```

- [ ] **Step 5: Correr el test de modelo y verificar que pasa**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_consentimiento_model.py -v
```
Expected: migración aplica; `3 passed`.

- [ ] **Step 6: Escribir el test de API que falla**

Crear `backend/tests/test_consentimiento_api.py`:

```python
def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


# TC-016-01: sin consentimiento firmado -> iniciar tratamiento bloqueado (409)
def test_iniciar_tratamiento_bloqueado_sin_consentimiento(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/iniciar-tratamiento")
    assert r.status_code == 409
    assert "consentimiento" in r.text.lower()


# TC-016-02: con consentimiento firmado -> tratamiento habilitado
def test_iniciar_tratamiento_con_consentimiento_firmado(as_admin):
    ing = _ingreso(as_admin)
    as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento",
        json={"estado": "firmado", "fecha_firma": "2026-06-02"},
    )
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/iniciar-tratamiento")
    assert r.status_code == 200
    assert r.json()["tratamiento_iniciado"] is True


# TC-016-03: consentimiento pendiente aparece en alertas
def test_alerta_consentimiento_pendiente(as_admin):
    ing = _ingreso(as_admin)
    as_admin.put(f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "pendiente"})
    r = as_admin.get("/api/v1/consentimientos/alertas")
    assert r.status_code == 200
    assert any(c["ingreso_id"] == ing["id"] for c in r.json())


# firmado NO aparece en alertas
def test_consentimiento_firmado_no_en_alertas(as_admin):
    ing = _ingreso(as_admin, rut="7.876.543-K")
    as_admin.put(f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "firmado"})
    r = as_admin.get("/api/v1/consentimientos/alertas")
    assert not any(c["ingreso_id"] == ing["id"] for c in r.json())


# TC-016-04: firmado sin evidencia se acepta (mecanismo D9 por definir)
def test_firmado_sin_evidencia_aceptado(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "firmado"}
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "firmado"


# estado inválido -> 422
def test_estado_consentimiento_invalido(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "quizas"}
    )
    assert r.status_code == 422


# TC-016-05: Auditor no puede cambiar estado del consentimiento -> 403
def test_auditor_no_cambia_consentimiento(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = as_auditor.put(
        f"/api/v1/ingresos/{ing['id']}/consentimiento", json={"estado": "firmado"}
    )
    assert r.status_code == 403
```

- [ ] **Step 7: Correr y ver fallar**

Run: `uv run pytest tests/test_consentimiento_api.py -v`
Expected: FAIL con `404`.

- [ ] **Step 8: Implementar schemas**

Crear `backend/app/schemas/consentimiento.py`:

```python
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.enums import EstadoConsentimiento


class ConsentimientoUpdate(BaseModel):
    """Registro del estado del consentimiento (CEPA-016). Evidencia opcional (D9)."""

    estado: EstadoConsentimiento
    evidencia_ref: str | None = None
    fecha_firma: date | None = None


class ConsentimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    estado: EstadoConsentimiento
    evidencia_ref: str | None
    fecha_firma: date | None


class ConsentimientoAlerta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    estado: EstadoConsentimiento
```

- [ ] **Step 9: Implementar el servicio**

Crear `backend/app/services/consentimiento.py`:

```python
"""Validador de consentimiento informado (CEPA-016, v4 D9)."""

from fastapi import HTTPException, status
from sqlalchemy import select

from app.domain.enums import EstadoConsentimiento
from app.models.consentimiento import Consentimiento
from app.models.ingreso import Ingreso
from app.schemas.consentimiento import ConsentimientoUpdate


def _obtener_ingreso(db, ingreso_id: int) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    return ingreso


def upsert_consentimiento(db, ingreso_id: int, data: ConsentimientoUpdate) -> Consentimiento:
    _obtener_ingreso(db, ingreso_id)
    consent = db.execute(
        select(Consentimiento).where(Consentimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if consent is None:
        consent = Consentimiento(ingreso_id=ingreso_id)
        db.add(consent)
    consent.estado = data.estado.value
    if data.evidencia_ref is not None:
        consent.evidencia_ref = data.evidencia_ref
    if data.fecha_firma is not None:
        consent.fecha_firma = data.fecha_firma
    db.flush()
    return consent


def iniciar_tratamiento(db, ingreso_id: int) -> Ingreso:
    """Bloquea el inicio si el consentimiento no está firmado (D9 RN-1)."""
    ingreso = _obtener_ingreso(db, ingreso_id)
    consent = db.execute(
        select(Consentimiento).where(Consentimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if consent is None or consent.estado != EstadoConsentimiento.FIRMADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede iniciar el tratamiento: el consentimiento informado es obligatorio y debe estar firmado.",
        )
    ingreso.tratamiento_iniciado = True
    db.flush()
    return ingreso


def consentimientos_pendientes(db) -> list[Consentimiento]:
    return list(
        db.execute(
            select(Consentimiento)
            .where(Consentimiento.estado == EstadoConsentimiento.PENDIENTE.value)
            .order_by(Consentimiento.id)
        ).scalars()
    )
```

- [ ] **Step 10: Añadir endpoints al router de ingresos + router de consentimientos**

Modificar `backend/app/routers/ingresos.py` (añadir):

```python
from app.schemas.consentimiento import ConsentimientoRead, ConsentimientoUpdate
from app.services.consentimiento import iniciar_tratamiento, upsert_consentimiento


@router.put(
    "/{ingreso_id}/consentimiento",
    response_model=ConsentimientoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_consentimiento(
    ingreso_id: int,
    payload: ConsentimientoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ConsentimientoRead:
    consent = upsert_consentimiento(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="consentimiento", entity_id=str(consent.id)
    )
    db.commit()
    db.refresh(consent)
    return consent


@router.post(
    "/{ingreso_id}/iniciar-tratamiento",
    response_model=IngresoRead,
    dependencies=[Depends(_writer)],
)
def iniciar_tratamiento_endpoint(
    ingreso_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = iniciar_tratamiento(db, ingreso_id)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso
```

Crear `backend/app/routers/consentimientos.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.consentimiento import ConsentimientoAlerta
from app.services.consentimiento import consentimientos_pendientes

router = APIRouter(prefix="/api/v1/consentimientos", tags=["consentimientos"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get("/alertas", response_model=list[ConsentimientoAlerta], dependencies=[Depends(_reader)])
def alertas(db: Session = Depends(get_db)) -> list[ConsentimientoAlerta]:
    return consentimientos_pendientes(db)
```

- [ ] **Step 11: Conectar el router en `app/main.py`**

```python
from app.routers import consentimientos

app.include_router(consentimientos.router)
```

- [ ] **Step 12: Correr el test de API y verificar que pasa**

Run: `uv run pytest tests/test_consentimiento_api.py -v`
Expected: `7 passed`.

- [ ] **Step 13: Commit**

```bash
git add backend/app/models/consentimiento.py backend/app/models/__init__.py backend/app/schemas/consentimiento.py backend/app/services/consentimiento.py backend/app/routers/ingresos.py backend/app/routers/consentimientos.py backend/app/main.py backend/migrations/versions/0015_crear_consentimiento.py backend/tests/test_consentimiento_model.py backend/tests/test_consentimiento_api.py
git commit -m "feat(ingresos): validador de consentimiento informado + bloqueo de tratamiento (CEPA-016)"
```

---

## Task 12: Verificación integral de la épica

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa + lint**

Run (desde `backend/`):
```bash
uv run pytest -v
uv run ruff check .
```
Expected: todos los tests de EPIC-01 (rut, enums, modelos, folio, alta, búsqueda, seguimiento, cierre, ODAS, consentimiento) y los de la Fundación/EPIC-00 en verde; ruff sin errores.

- [ ] **Step 2: Migraciones desde cero (paridad con producción)**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: baja a vacío y reconstruye todo el esquema (incluidas `paciente`, `ingreso`, `folio_seq`, `seguimiento`, `plazo_programa`, `oda`, `consentimiento`) sin error.

- [ ] **Step 3: Verificar el job Oracle gated (portabilidad)**

Confirmar que el push dispara `backend-ci` y que el job Oracle (gated, allowed-to-fail) aplica las migraciones de EPIC-01 sin usar tipos/SQL específicos de motor. Revisar que no se introdujeron `ON CONFLICT`/`LIMIT/OFFSET` crudos ni tipos nativos.

- [ ] **Step 4: Commit final (si quedó algo, p. ej. `uv.lock`)**

```bash
git add -A
git commit -m "chore(ingresos): EPIC-01 completa — ingresos, folio, 360, seguimiento, ODAS, consentimiento" || echo "nada que commitear"
```

---

## Cobertura (CEPA-01X ↔ Tasks)

| Historia | Tasks | Test Cases cubiertos |
|----------|-------|----------------------|
| **(util compartido RUT)** | Task 1 | RN-1 de CEPA-010 (validación módulo 11) |
| **(catálogos D4/D6)** | Task 2 | RN-6 CEPA-010, estados/altas CEPA-013/014/016 |
| **CEPA-010** Registrar ingreso | Task 3 (paciente), Task 4 (ingreso), Task 6 (alta) | TC-010-01..06 (CA-1..CA-5, RN-1..RN-7) |
| **CEPA-011** Folio auto/manual | Task 4 (modelo), Task 5 (secuencial), Task 6 (resolución folio) | TC-011-01, 02, 04, 05, 06 (CA-1..CA-4) |
| **CEPA-012** Búsqueda 360° | Task 7 | TC-012-01, 02, 04, 05, 06 (CA-1, CA-3, CA-4) |
| **CEPA-013** Seguimiento clínico | Task 8 | TC-013-01..06 (CA-1..CA-4, validador D10) |
| **CEPA-014** Cierre y alta | Task 9 | TC-014-01, 02, 04, 05, 06 (CA-1..CA-4) |
| **CEPA-015** ODAS y alerta | Task 10 | TC-015-01..06 (CA-1..CA-3) |
| **CEPA-016** Consentimiento | Task 11 | TC-016-01..05 (CA-1..CA-4) |
| **Verificación** | Task 12 | DoD: suite verde, OpenAPI auto (FastAPI), migraciones portables |

**Notas de mapeo / TC parcialmente diferidos:**
- **TC-011-03** (ingreso post-15:00 con fecha del día hábil siguiente): el modelo ya permite `fecha_ingreso` y `folio_manual` arbitrarios — el cálculo del "día hábil siguiente" es lógica de presentación/UI; el backend acepta la fecha provista. Se valida que el alta acepta `fecha_ingreso` manual; el calendario de días hábiles queda como mejora.
- **TC-012-03** (rendimiento < 10 s, OU3): se cubre estructuralmente con índices en `rut`, `nombre`, `folio` y `paciente_id`; la medición de carga es una prueba no funcional a ejecutar en QA con volumen real (no es un test unitario de esta épica).
- **CA-2 de CEPA-016** (validador marca "cumplido"): se materializa en el flag `tratamiento_iniciado` + el 200 de `iniciar-tratamiento`; el endpoint de "estado del validador" puede consultarse vía `vista-360`/`consentimiento` GET si se requiere explícito en EPIC-10 (alertas).

---

## Notas de cierre

### Firmas que dependen de Fundación/EPIC-00 — verificar contra el código real antes del loop
- **`app.auth.deps.require_role(*roles)` y `get_current_user`**: este plan asume que `require_role` devuelve una dependencia usable en `dependencies=[Depends(...)]` y que `get_current_user` retorna un objeto con `.username`. Verificar el nombre exacto del atributo (`username` vs `user` vs `email`) y ajustar `record_audit(actor=...)` en todos los routers.
- **`app.audit.service.record_audit(db, actor, action, entity, entity_id)`**: confirmar firma exacta (posicional vs keyword) y si hace `flush`/`commit` internamente. Este plan llama a `record_audit(...)` y luego `db.commit()` en el router; si `record_audit` ya commitea, eliminar el `db.commit()` redundante o reordenar.
- **Fixtures `as_admin`, `as_auditor`, `as_coordinacion`**: se asume que son `TestClient` con JWT del rol ya inyectado. Verificar nombres reales en el `conftest.py` de EPIC-00.
- **`down_revision` de la migración 0010**: reemplazar `<ULTIMA_REVISION_DE_EPIC_00>` por la revisión head real (`uv run alembic heads`). El encadenamiento 0011→0010, 0012→0011, etc., asume que 0010 es la primera de esta épica.
- **`_utcnow()`**: la Fundación lo define en `audit_log.py`. Este plan lo redeclara local en cada modelo para no acoplar; si se prefiere centralizarlo, moverlo a `app/util/time.py` y reimportar.

### Decisiones de negocio abiertas (declaradas en el spec) — no bloquean el plan, pero condicionan refinamientos
- **D11 — tipificación de altas**: el plan implementa **una sola `fecha_alta`** (última atención) con `tipo_alta` opcional, conforme a la inclinación de v4 D11. Si Coordinación opta por múltiples fechas por tipo de alta, habrá que migrar a una tabla `alta` 1:N (cambio aditivo, nueva migración).
- **D9 — origen del consentimiento**: el plan modela `evidencia_ref` como string opcional (URL de archivo o id en ficha clínica) y **acepta firmado sin evidencia** (TC-016-04). Cuando se defina el mecanismo (carga de archivo vs. referencia a SALUTEM/SAM, recordando que el aplicativo no escribe sobre SALUTEM, D12), se endurece la validación o se agrega almacenamiento de archivo.
- **D2 — reingreso vs. nuevo folio**: el plan permite reutilizar folio en reingresos del mismo paciente (`es_reingreso=True`) diferenciando por `numero_siniestro`. Pendiente confirmar con Coordinación si los reingresos deben generar **nuevo** folio; de ser así, basta con cambiar la rama de `_resolver_folio` (sin tocar el esquema).
- **Ventana de alerta de ODAS** (CEPA-015 nota): fijada en 5 días (`VENTANA_ALERTA_DIAS`); parametrizable por configuración cuando EPIC-11 (Config/Calidad) lo formalice.
- **Catálogos de regiones/comunas y diagnósticos** (CEPA-010 nota, D5): hoy se aceptan como string libre; cuando se confirme el catálogo (alineación con dashboard), se podrán convertir en listas cerradas o tablas de referencia.

### Dependencias hacia adelante (Oleada 3/4)
- La **vista 360°** (Task 7) devuelve ranuras vacías para fármacos/licencias/controles/reintegro. Esas épicas deben **poblar** esas dimensiones consultando por `folio`/`paciente_id`; documentar el contrato de `Vista360` para que lo extiendan sin romperlo.
- Las **alertas** de ODAS (Task 10) y consentimiento (Task 11) exponen endpoints de consulta; **EPIC-10 (Alertas/Notificaciones)** decidirá la entrega in-app/correo (D12: correo solo para alertas) y la programación del proceso.
- El **reporte de ODAS vencidas** queda fuera de EPIC-01 (corresponde a **EPIC-09**, según CEPA-015 RN-4).
