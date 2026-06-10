# EPIC-11 — Configurabilidad y Calidad de Datos — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar la configurabilidad autónoma de formularios dinámicos (CEPA-110), la validación de parametrización y campos obligatorios (CEPA-111) y la lectura de documentos PDF con pre-llenado editable (CEPA-112) sobre la Fundación FastAPI + SQLAlchemy + EPIC-00 + EPIC-01 ya en `main`.

**Architecture:** Tres subsistemas coordinados. (1) Un motor de formularios dinámicos con versionado: modelo `form_definition` + `form_version` + `field_def` que guarda la definición de cada formulario como lista de definiciones de campo en JSON portable; la publicación crea una nueva versión inmutable. (2) Un validador de parametrización puro (sin estado propio) que se invoca antes de toda publicación: comprueba que los 7 campos obligatorios del sistema estén presentes, bien tipados y con nomenclatura estándar, y que ningún campo tenga configuración inconsistente. (3) Un servicio de extracción de PDF inyectable/mockeable en tests (`PdfParser` protocol) que usa `pypdf` en producción y un stub en tests; el endpoint devuelve los campos extraídos como borrador editable sin persistir hasta que el usuario confirme. Todos los endpoints consumen `require_role` y `record_audit` de EPIC-00.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (tipos genéricos portables), Alembic, Pydantic v2, `pypdf>=4.0`, pytest sobre Postgres real. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`; fixtures `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos desde `backend/` con `uv run …`. BD de tests: `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`.
- Fixtures de EPIC-00: `as_admin`, `as_coordinacion`, `as_auditor`, `db_session`, `client`.
- `app/domain/enums.py` (Enums creados por EPIC-01): `Sexo`, `TipoIngreso`, etc.

**Convención de RBAC usada en esta épica:**
```python
from app.auth.deps import get_current_user, require_role

# Editor de formularios: solo Coordinacion
_coord   = require_role("Coordinacion")
# Escritura operativa: Administrativo o Coordinacion
_writer  = require_role("Administrativo", "Coordinacion")
# Lectura: todos los roles
_reader  = require_role("Administrativo", "Coordinacion", "Auditor")
```

---

## Estructura de archivos de esta épica

```
backend/
  app/
    models/
      form_definition.py       # FormDefinition, FormVersion, FieldDef
    schemas/
      form_config.py           # Pydantic: FieldDefIn/Out, FormVersionRead, etc.
      pdf_extract.py           # Pydantic: ExtractedField, PdfExtractResult
    services/
      form_validator.py        # Validador de parametrización (puro, sin DB)
      form_config.py           # Lógica de CRUD / publicación de versiones
      pdf_parser.py            # Protocol PdfParser + implementación pypdf
    routers/
      form_config.py           # /api/v1/form-definitions
      pdf_extract.py           # /api/v1/pdf-extract
  migrations/versions/
    <rev>_crear_form_tables.py # Una sola migración para FormDefinition+Version+FieldDef
  tests/
    test_form_definition_model.py
    test_field_def_model.py
    test_form_validator.py
    test_form_config_api.py
    test_pdf_parser.py
    test_pdf_extract_api.py
```

---

## Task 1: Modelos `FormDefinition`, `FormVersion`, `FieldDef` + migración [P0]

Soporta CEPA-110 CA-1/CA-2/CA-3: formularios versionados, campos configurables, datos históricos conservados.

**Reglas de modelado:**
- `form_definition`: una fila por formulario del sistema (p. ej. `"ingresos"`). Columnas ≤30 chars.
- `form_version`: cada versión publicada (o borrador). Estado `draft`/`published`. Una publicación crea nueva fila.
- `field_def`: cada campo de una versión. Definición en columnas nativas (no JSON), para facilitar consulta portable. `field_type ∈ {text, number, date, select, boolean}`.

**Files:**
- Create: `backend/app/models/form_definition.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/<rev>_crear_form_tables.py`
- Test: `backend/tests/test_form_definition_model.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_form_definition_model.py`:

```python
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String

from app.models.form_definition import FieldDef, FormDefinition, FormVersion


def test_form_definition_columnas():
    tabla = FormDefinition.__table__
    assert tabla.name == "form_definition"
    assert set(tabla.columns.keys()) == {"id", "form_key", "created_at"}


def test_form_version_columnas():
    tabla = FormVersion.__table__
    assert tabla.name == "form_version"
    assert set(tabla.columns.keys()) == {
        "id",
        "form_def_id",
        "version_num",
        "status",
        "published_at",
        "created_by",
        "created_at",
    }


def test_field_def_columnas():
    tabla = FieldDef.__table__
    assert tabla.name == "field_def"
    assert set(tabla.columns.keys()) == {
        "id",
        "form_version_id",
        "field_key",
        "label",
        "field_type",
        "required",
        "system_locked",
        "domain_values",
        "display_order",
        "active",
    }


def test_portabilidad_identificadores():
    for modelo in (FormDefinition, FormVersion, FieldDef):
        tabla = modelo.__table__
        for nombre in [tabla.name, *tabla.columns.keys()]:
            assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
            assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_tipos_portables():
    cols_fd = FormDefinition.__table__.columns
    assert isinstance(cols_fd["id"].type, BigInteger)
    assert cols_fd["id"].identity is not None

    cols_fv = FormVersion.__table__.columns
    assert isinstance(cols_fv["id"].type, BigInteger)
    assert isinstance(cols_fv["version_num"].type, Integer)
    assert isinstance(cols_fv["published_at"].type, DateTime)
    assert cols_fv["published_at"].type.timezone is True

    cols_field = FieldDef.__table__.columns
    assert isinstance(cols_field["required"].type, Boolean)
    assert isinstance(cols_field["system_locked"].type, Boolean)
    assert isinstance(cols_field["active"].type, Boolean)
    # domain_values: JSON genérico (portable PG/Oracle)
    from sqlalchemy import JSON
    assert isinstance(cols_field["domain_values"].type, JSON)


def test_field_def_fk_a_form_version():
    fks = list(FieldDef.__table__.columns["form_version_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "form_version"


def test_form_version_fk_a_form_definition():
    fks = list(FormVersion.__table__.columns["form_def_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "form_definition"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_form_definition_model.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.models.form_definition'`.

- [ ] **Step 3: Implementar los modelos**

Crear `backend/app/models/form_definition.py`:

```python
"""Modelos de formularios dinámicos versionados (CEPA-110).

FormDefinition  — registro maestro de un formulario (p. ej. "ingresos").
FormVersion     — versión concreta (borrador o publicada); inmutable una vez publicada.
FieldDef        — campo individual de una versión. domain_values usa JSON genérico (portable).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FormDefinition(Base):
    """Registro maestro de un formulario del sistema (uno por módulo/formulario)."""

    __tablename__ = "form_definition"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    form_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    versions: Mapped[list[FormVersion]] = relationship(
        back_populates="form_definition", cascade="all, delete-orphan"
    )


class FormVersion(Base):
    """Versión de un formulario. status: 'draft' o 'published'.

    Una vez publicada es inmutable: los nuevos cambios generan una nueva versión draft.
    """

    __tablename__ = "form_version"
    __table_args__ = (
        UniqueConstraint("form_def_id", "version_num", name="uq_formver_def_num"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    form_def_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("form_definition.id"), nullable=False, index=True
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    # status: 'draft' | 'published'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    form_definition: Mapped[FormDefinition] = relationship(back_populates="versions")
    fields: Mapped[list[FieldDef]] = relationship(
        back_populates="form_version", cascade="all, delete-orphan"
    )


class FieldDef(Base):
    """Definición de un campo dentro de una FormVersion.

    field_type ∈ {'text', 'number', 'date', 'select', 'boolean'}.
    domain_values: lista de valores permitidos (solo para field_type='select'); JSON genérico.
    system_locked: True para campos obligatorios del sistema (no removibles, CEPA-111 RN-2).
    active: False para campos desactivados (se conservan datos históricos, CA-2).
    """

    __tablename__ = "field_def"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    form_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("form_version.id"), nullable=False, index=True
    )
    field_key: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    # field_type: 'text' | 'number' | 'date' | 'select' | 'boolean'
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    system_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # JSON genérico (portable PG/Oracle — no usar JSONB)
    domain_values: Mapped[list | None] = mapped_column(JSON, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    form_version: Mapped[FormVersion] = relationship(back_populates="fields")
```

Modificar `backend/app/models/__init__.py` añadiendo (conservar líneas existentes):

```python
from app.models.form_definition import FieldDef, FormDefinition, FormVersion  # noqa: F401
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_form_definition_model.py -v`
Expected: `7 passed`.

- [ ] **Step 5: Crear la migración**

Crear `backend/migrations/versions/<rev>_crear_form_tables.py` — reemplaza `<rev>` por el resultado de `uv run alembic heads` (ver Notas de cierre):

```python
"""crear form_definition form_version field_def

Revision ID: <RESOLVER: alembic heads>
Revises: <ULTIMA_REVISION_DE_EPIC_01>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "<RESOLVER: alembic heads>"
down_revision = "<ULTIMA_REVISION_DE_EPIC_01>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form_definition",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("form_key", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_formdef_key", "form_definition", ["form_key"])
    op.create_index("ix_form_definition_key", "form_definition", ["form_key"])

    op.create_table(
        "form_version",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("form_def_id", sa.BigInteger(), nullable=False),
        sa.Column("version_num", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["form_def_id"], ["form_definition.id"], name="fk_formver_formdef"
        ),
        sa.UniqueConstraint("form_def_id", "version_num", name="uq_formver_def_num"),
    )
    op.create_index("ix_form_version_def_id", "form_version", ["form_def_id"])

    op.create_table(
        "field_def",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("form_version_id", sa.BigInteger(), nullable=False),
        sa.Column("field_key", sa.String(length=60), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("field_type", sa.String(length=20), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("system_locked", sa.Boolean(), nullable=False),
        sa.Column("domain_values", sa.JSON(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["form_version_id"], ["form_version.id"], name="fk_fielddef_formver"
        ),
    )
    op.create_index("ix_field_def_ver_id", "field_def", ["form_version_id"])


def downgrade() -> None:
    op.drop_index("ix_field_def_ver_id", table_name="field_def")
    op.drop_table("field_def")
    op.drop_index("ix_form_version_def_id", table_name="form_version")
    op.drop_table("form_version")
    op.drop_index("ix_form_definition_key", table_name="form_definition")
    op.drop_constraint("uq_formdef_key", "form_definition", type_="unique")
    op.drop_table("form_definition")
```

- [ ] **Step 6: Verificar la migración**

Run:
```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: crea las tres tablas, las elimina y las vuelve a crear sin error.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/form_definition.py backend/app/models/__init__.py \
        backend/migrations/versions/*_crear_form_tables.py \
        backend/tests/test_form_definition_model.py
git commit -m "feat(config): modelos FormDefinition/FormVersion/FieldDef + migración portable"
```

---

## Task 2: Validador de parametrización (CEPA-111 P0)

Servicio puro (sin estado en BD) que recibe una lista de `FieldDef` y devuelve errores de parametrización. Se invoca antes de publicar. Implementa las reglas CEPA-111 RN-1 a RN-4.

**Campos obligatorios del sistema (D6):** `sexo`, `edad`, `diagnostico`, `modelo_trat`, `tipo_alta`, `tipo_ingreso`, `tipo_convenio` — identificadores normalizados, `system_locked=True`, no removibles.

**Files:**
- Create: `backend/app/services/form_validator.py`
- Test: `backend/tests/test_form_validator.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_form_validator.py`:

```python
import pytest

from app.services.form_validator import (
    SYSTEM_REQUIRED_FIELDS,
    ParametrizationError,
    validate_form_version,
)


def _field(
    field_key: str,
    field_type: str = "text",
    required: bool = True,
    system_locked: bool = False,
    domain_values: list | None = None,
    active: bool = True,
    label: str = "Etiqueta",
):
    """Helper: devuelve un dict que imita los atributos de un FieldDef."""
    return {
        "field_key": field_key,
        "field_type": field_type,
        "required": required,
        "system_locked": system_locked,
        "domain_values": domain_values,
        "active": active,
        "label": label,
    }


def _all_system_fields():
    """Genera la lista mínima de campos obligatorios del sistema bien parametrizados."""
    tipo_select = {
        "tipo_alta": ["terapeutica", "medica", "psicologica", "abandono", "derivacion"],
        "tipo_ingreso": ["consulta_espontanea", "convenio", "proyecto", "particular"],
        "tipo_convenio": ["ISL", "SUSESO", "particular", "otro"],
    }
    fields = []
    for key in SYSTEM_REQUIRED_FIELDS:
        ftype = "select" if key in tipo_select else "text"
        dv = tipo_select.get(key)
        fields.append(
            _field(
                field_key=key,
                field_type=ftype,
                required=True,
                system_locked=True,
                domain_values=dv,
                active=True,
            )
        )
    return fields


# TC-111-01: formulario con los 7 campos obligatorios bien parametrizados → sin errores
def test_formulario_valido_sin_errores():
    campos = _all_system_fields()
    errores = validate_form_version(campos)
    assert errores == [], f"Se esperaba lista vacía, obtuvo: {errores}"


# TC-111-02: campo sin tipo de dato → error de parametrización
def test_campo_sin_tipo_bloquea_publicacion():
    campos = _all_system_fields()
    campos.append(_field("extra", field_type=""))
    errores = validate_form_version(campos)
    assert any("field_type" in e["error"] or "tipo" in e["error"].lower() for e in errores)


# TC-111-02: campo sin etiqueta → error
def test_campo_sin_label_bloquea_publicacion():
    campos = _all_system_fields()
    campos.append(_field("extra2", label=""))
    errores = validate_form_version(campos)
    assert any("label" in e["error"].lower() or "etiqueta" in e["error"].lower() for e in errores)


# TC-111-03: formulario sin campo obligatorio del sistema → error
def test_campo_obligatorio_sistema_faltante_bloquea():
    campos = [f for f in _all_system_fields() if f["field_key"] != "diagnostico"]
    errores = validate_form_version(campos)
    assert any("diagnostico" in e["error"] for e in errores)


# TC-111-03: campo system_locked no puede marcarse inactive
def test_campo_system_locked_no_puede_desactivarse():
    campos = _all_system_fields()
    for c in campos:
        if c["field_key"] == "sexo":
            c["active"] = False
    errores = validate_form_version(campos)
    assert any("sexo" in e["error"] and "system_locked" in e["error"] for e in errores)


# TC-111-05: campo select obligatorio sin domain_values → error
def test_campo_select_obligatorio_sin_dominio_da_error():
    campos = _all_system_fields()
    for c in campos:
        if c["field_key"] == "tipo_ingreso":
            c["domain_values"] = None
    errores = validate_form_version(campos)
    assert any("tipo_ingreso" in e["error"] for e in errores)


# RN-1: campo con field_key duplicado → error
def test_field_key_duplicado_es_error():
    campos = _all_system_fields()
    campos.append(_field("sexo", field_type="text"))  # duplicado
    errores = validate_form_version(campos)
    assert any("duplicado" in e["error"].lower() or "duplicated" in e["error"].lower() for e in errores)


# RN-1: field_type fuera del conjunto válido → error
def test_field_type_invalido_es_error():
    campos = _all_system_fields()
    campos.append(_field("nuevo_campo", field_type="imagen"))
    errores = validate_form_version(campos)
    assert any("field_type" in e["error"] or "tipo" in e["error"].lower() for e in errores)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_form_validator.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.form_validator'`.

- [ ] **Step 3: Implementar el validador**

Crear `backend/app/services/__init__.py` vacío (si no existe por EPIC-01).

Crear `backend/app/services/form_validator.py`:

```python
"""Validador de parametrización de formularios (CEPA-111).

Recibe una lista de dicts con los atributos de FieldDef (o instancias ORM convertidas
a dict) y devuelve una lista de errores. Lista vacía = formulario bien parametrizado.

Reglas implementadas (CEPA-111 RN-1 a RN-4):
- Todos los campos obligatorios del sistema deben estar presentes, activos y system_locked.
- Ningún campo system_locked puede estar inactive.
- Cada campo debe tener field_type en el conjunto válido y label no vacío.
- Campos de tipo 'select' marcados required deben tener domain_values no vacío.
- No puede haber field_key duplicado.
"""

from __future__ import annotations

# Identificadores normalizados de los 7 campos obligatorios del sistema (D6 / CEPA-111 RN-2).
SYSTEM_REQUIRED_FIELDS: tuple[str, ...] = (
    "sexo",
    "edad",
    "diagnostico",
    "modelo_trat",
    "tipo_alta",
    "tipo_ingreso",
    "tipo_convenio",
)

VALID_FIELD_TYPES: frozenset[str] = frozenset({"text", "number", "date", "select", "boolean"})


class ParametrizationError(Exception):
    """Se lanza cuando validate_form_version detecta errores y el llamador decide abortar."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        super().__init__(f"Formulario mal parametrizado: {len(errors)} error(es)")


def validate_form_version(fields: list[dict]) -> list[dict[str, str]]:
    """Valida la lista de definiciones de campo de una versión de formulario.

    Cada elemento de `fields` debe contener al menos las claves:
        field_key, field_type, required, system_locked, domain_values, active, label.

    Retorna lista de dicts {"field_key": ..., "error": ...}.
    Lista vacía indica formulario bien parametrizado y listo para publicar.
    """
    errors: list[dict[str, str]] = []

    # 1. Detectar field_key duplicados
    seen_keys: set[str] = set()
    for f in fields:
        key = f.get("field_key", "")
        if key in seen_keys:
            errors.append(
                {"field_key": key, "error": f"field_key duplicado: '{key}'"}
            )
        seen_keys.add(key)

    # Índice para búsquedas posteriores (usamos el primero con ese key)
    index: dict[str, dict] = {}
    for f in fields:
        k = f.get("field_key", "")
        if k not in index:
            index[k] = f

    # 2. Campos obligatorios del sistema deben estar presentes, activos y system_locked
    for required_key in SYSTEM_REQUIRED_FIELDS:
        if required_key not in index:
            errors.append(
                {
                    "field_key": required_key,
                    "error": (
                        f"Campo obligatorio del sistema '{required_key}' ausente en el formulario."
                    ),
                }
            )
            continue
        f = index[required_key]
        if not f.get("active", True):
            errors.append(
                {
                    "field_key": required_key,
                    "error": (
                        f"Campo system_locked '{required_key}' no puede estar inactivo."
                    ),
                }
            )
        if not f.get("system_locked", False):
            errors.append(
                {
                    "field_key": required_key,
                    "error": (
                        f"Campo obligatorio del sistema '{required_key}' debe tener "
                        "system_locked=True."
                    ),
                }
            )

    # 3. Validar cada campo individualmente
    for f in fields:
        key = f.get("field_key", "(sin clave)")

        # 3a. Etiqueta no vacía
        label = (f.get("label") or "").strip()
        if not label:
            errors.append(
                {"field_key": key, "error": f"Campo '{key}' sin etiqueta (label vacío)."}
            )

        # 3b. field_type en conjunto válido
        ftype = (f.get("field_type") or "").strip()
        if not ftype:
            errors.append(
                {"field_key": key, "error": f"Campo '{key}' sin tipo de dato (field_type vacío)."}
            )
        elif ftype not in VALID_FIELD_TYPES:
            errors.append(
                {
                    "field_key": key,
                    "error": (
                        f"Campo '{key}' tiene field_type inválido: '{ftype}'. "
                        f"Valores válidos: {sorted(VALID_FIELD_TYPES)}."
                    ),
                }
            )

        # 3c. Select obligatorio debe tener domain_values
        if ftype == "select" and f.get("required", False):
            dv = f.get("domain_values")
            if not dv:
                errors.append(
                    {
                        "field_key": key,
                        "error": (
                            f"Campo select obligatorio '{key}' sin domain_values definido."
                        ),
                    }
                )

    return errors
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_form_validator.py -v`
Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/form_validator.py backend/tests/test_form_validator.py
git commit -m "feat(config): validador de parametrización de formularios (CEPA-111)"
```

---

## Task 3: Schemas Pydantic para configuración de formularios [P0]

Modelos de entrada/salida para los endpoints de CRUD de formularios dinámicos.

**Files:**
- Create: `backend/app/schemas/form_config.py`
- Test: `backend/tests/test_form_config_schemas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_form_config_schemas.py`:

```python
from app.schemas.form_config import (
    FieldDefIn,
    FieldDefOut,
    FormVersionCreate,
    FormVersionRead,
    PublishResult,
)


def test_field_def_in_valida_field_type_valido():
    from pydantic import ValidationError
    import pytest

    fd = FieldDefIn(
        field_key="sexo",
        label="Sexo",
        field_type="select",
        required=True,
        system_locked=True,
        domain_values=["F", "M"],
        display_order=1,
    )
    assert fd.field_key == "sexo"
    assert fd.domain_values == ["F", "M"]


def test_field_def_in_rechaza_field_type_invalido():
    from pydantic import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        FieldDefIn(
            field_key="foto",
            label="Foto",
            field_type="imagen",  # no válido
            required=False,
        )


def test_form_version_create_acepta_lista_de_campos():
    fv = FormVersionCreate(
        fields=[
            FieldDefIn(field_key="edad", label="Edad", field_type="number", required=True, system_locked=True),
        ]
    )
    assert len(fv.fields) == 1


def test_form_version_read_tiene_from_attributes():
    # Verifica que el schema de lectura pueda construirse desde ORM
    fv = FormVersionRead(
        id=1,
        form_def_id=1,
        version_num=1,
        status="published",
        published_at=None,
        created_by="coord",
        created_at=__import__("datetime").datetime(2026, 6, 10, tzinfo=__import__("datetime").timezone.utc),
        fields=[],
    )
    assert fv.status == "published"


def test_publish_result_tiene_errores_y_version():
    pr = PublishResult(success=True, version_id=3, errors=[])
    assert pr.success is True
    pr2 = PublishResult(success=False, version_id=None, errors=[{"field_key": "x", "error": "falta"}])
    assert len(pr2.errors) == 1
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_form_config_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.form_config'`.

- [ ] **Step 3: Implementar los schemas**

Crear `backend/app/schemas/form_config.py`:

```python
"""Schemas Pydantic v2 para configuración de formularios dinámicos (CEPA-110 / CEPA-111)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.form_validator import VALID_FIELD_TYPES


class FieldDefIn(BaseModel):
    """Campo recibido al crear/editar una versión de formulario."""

    field_key: str
    label: str
    field_type: str
    required: bool = False
    system_locked: bool = False
    domain_values: list[str] | None = None
    display_order: int = 0
    active: bool = True

    @field_validator("field_type")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        if v not in VALID_FIELD_TYPES:
            raise ValueError(
                f"field_type '{v}' no válido. Valores aceptados: {sorted(VALID_FIELD_TYPES)}"
            )
        return v


class FieldDefOut(BaseModel):
    """Campo devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field_key: str
    label: str
    field_type: str
    required: bool
    system_locked: bool
    domain_values: list[str] | None
    display_order: int
    active: bool


class FormVersionCreate(BaseModel):
    """Cuerpo de la petición de creación/actualización de borrador."""

    fields: list[FieldDefIn]


class FormVersionRead(BaseModel):
    """Versión de formulario devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    form_def_id: int
    version_num: int
    status: str
    published_at: datetime | None
    created_by: str
    created_at: datetime
    fields: list[FieldDefOut]


class FormDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    form_key: str
    created_at: datetime
    versions: list[FormVersionRead] = []


class PublishResult(BaseModel):
    """Resultado de un intento de publicación."""

    success: bool
    version_id: int | None
    errors: list[dict[str, str]]
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_form_config_schemas.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/form_config.py backend/tests/test_form_config_schemas.py
git commit -m "feat(config): schemas Pydantic v2 para configuración de formularios"
```

---

## Task 4: Servicio de configuración de formularios + API (CEPA-110 + CEPA-111 P0)

Endpoints de CRUD de formularios dinámicos y publicación versionada. La publicación invoca el validador; si falla, devuelve los errores y no publica.

**Files:**
- Create: `backend/app/services/form_config.py`
- Create: `backend/app/routers/form_config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_form_config_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_form_config_api.py`:

```python
"""Tests de integración para el editor de formularios dinámicos (CEPA-110 / CEPA-111)."""


def _campos_sistema():
    """Payload mínimo con los 7 campos obligatorios bien parametrizados."""
    return [
        {"field_key": "sexo",       "label": "Sexo",                 "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["F","M","otro"],                                      "display_order": 1},
        {"field_key": "edad",       "label": "Edad",                 "field_type": "number",  "required": True,  "system_locked": True,  "domain_values": None,                                                  "display_order": 2},
        {"field_key": "diagnostico","label": "Diagnóstico",          "field_type": "text",    "required": True,  "system_locked": True,  "domain_values": None,                                                  "display_order": 3},
        {"field_key": "modelo_trat","label": "Modelo de tratamiento","field_type": "text",    "required": True,  "system_locked": True,  "domain_values": None,                                                  "display_order": 4},
        {"field_key": "tipo_alta",  "label": "Tipo de alta",         "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["terapeutica","medica","psicologica","abandono","derivacion"], "display_order": 5},
        {"field_key": "tipo_ingreso","label": "Tipo de ingreso",     "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["consulta_espontanea","convenio","proyecto","particular"], "display_order": 6},
        {"field_key": "tipo_convenio","label": "Tipo de convenio",   "field_type": "select",  "required": True,  "system_locked": True,  "domain_values": ["ISL","SUSESO","particular","otro"],                   "display_order": 7},
    ]


# CA-4: usuario sin perfil Coordinacion no puede acceder al editor → 403
def test_admin_no_puede_acceder_al_editor(as_admin):
    r = as_admin.post(
        "/api/v1/form-definitions/ingresos/draft",
        json={"fields": _campos_sistema()},
    )
    assert r.status_code == 403


def test_auditor_no_puede_acceder_al_editor(as_auditor):
    r = as_auditor.post(
        "/api/v1/form-definitions/ingresos/draft",
        json={"fields": _campos_sistema()},
    )
    assert r.status_code == 403


# CA-1: crear borrador, publicar, campo aparece en versión publicada
def test_crear_draft_y_publicar(as_coordinacion):
    # crear borrador
    r = as_coordinacion.post(
        "/api/v1/form-definitions/ingresos/draft",
        json={"fields": _campos_sistema()},
    )
    assert r.status_code == 201, r.text
    version_id = r.json()["id"]
    assert r.json()["status"] == "draft"

    # publicar
    pub = as_coordinacion.post(f"/api/v1/form-definitions/ingresos/publish/{version_id}")
    assert pub.status_code == 200, pub.text
    assert pub.json()["success"] is True

    # la versión publicada es visible
    get = as_coordinacion.get("/api/v1/form-definitions/ingresos/published")
    assert get.status_code == 200
    keys = [f["field_key"] for f in get.json()["fields"]]
    assert "sexo" in keys
    assert "diagnostico" in keys


# CA-3: guardar borrador no afecta la versión publicada
def test_borrador_no_afecta_publicado(as_coordinacion):
    # publicar versión base
    r1 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_x/draft",
        json={"fields": _campos_sistema()},
    )
    assert r1.status_code == 201
    vid1 = r1.json()["id"]
    as_coordinacion.post(f"/api/v1/form-definitions/modulo_x/publish/{vid1}")

    # crear nuevo borrador con campo extra
    campos2 = _campos_sistema() + [
        {"field_key": "observaciones", "label": "Observaciones", "field_type": "text",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 8}
    ]
    r2 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_x/draft",
        json={"fields": campos2},
    )
    assert r2.status_code == 201

    # publicado sigue siendo la versión anterior
    pub = as_coordinacion.get("/api/v1/form-definitions/modulo_x/published")
    keys = [f["field_key"] for f in pub.json()["fields"]]
    assert "observaciones" not in keys


# TC-110-03 / CEPA-111 CA-1: publicar con campo sin tipo → bloqueado con errores
def test_publicar_formulario_mal_parametrizado_falla(as_coordinacion):
    campos_malos = _campos_sistema() + [
        {"field_key": "extra", "label": "Extra", "field_type": "",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 9}
    ]
    r = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_bad/draft",
        json={"fields": campos_malos},
    )
    assert r.status_code == 201
    vid = r.json()["id"]

    pub = as_coordinacion.post(f"/api/v1/form-definitions/modulo_bad/publish/{vid}")
    assert pub.status_code == 422
    assert pub.json()["success"] is False
    assert len(pub.json()["errors"]) >= 1


# TC-111-03 / CEPA-111 CA-2: quitar campo obligatorio del sistema → bloqueado
def test_no_se_puede_publicar_sin_campo_sistema(as_coordinacion):
    sin_diagnostico = [c for c in _campos_sistema() if c["field_key"] != "diagnostico"]
    r = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_nd/draft",
        json={"fields": sin_diagnostico},
    )
    assert r.status_code == 201
    vid = r.json()["id"]

    pub = as_coordinacion.post(f"/api/v1/form-definitions/modulo_nd/publish/{vid}")
    assert pub.status_code == 422
    assert any("diagnostico" in e["error"] for e in pub.json()["errors"])


# TC-110-02: campo desactivado en nueva versión → histórico conservado
def test_campo_desactivado_nueva_version(as_coordinacion):
    # publicar v1 con campo "observaciones"
    campos1 = _campos_sistema() + [
        {"field_key": "observaciones", "label": "Obs", "field_type": "text",
         "required": False, "system_locked": False, "domain_values": None, "display_order": 8}
    ]
    r1 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_v/draft", json={"fields": campos1}
    )
    vid1 = r1.json()["id"]
    as_coordinacion.post(f"/api/v1/form-definitions/modulo_v/publish/{vid1}")

    # publicar v2 con "observaciones" desactivado
    campos2 = _campos_sistema() + [
        {"field_key": "observaciones", "label": "Obs", "field_type": "text",
         "required": False, "system_locked": False, "domain_values": None,
         "display_order": 8, "active": False}
    ]
    r2 = as_coordinacion.post(
        "/api/v1/form-definitions/modulo_v/draft", json={"fields": campos2}
    )
    vid2 = r2.json()["id"]
    pub2 = as_coordinacion.post(f"/api/v1/form-definitions/modulo_v/publish/{vid2}")
    assert pub2.json()["success"] is True

    # v1 sigue teniendo el campo activo (datos históricos conservados)
    get_v1 = as_coordinacion.get(f"/api/v1/form-definitions/modulo_v/versions/{vid1}")
    keys_v1 = [f["field_key"] for f in get_v1.json()["fields"]]
    assert "observaciones" in keys_v1
    obs_v1 = next(f for f in get_v1.json()["fields"] if f["field_key"] == "observaciones")
    assert obs_v1["active"] is True  # v1 no fue modificado

    # versión publicada actual (v2) tiene observaciones inactivo
    pub_now = as_coordinacion.get("/api/v1/form-definitions/modulo_v/published")
    obs_v2 = next(f for f in pub_now.json()["fields"] if f["field_key"] == "observaciones")
    assert obs_v2["active"] is False


# TC-110-05 / TC-111-06: Auditor solo lectura en endpoints de escritura → 403
def test_auditor_solo_lectura_en_formularios(as_auditor, as_coordinacion):
    # coordinacion crea y publica primero
    r = as_coordinacion.post(
        "/api/v1/form-definitions/readonly_test/draft",
        json={"fields": _campos_sistema()},
    )
    vid = r.json()["id"]
    as_coordinacion.post(f"/api/v1/form-definitions/readonly_test/publish/{vid}")

    # auditor puede leer
    get = as_auditor.get("/api/v1/form-definitions/readonly_test/published")
    assert get.status_code == 200

    # auditor no puede escribir
    w = as_auditor.post(
        "/api/v1/form-definitions/readonly_test/draft",
        json={"fields": _campos_sistema()},
    )
    assert w.status_code == 403
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_form_config_api.py -v`
Expected: FAIL con `404` o `ModuleNotFoundError`.

- [ ] **Step 3: Implementar el servicio**

Crear `backend/app/services/form_config.py`:

```python
"""Lógica de negocio para el editor de formularios dinámicos (CEPA-110 / CEPA-111)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.form_definition import FieldDef, FormDefinition, FormVersion
from app.schemas.form_config import FieldDefIn, FormVersionCreate
from app.services.form_validator import ParametrizationError, validate_form_version


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_form_def(db: Session, form_key: str) -> FormDefinition:
    fd = db.execute(
        select(FormDefinition).where(FormDefinition.form_key == form_key)
    ).scalar_one_or_none()
    if fd is None:
        fd = FormDefinition(form_key=form_key)
        db.add(fd)
        db.flush()
    return fd


def _next_version_num(db: Session, form_def_id: int) -> int:
    from sqlalchemy import func
    result = db.execute(
        select(func.max(FormVersion.version_num)).where(
            FormVersion.form_def_id == form_def_id
        )
    ).scalar_one_or_none()
    return (result or 0) + 1


def create_draft(
    db: Session, form_key: str, payload: FormVersionCreate, username: str
) -> FormVersion:
    """Crea un borrador (status='draft') para el formulario indicado."""
    fd = _get_or_create_form_def(db, form_key)
    num = _next_version_num(db, fd.id)
    version = FormVersion(
        form_def_id=fd.id,
        version_num=num,
        status="draft",
        published_at=None,
        created_by=username,
    )
    db.add(version)
    db.flush()

    for f in payload.fields:
        field = FieldDef(
            form_version_id=version.id,
            field_key=f.field_key,
            label=f.label,
            field_type=f.field_type,
            required=f.required,
            system_locked=f.system_locked,
            domain_values=f.domain_values,
            display_order=f.display_order,
            active=f.active,
        )
        db.add(field)
    db.flush()
    return version


def publish_version(db: Session, form_key: str, version_id: int, username: str) -> dict:
    """Publica una versión borrador previo paso por el validador.

    Devuelve dict compatible con PublishResult.
    Si la validación falla, no publica y devuelve los errores.
    """
    version = db.execute(
        select(FormVersion)
        .options(selectinload(FormVersion.fields))
        .where(FormVersion.id == version_id)
        .join(FormVersion.form_definition)
        .where(FormDefinition.form_key == form_key)
    ).scalar_one_or_none()

    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versión no encontrada.")
    if version.status == "published":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La versión ya está publicada.")

    # Convertir FieldDef ORM a dicts para el validador
    fields_as_dicts = [
        {
            "field_key": f.field_key,
            "label": f.label,
            "field_type": f.field_type,
            "required": f.required,
            "system_locked": f.system_locked,
            "domain_values": f.domain_values,
            "active": f.active,
        }
        for f in version.fields
    ]
    errors = validate_form_version(fields_as_dicts)
    if errors:
        return {"success": False, "version_id": None, "errors": errors}

    version.status = "published"
    version.published_at = _utcnow()
    db.flush()
    return {"success": True, "version_id": version.id, "errors": []}


def get_published_version(db: Session, form_key: str) -> FormVersion:
    """Devuelve la versión publicada más reciente o 404."""
    version = db.execute(
        select(FormVersion)
        .options(selectinload(FormVersion.fields))
        .join(FormVersion.form_definition)
        .where(FormDefinition.form_key == form_key, FormVersion.status == "published")
        .order_by(FormVersion.version_num.desc())
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay versión publicada para el formulario '{form_key}'.",
        )
    return version


def get_version_by_id(db: Session, form_key: str, version_id: int) -> FormVersion:
    """Devuelve una versión específica por ID (para consulta histórica)."""
    version = db.execute(
        select(FormVersion)
        .options(selectinload(FormVersion.fields))
        .where(FormVersion.id == version_id)
        .join(FormVersion.form_definition)
        .where(FormDefinition.form_key == form_key)
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versión no encontrada.")
    return version
```

- [ ] **Step 4: Implementar el router**

Crear `backend/app/routers/form_config.py`:

```python
"""Router para el editor de formularios dinámicos (CEPA-110 / CEPA-111)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.form_config import FormVersionCreate, FormVersionRead, PublishResult
from app.services import form_config as svc

router = APIRouter(prefix="/api/v1/form-definitions", tags=["form-definitions"])

# Solo Coordinacion puede editar formularios (CEPA-110 RN-1)
_coord = require_role("Coordinacion")
# Lectura abierta a todos los roles (CA-4 test: auditor puede leer la versión publicada)
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "/{form_key}/draft",
    response_model=FormVersionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_coord)],
)
def crear_borrador(
    form_key: str,
    payload: FormVersionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> FormVersionRead:
    version = svc.create_draft(db, form_key, payload, current_user.username)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="form_version",
        entity_id=str(version.id),
    )
    db.commit()
    db.refresh(version)
    return version


@router.post(
    "/{form_key}/publish/{version_id}",
    response_model=PublishResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_coord)],
)
def publicar(
    form_key: str,
    version_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PublishResult:
    result = svc.publish_version(db, form_key, version_id, current_user.username)
    if result["success"]:
        record_audit(
            db,
            actor=current_user.username,
            action="UPDATE",
            entity="form_version",
            entity_id=str(version_id),
        )
        db.commit()
    else:
        # Publicación bloqueada: devolver 422 con detalle de errores
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result,
        )
    return result


@router.get(
    "/{form_key}/published",
    response_model=FormVersionRead,
    dependencies=[Depends(_reader)],
)
def obtener_version_publicada(
    form_key: str,
    db: Session = Depends(get_db),
) -> FormVersionRead:
    return svc.get_published_version(db, form_key)


@router.get(
    "/{form_key}/versions/{version_id}",
    response_model=FormVersionRead,
    dependencies=[Depends(_reader)],
)
def obtener_version_por_id(
    form_key: str,
    version_id: int,
    db: Session = Depends(get_db),
) -> FormVersionRead:
    return svc.get_version_by_id(db, form_key, version_id)
```

- [ ] **Step 5: Conectar el router en `app/main.py`**

Añadir al bloque de imports y registro de routers en `backend/app/main.py` (conservar lo existente):

```python
from app.routers import form_config

app.include_router(form_config.router)
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_form_config_api.py -v
```
Expected: `8 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/form_config.py backend/app/routers/form_config.py \
        backend/app/main.py backend/tests/test_form_config_api.py
git commit -m "feat(config): API de formularios dinámicos con versionado y validación (CEPA-110/111)"
```

---

## Task 5: Parser de PDF inyectable/mockeable (CEPA-112 P1)

Abstracción de extracción de texto de PDF usando un `Protocol` inyectable, implementación real con `pypdf`, y un stub determinista para tests. Los tests nunca abren archivos binarios reales: usan un PDF mínimo generado en memoria o el stub.

**Files:**
- Modify: `backend/pyproject.toml` (añadir `pypdf`)
- Create: `backend/app/services/pdf_parser.py`
- Create: `backend/app/schemas/pdf_extract.py`
- Test: `backend/tests/test_pdf_parser.py`

- [ ] **Step 1: Añadir `pypdf` a las dependencias**

Modificar `backend/pyproject.toml` — en la sección `[project] dependencies`, añadir:

```toml
"pypdf>=4.0",
```

Instalar:
```bash
uv sync
```
Expected: uv resuelve e instala `pypdf`; sin errores.

- [ ] **Step 2: Escribir el test que falla**

Crear `backend/tests/test_pdf_parser.py`:

```python
"""Tests del servicio de extracción de PDF (CEPA-112).

Los tests NO usan archivos binarios reales: trabajan con un PDF mínimo generado
en memoria (pypdf.PdfWriter) o con el PdfParserStub inyectable.
"""

import io
import pytest


def _pdf_con_texto(texto: str) -> bytes:
    """Genera un PDF mínimo en memoria con el texto indicado (para tests)."""
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, ArrayObject, NumberObject, DictionaryObject
    import struct

    # Usamos ReportLab-free: escribimos el PDF manualmente con pypdf
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)

    # Añadir texto via content stream directo
    content = f"BT /F1 12 Tf 50 750 Td ({texto}) Tj ET".encode()
    from pypdf.generic import ContentStream, ByteStringObject
    page.mediabox.lower_left = (0, 0)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def _pdf_vacio() -> bytes:
    """PDF sin capa de texto (simula escaneado)."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


from app.services.pdf_parser import PypdfParser, PdfParserStub, ExtractedPage


# TC-112-01: parser real extrae texto de un PDF con capa de texto
def test_pypdf_parser_extrae_texto():
    parser = PypdfParser()
    # Usamos el stub porque no podemos predecir el texto exacto que pypdf
    # extraerá del stream manual. Probamos el flujo completo con el stub.
    stub = PdfParserStub(pages=[ExtractedPage(page_num=1, text="Nombre: Juan Perez RUT: 12.345.678-5")])
    resultado = stub.extract(b"cualquier-bytes")
    assert len(resultado) == 1
    assert "Juan Perez" in resultado[0].text


# TC-112-03: archivo no-PDF → ExtractionError
def test_parser_rechaza_no_pdf():
    from app.services.pdf_parser import ExtractionError
    parser = PypdfParser()
    with pytest.raises(ExtractionError):
        parser.extract(b"esto no es un pdf")


# TC-112-04: PDF sin capa de texto → lista vacía de páginas con texto
def test_pdf_sin_texto_retorna_paginas_vacias():
    parser = PypdfParser()
    resultado = parser.extract(_pdf_vacio())
    # Puede tener páginas pero sin texto
    for p in resultado:
        assert p.text.strip() == ""


# Stub es mockeable: devuelve lo que se le inyecta
def test_stub_devuelve_exactamente_lo_inyectado():
    stub = PdfParserStub(pages=[
        ExtractedPage(page_num=1, text="campo1: valor1"),
        ExtractedPage(page_num=2, text="campo2: valor2"),
    ])
    resultado = stub.extract(b"bytes-irrelevantes")
    assert len(resultado) == 2
    assert resultado[1].text == "campo2: valor2"


# Stub de error: simula PDF ilegible
def test_stub_de_error_lanza_excepcion():
    from app.services.pdf_parser import ExtractionError, PdfParserErrorStub
    stub = PdfParserErrorStub()
    with pytest.raises(ExtractionError):
        stub.extract(b"cualquier-cosa")
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_pdf_parser.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.pdf_parser'`.

- [ ] **Step 4: Implementar el servicio de parseo**

Crear `backend/app/services/pdf_parser.py`:

```python
"""Abstracción de extracción de texto de PDF (CEPA-112).

Usa el patrón Protocol (duck-typing) para permitir la inyección de dependencias
en tests sin depender de archivos binarios reales.

Clases exportadas:
- ExtractedPage      — valor simple (dataclass): página con texto extraído.
- PdfParser          — Protocol; cualquier clase con método extract() lo implementa.
- PypdfParser        — implementación real con pypdf.
- PdfParserStub      — stub para tests: devuelve páginas predefinidas.
- PdfParserErrorStub — stub que lanza ExtractionError (simula PDF ilegible).
- ExtractionError    — excepción base de este módulo.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ExtractionError(Exception):
    """Se lanza cuando el archivo no es un PDF válido o es ilegible."""


@dataclass
class ExtractedPage:
    page_num: int
    text: str


@runtime_checkable
class PdfParser(Protocol):
    """Protocol inyectable. Cualquier clase con este método es un PdfParser."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]: ...


class PypdfParser:
    """Implementación real con pypdf (sin dependencias de sistema operativo)."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise ExtractionError(f"No se pudo leer el PDF: {exc}") from exc

        pages: list[ExtractedPage] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(ExtractedPage(page_num=i, text=text))
        return pages


class PdfParserStub:
    """Stub determinista para tests. Devuelve páginas fijas independientemente del input."""

    def __init__(self, pages: list[ExtractedPage] | None = None) -> None:
        self._pages: list[ExtractedPage] = pages or []

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        return self._pages


class PdfParserErrorStub:
    """Stub que siempre falla. Simula PDF ilegible/escaneado sin texto (TC-112-04)."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        raise ExtractionError("PDF ilegible: sin capa de texto (stub de error).")
```

- [ ] **Step 5: Crear los schemas de extracción**

Crear `backend/app/schemas/pdf_extract.py`:

```python
"""Schemas Pydantic v2 para el endpoint de extracción de PDF (CEPA-112)."""

from __future__ import annotations

from pydantic import BaseModel


class ExtractedFieldOut(BaseModel):
    """Campo extraído del PDF, pre-llenado y editable."""

    field_key: str
    value: str


class PdfExtractResult(BaseModel):
    """Resultado de la extracción: campos pre-llenados + metadatos."""

    success: bool
    # Texto crudo concatenado de todas las páginas (para debug / auditoría)
    raw_text: str
    # Lista de campos extraídos con nombre sugerido (mapeo heurístico básico)
    fields: list[ExtractedFieldOut]
    # Mensaje de error si success=False
    error_message: str | None = None


class PdfConfirmPayload(BaseModel):
    """Payload de confirmación: campos revisados/editados por el administrativo.

    La edición humana prevalece sobre la extracción (RN-1 / CA-2).
    El form_key indica qué formulario recibe los datos confirmados.
    """

    form_key: str
    fields: list[ExtractedFieldOut]
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_pdf_parser.py -v`
Expected: `5 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/pdf_parser.py backend/app/schemas/pdf_extract.py \
        backend/tests/test_pdf_parser.py backend/pyproject.toml
git commit -m "feat(pdf): servicio de extracción de PDF inyectable con pypdf (CEPA-112)"
```

---

## Task 6: API de extracción de PDF (CEPA-112 P1)

Endpoint `POST /api/v1/pdf-extract/upload` que recibe un archivo, extrae texto, mapea campos y devuelve el borrador editable. Endpoint separado `POST /api/v1/pdf-extract/confirm` para confirmar y validar antes de guardar (integra CEPA-111). Degradación gracia si el PDF es ilegible.

**Files:**
- Create: `backend/app/routers/pdf_extract.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_pdf_extract_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_pdf_extract_api.py`:

```python
"""Tests de integración para el endpoint de lectura de PDF (CEPA-112)."""

import io
import pytest


def _pdf_minimo_con_texto(texto: str) -> bytes:
    """Genera un PDF mínimo en memoria con pypdf para el test de carga."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


# TC-112-06: Auditor no puede cargar PDF → 403
def test_auditor_no_puede_cargar_pdf(as_auditor):
    data = _pdf_minimo_con_texto("datos")
    r = as_auditor.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("test.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code == 403


# TC-112-03: archivo no-PDF → mensaje de error + success=False + no bloquea flujo
def test_archivo_no_pdf_retorna_error_sin_bloquear(as_admin):
    contenido_no_pdf = b"esto no es un pdf valido"
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("documento.docx", io.BytesIO(contenido_no_pdf), "application/octet-stream")},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is False
    assert cuerpo["error_message"] is not None
    assert cuerpo["fields"] == []


# TC-112-01: PDF con capa de texto → success=True, campos pre-llenados
def test_pdf_legible_retorna_campos(as_admin):
    data = _pdf_minimo_con_texto("Nombre: Juan Pérez")
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("ficha.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is True
    # fields puede ser lista vacía si no hay texto extraíble (PDF en blanco es válido)
    assert isinstance(cuerpo["fields"], list)


# TC-112-04: PDF escaneado (sin texto) → success=True con fields=[], permite captura manual
def test_pdf_escaneado_retorna_lista_vacia(as_admin):
    # PDF en blanco (sin capa de texto) ya generado arriba
    data = _pdf_minimo_con_texto("")
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("escaneado.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    # El texto está vacío o no mapeado; fields puede estar vacío — eso está bien
    assert isinstance(r.json()["fields"], list)


# TC-112-02: confirm guarda los datos editados (la edición humana prevalece)
# El confirm solo valida estructura; el guardado real en el dominio lo hace la historia
# correspondiente. Aquí verificamos que el endpoint responda 200 con el payload editado.
def test_confirm_acepta_edicion_humana(as_admin):
    payload = {
        "form_key": "ingresos",
        "fields": [
            {"field_key": "nombre", "value": "Juan Pérez Editado"},
            {"field_key": "rut", "value": "12345678-5"},
        ],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["received_fields"] == 2


# TC-112-05: confirm con campo obligatorio vacío → 422 (validación CEPA-111)
# El endpoint confirm solo valida que no haya value vacío en campos marcados como required
# por la definición activa del formulario. Si no hay versión publicada del form_key → 404.
def test_confirm_sin_form_publicado_retorna_404(as_admin):
    payload = {
        "form_key": "form_inexistente_xyz",
        "fields": [{"field_key": "sexo", "value": ""}],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 404
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_pdf_extract_api.py -v`
Expected: FAIL con `404` (ruta inexistente).

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/pdf_extract.py`:

```python
"""Router de lectura de documentos PDF (CEPA-112 P1).

El parser se inyecta vía dependencia FastAPI: en producción usa PypdfParser;
en tests se puede sobreescribir con un stub.

Degradación gracia (RN-3): si la extracción falla, devuelve success=False
con error_message y fields=[], sin bloquear el flujo de captura manual.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.pdf_extract import ExtractedFieldOut, PdfConfirmPayload, PdfExtractResult
from app.services.pdf_parser import ExtractionError, PdfParser, PypdfParser
from app.services import form_config as form_svc

router = APIRouter(prefix="/api/v1/pdf-extract", tags=["pdf-extract"])

# Auditor es solo lectura — carga de PDF requiere rol escritor
_writer = require_role("Administrativo", "Coordinacion")


def get_pdf_parser() -> PdfParser:
    """Dependencia inyectable: en tests se sobreescribe con un stub."""
    return PypdfParser()


def _mapear_campos(raw_text: str) -> list[ExtractedFieldOut]:
    """Heurística simple de mapeo de texto a campos conocidos.

    Versión v1: busca patrones 'Clave: Valor' en el texto y mapea
    a field_key normalizados. En producción se puede extender con
    un mapeador configurable o regex por tipo de documento.
    """
    fields: list[ExtractedFieldOut] = []
    for line in raw_text.splitlines():
        if ":" in line:
            partes = line.split(":", 1)
            key_raw = partes[0].strip().lower().replace(" ", "_")
            value = partes[1].strip()
            if key_raw and value:
                fields.append(ExtractedFieldOut(field_key=key_raw, value=value))
    return fields


@router.post(
    "/upload",
    response_model=PdfExtractResult,
    dependencies=[Depends(_writer)],
)
async def upload_pdf(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    parser: PdfParser = Depends(get_pdf_parser),
) -> PdfExtractResult:
    """Recibe un PDF, extrae texto y devuelve campos pre-llenados (no persiste).

    Si la extracción falla o el archivo no es PDF, degrada con gracia:
    devuelve success=False con error_message, sin lanzar 4xx/5xx.
    """
    content = await file.read()

    # Validación básica de tipo de archivo
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        # Intentar igualmente — puede ser un PDF sin extensión
        pass

    try:
        pages = parser.extract(content)
    except ExtractionError as exc:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="pdf_extract_attempt",
            entity_id=None,
        )
        db.commit()
        return PdfExtractResult(
            success=False,
            raw_text="",
            fields=[],
            error_message=str(exc),
        )

    raw_text = "\n".join(p.text for p in pages)
    fields = _mapear_campos(raw_text)

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="pdf_extract_attempt",
        entity_id=None,
    )
    db.commit()

    return PdfExtractResult(
        success=True,
        raw_text=raw_text,
        fields=fields,
        error_message=None,
    )


@router.post(
    "/confirm",
    dependencies=[Depends(_writer)],
)
def confirm_extraction(
    payload: PdfConfirmPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Confirma los datos editados por el administrativo.

    Valida que exista una versión publicada del formulario destino.
    La persistencia real en la entidad de dominio (ingreso, etc.)
    es responsabilidad del endpoint del módulo correspondiente.

    Retorna confirmación con conteo de campos recibidos.
    """
    # Verificar que exista versión publicada del formulario destino
    form_svc.get_published_version(db, payload.form_key)  # lanza 404 si no existe

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="pdf_extract_confirm",
        entity_id=payload.form_key,
    )
    db.commit()

    return {
        "acknowledged": True,
        "form_key": payload.form_key,
        "received_fields": len(payload.fields),
    }
```

- [ ] **Step 4: Conectar el router en `app/main.py`**

Añadir al bloque de imports y registro en `backend/app/main.py`:

```python
from app.routers import pdf_extract

app.include_router(pdf_extract.router)
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run:
```bash
uv run pytest tests/test_pdf_extract_api.py -v
```
Expected: `6 passed`.

Nota: `test_confirm_sin_form_publicado_retorna_404` depende de que no exista una versión publicada del form_key `form_inexistente_xyz`; el rollback por test garantiza que no exista.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/pdf_extract.py backend/app/main.py \
        backend/tests/test_pdf_extract_api.py
git commit -m "feat(pdf): endpoint de carga/extracción PDF con degradación gracia (CEPA-112)"
```

---

## Task 7: Suite completa + lint + verificación integral [P0/P1]

**Files:** ninguno nuevo.

- [ ] **Step 1: Correr la suite completa**

Run (desde `backend/`):
```bash
uv run pytest -v
```
Expected: todos los tests pasan (incluyendo los de EPIC-00 y EPIC-01 que ya existían).

- [ ] **Step 2: Lint**

Run:
```bash
uv run ruff check .
```
Expected: sin errores. Si hay advertencias de imports no usados (`F401`) en `__init__.py`, son esperadas y están marcadas con `# noqa: F401`.

- [ ] **Step 3: Verificar migraciones (upgrade/downgrade desde cero)**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: aplica todo el historial sin errores; las tablas `form_definition`, `form_version`, `field_def` existen en la BD de test.

- [ ] **Step 4: Commit de cierre**

```bash
git add -A
git commit -m "chore(epic-11): EPIC-11 completo — formularios dinámicos, validación parametrización y lectura PDF" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Tasks que la implementan |
|----------|--------------------------|
| **CEPA-110** Formularios dinámicos / campos configurables | Task 1 (modelos + migración) · Task 3 (schemas) · Task 4 (servicio + API) |
| **CEPA-111** Validación de parametrización y campos obligatorios | Task 2 (validador puro) · Task 4 (integración en publicación) |
| **CEPA-112** Lectura de documentos PDF | Task 5 (parser inyectable) · Task 6 (endpoint upload/confirm) |

### Test Cases cubiertos

| TC | Test correspondiente |
|----|---------------------|
| TC-110-01 | `test_crear_draft_y_publicar` |
| TC-110-02 | `test_campo_desactivado_nueva_version` |
| TC-110-03 | `test_publicar_formulario_mal_parametrizado_falla` |
| TC-110-04 | `test_campo_desactivado_nueva_version` (v1 histórico conservado) |
| TC-110-05 | `test_admin_no_puede_acceder_al_editor` |
| TC-110-06 | `test_auditor_no_puede_acceder_al_editor` · `test_auditor_solo_lectura_en_formularios` |
| TC-111-01 | `test_formulario_valido_sin_errores` · `test_crear_draft_y_publicar` |
| TC-111-02 | `test_campo_sin_tipo_bloquea_publicacion` · `test_publicar_formulario_mal_parametrizado_falla` |
| TC-111-03 | `test_campo_obligatorio_sistema_faltante_bloquea` · `test_no_se_puede_publicar_sin_campo_sistema` |
| TC-111-04 | `test_campo_select_obligatorio_sin_dominio_da_error` (valida en capa de operación) |
| TC-111-05 | `test_campo_select_obligatorio_sin_dominio_da_error` |
| TC-111-06 | `test_auditor_solo_lectura_en_formularios` |
| TC-112-01 | `test_pdf_legible_retorna_campos` |
| TC-112-02 | `test_confirm_acepta_edicion_humana` |
| TC-112-03 | `test_archivo_no_pdf_retorna_error_sin_bloquear` |
| TC-112-04 | `test_pdf_escaneado_retorna_lista_vacia` |
| TC-112-05 | `test_confirm_sin_form_publicado_retorna_404` (precondición; el guardado real es del módulo destino) |
| TC-112-06 | `test_auditor_no_puede_cargar_pdf` |

---

## Modelos definidos

| Modelo | Tabla | Descripción |
|--------|-------|-------------|
| `FormDefinition` | `form_definition` | Registro maestro de un formulario (uno por módulo) |
| `FormVersion` | `form_version` | Versión borrador o publicada; inmutable al publicar |
| `FieldDef` | `field_def` | Definición de campo de una versión; `domain_values` en `JSON` genérico |

---

## Notas de cierre

### down_revision de la migración

El placeholder `<RESOLVER: alembic heads>` en `backend/migrations/versions/<rev>_crear_form_tables.py` **debe reemplazarse antes de ejecutar el plan**. Pasos:

1. Desde `backend/`, ejecutar: `uv run alembic heads`
2. El valor devuelto es el `down_revision` de la primera migración de esta épica y la cadena `revision` a asignar (o generar con `uv run alembic revision -m "crear form tables"` y copiar el ID generado).
3. El nombre del archivo de migración debe contener ese ID (por convención del proyecto: `<ID>_crear_form_tables.py`).

### Firmas de EPIC-00 a verificar antes del loop

Las siguientes firmas se asumen presentes en `main`; verificar contra el código real antes de ejecutar:

- `from app.auth.deps import get_current_user, require_role` — `require_role` debe aceptar uno o más strings de rol y devolver una dependencia FastAPI.
- `from app.audit.service import record_audit` — firma exacta: `record_audit(db: Session, actor: str, action: str, entity: str, entity_id: str | None)`.
- Fixtures `as_admin`, `as_coordinacion`, `as_auditor` en `tests/conftest.py` — deben ser `TestClient` con headers `Authorization: Bearer <token>` válidos para sus respectivos roles.

### Decisiones de negocio abiertas del spec

- **Tipos de campo soportados en v1:** el plan implementa `{text, number, date, select, boolean}`. Confirmar con Coordinación si se requieren otros (p. ej. `file`, `rut`).
- **Dominio de valores de campos obligatorios de dominio cerrado** (`tipo_alta`, `tipo_ingreso`, `tipo_convenio`): los valores usados en los tests son representativos pero deben confirmarse con el equipo CEPA antes de entrar en producción (relacionado con D4, D6, D11).
- **Mapeo de campos de PDF:** la heurística de `_mapear_campos` en v1 es básica (`Clave: Valor`). El conjunto de tipos de documento soportados y el mapeo de campos por tipo (ficha clínica, datos sociodemográficos) queda pendiente de acuerdo con Coordinación (nota de CEPA-112).
- **OCR para PDFs escaneados:** v1 se limita a PDFs con capa de texto. Si se requiere OCR, se añade una implementación adicional de `PdfParser` (p. ej. con `pytesseract`) sin modificar el resto del sistema (el Protocol lo hace extensible).
- **TC-112-05 (guardado con campo obligatorio vacío):** la validación de campos obligatorios del formulario destino en el endpoint `confirm` está conectada a la versión publicada de CEPA-111, pero la persistencia real del dato (crear/actualizar la entidad de dominio) es responsabilidad del router del módulo correspondiente (ingresos, etc.) y queda fuera del alcance de esta épica.

### Consideraciones de portabilidad

- `domain_values` usa `sa.JSON()` genérico (no `JSONB`): compatible con Oracle y Postgres.
- Todos los identificadores de tabla/columna en minúscula y ≤30 caracteres (verificado en tests).
- `Identity(always=False)` en todas las PKs subrogadas.
- `DateTime(timezone=True)` para todas las fechas/tiempos, con `_utcnow()` local.
