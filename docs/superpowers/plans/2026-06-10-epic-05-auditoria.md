# EPIC-05 — Auditoría (Vista Consolidada del Caso y Reportes) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar el módulo de Auditoría del Sistema CEPA: una vista consolidada de solo lectura que agrega todos los hitos de cada caso clínico (datos del caso, evaluaciones, controles, reintegro y cierre) desde los módulos fuente, y un generador de reportes filtrables y descargables para el perfil Auditor. Cubre las historias CEPA-050 y CEPA-051.

**Architecture:** Este módulo es de **pura lectura/agregación**: no crea tablas de dominio propias (no modifica datos clínicos), sino que consulta via ORM las tablas de los módulos fuente (EPIC-01..07). La vista consolidada se construye como una consulta compuesta sobre `ingreso`, `paciente`, `seguimiento`, tablas de fármacos, EPT, reintegro, controles, licencias y ODAS, retornando un DTO plano ensamblado en la capa de servicio. El reporte de auditoría es la misma lógica con filtros adicionales y un endpoint de descarga CSV. Se sigue el patrón establecido: `app/services/auditoria.py` (lógica de agregación), `app/schemas/auditoria.py` (DTOs Pydantic v2), `app/routers/auditoria.py` (endpoints `/api/v1/auditoria/...`). Los tests crean datos directamente en la BD de tests vía los modelos de los módulos fuente (se asumen existentes).

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (ORM, sin SQL específico de motor), Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`. Importa de EPIC-01..07: modelos `Paciente`, `Ingreso`, `Seguimiento`, `Oda`, `Farmaco`, `AsignacionFarmaco`, `Ept`, `Reintegro`, `Control`, `Licencia`. Fixtures de test de EPIC-00: `as_auditor`, `as_coordinacion`, `as_admin`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role` — roles `"Coordinacion"`, `"Administrativo"`, `"Auditor"`.
- `from app.audit.service import record_audit` — `record_audit(db, actor=..., action=..., entity=..., entity_id=...)`.
- Modelos de EPIC-01: `app.models.paciente.Paciente`, `app.models.ingreso.Ingreso`, `app.models.ingreso.Seguimiento`, `app.models.oda.Oda`.
- Modelos de EPIC-02: `app.models.farmaco.Farmaco`, `app.models.farmaco.AsignacionFarmaco`.
- Modelos de EPIC-03: `app.models.ept.Ept`.
- Modelos de EPIC-04: `app.models.reintegro.Reintegro`.
- Modelos de EPIC-06: `app.models.control.Control`.
- Modelos de EPIC-07: `app.models.licencia.Licencia`.
- Fixtures de test de EPIC-00: `as_auditor`, `as_coordinacion`, `as_admin`, `db_session`, `client`.

**Convención RBAC de esta épica (solo lectura):**
```python
from app.auth.deps import require_role

# Auditoría es solo lectura: Coordinacion y Auditor; Administrativo NO accede
_reader = require_role("Coordinacion", "Auditor")
```

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `backend/app/schemas/auditoria.py` | DTOs Pydantic v2: `CasoConsolidadoRead`, `FiltrosReporte`, `FilaReporteRead`, `ReporteAuditoriaRead` |
| `backend/app/services/auditoria.py` | Lógica de agregación ORM: `get_caso_consolidado`, `generar_reporte` |
| `backend/app/routers/auditoria.py` | Endpoints `/api/v1/auditoria/casos/{ingreso_id}`, `/api/v1/auditoria/casos`, `/api/v1/auditoria/reportes`, `/api/v1/auditoria/reportes/descargar` |
| `backend/app/main.py` | Registro del router de auditoría (modificación) |
| `backend/tests/test_auditoria_schemas.py` | Tests unitarios de schemas y DTOs |
| `backend/tests/test_auditoria_service.py` | Tests de la capa de servicio (lógica de filtros y agregación) |
| `backend/tests/test_auditoria_api.py` | Tests de integración end-to-end de los endpoints |

> **Nota sobre migraciones:** esta épica **no crea tablas nuevas** (es de pura lectura). No se requieren migraciones Alembic propias. Las tablas que consulta ya existen en las migraciones de EPIC-01..07.

---

## Task 1: Schemas Pydantic v2 para la vista consolidada y el reporte

Define todos los DTOs que usan las Tasks posteriores. Sin implementación de lógica — solo tipos.

**Files:**
- Create: `backend/app/schemas/auditoria.py`
- Test: `backend/tests/test_auditoria_schemas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auditoria_schemas.py`:

```python
"""Tests unitarios de los schemas de auditoría (sin BD)."""
import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auditoria import (
    CasoConsolidadoRead,
    FilaReporteRead,
    FiltrosReporte,
    ReporteAuditoriaRead,
    SeccionCierreRead,
    SeccionControlesRead,
    SeccionDatosCasoRead,
    SeccionEvaluacionesRead,
)


# ── SeccionDatosCasoRead ───────────────────────────────────────────────────

def test_seccion_datos_caso_campos_minimos():
    datos = SeccionDatosCasoRead(
        folio="2026-0123",
        numero_siniestro="SIN-2026-001",
        fecha_denuncia=datetime.date(2026, 1, 15),
        tipo_denuncia="DIAT",
        fecha_derivacion=datetime.date(2026, 1, 20),
        nombre_completo="Ana González",
        rut="123456785",
        region="Maule",
    )
    assert datos.folio == "2026-0123"
    assert datos.region == "Maule"


def test_seccion_datos_caso_campos_opcionales_son_none_por_defecto():
    datos = SeccionDatosCasoRead(
        folio="2026-0124",
        numero_siniestro=None,
        fecha_denuncia=None,
        tipo_denuncia=None,
        fecha_derivacion=None,
        nombre_completo="Pedro Díaz",
        rut="87654321K",
        region=None,
    )
    assert datos.numero_siniestro is None
    assert datos.fecha_derivacion is None


# ── SeccionEvaluacionesRead ────────────────────────────────────────────────

def test_seccion_evaluaciones_diagnoticos_separados():
    ev = SeccionEvaluacionesRead(
        fecha_eval_medica=datetime.date(2026, 2, 1),
        fecha_eval_psicologica=datetime.date(2026, 2, 5),
        fecha_calificacion_reca=datetime.date(2026, 3, 1),
        diagnostico_inicial="F32.0 Episodio depresivo leve",
        diagnostico_post_reca="F33.1 Trastorno depresivo recurrente",
        numero_sesiones_evaluacion=3,
    )
    assert ev.diagnostico_inicial != ev.diagnostico_post_reca
    assert ev.fecha_calificacion_reca == datetime.date(2026, 3, 1)


def test_seccion_evaluaciones_todos_opcionales():
    ev = SeccionEvaluacionesRead(
        fecha_eval_medica=None,
        fecha_eval_psicologica=None,
        fecha_calificacion_reca=None,
        diagnostico_inicial=None,
        diagnostico_post_reca=None,
        numero_sesiones_evaluacion=0,
    )
    assert ev.numero_sesiones_evaluacion == 0


# ── SeccionControlesRead ───────────────────────────────────────────────────

def test_seccion_controles_campos_completos():
    ctrl = SeccionControlesRead(
        fecha_primera_consulta_medica=datetime.date(2026, 3, 10),
        fecha_primera_consulta_psicologica=datetime.date(2026, 3, 12),
        n_sesiones_medicas=5,
        n_sesiones_psicologicas=8,
        n_sesiones_ampliacion=2,
        reintegro_parcial=True,
        fecha_reintegro_parcial=datetime.date(2026, 5, 1),
        reintegro_total=False,
        fecha_reintegro_total=None,
    )
    assert ctrl.reintegro_parcial is True
    assert ctrl.fecha_reintegro_total is None


# ── SeccionCierreRead ──────────────────────────────────────────────────────

def test_seccion_cierre_pendiente_cuando_sin_altas():
    """CA-5 / TC-050-04: caso en tratamiento sin altas registradas."""
    cierre = SeccionCierreRead(
        alta_medica=False,
        fecha_alta_medica=None,
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general=None,
        observaciones=None,
    )
    assert cierre.alta_medica is False
    assert cierre.estado_general is None


def test_seccion_cierre_con_altas_parciales():
    cierre = SeccionCierreRead(
        alta_medica=True,
        fecha_alta_medica=datetime.date(2026, 6, 1),
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general="cerrado",
        observaciones="Alta médica emitida; psicología en curso.",
    )
    assert cierre.alta_medica is True
    assert cierre.alta_psicologica is False


# ── CasoConsolidadoRead ────────────────────────────────────────────────────

def test_caso_consolidado_contiene_todas_las_secciones():
    caso = CasoConsolidadoRead(
        ingreso_id=1,
        datos_caso=SeccionDatosCasoRead(
            folio="2026-0123",
            numero_siniestro="SIN-001",
            fecha_denuncia=datetime.date(2026, 1, 15),
            tipo_denuncia="DIAT",
            fecha_derivacion=datetime.date(2026, 1, 20),
            nombre_completo="Ana González",
            rut="123456785",
            region="Maule",
        ),
        evaluaciones=SeccionEvaluacionesRead(
            fecha_eval_medica=None,
            fecha_eval_psicologica=None,
            fecha_calificacion_reca=None,
            diagnostico_inicial="F32.0",
            diagnostico_post_reca=None,
            numero_sesiones_evaluacion=0,
        ),
        controles=SeccionControlesRead(
            fecha_primera_consulta_medica=None,
            fecha_primera_consulta_psicologica=None,
            n_sesiones_medicas=0,
            n_sesiones_psicologicas=0,
            n_sesiones_ampliacion=0,
            reintegro_parcial=False,
            fecha_reintegro_parcial=None,
            reintegro_total=False,
            fecha_reintegro_total=None,
        ),
        cierre=SeccionCierreRead(
            alta_medica=False,
            fecha_alta_medica=None,
            alta_psicologica=False,
            fecha_alta_psicologica=None,
            alta_terapeutica=False,
            fecha_alta_terapeutica=None,
            estado_general=None,
            observaciones=None,
        ),
    )
    assert caso.ingreso_id == 1
    assert caso.datos_caso.folio == "2026-0123"
    assert caso.cierre.alta_medica is False


# ── FiltrosReporte ─────────────────────────────────────────────────────────

def test_filtros_periodo_obligatorio():
    """RN-2: el período es obligatorio para acotar el universo del reporte."""
    with pytest.raises(ValidationError):
        FiltrosReporte(fecha_desde=None, fecha_hasta=None)


def test_filtros_periodo_minimo_valido():
    f = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    assert f.fecha_desde == datetime.date(2026, 1, 1)
    assert f.diagnostico is None
    assert f.profesional is None
    assert f.estado_caso is None
    assert f.programa is None
    assert f.tipo_alta is None
    assert f.region is None
    assert f.tipo_ingreso is None


def test_filtros_todos_los_campos():
    f = FiltrosReporte(
        fecha_desde=datetime.date(2026, 5, 1),
        fecha_hasta=datetime.date(2026, 5, 31),
        diagnostico="F32.0",
        profesional="Dr. Juan Pérez",
        estado_caso="activo",
        programa="Programa ISL",
        tipo_alta="terapeutica",
        region="Maule",
        tipo_ingreso="convenio",
    )
    assert f.estado_caso == "activo"
    assert f.tipo_alta == "terapeutica"


# ── FilaReporteRead ────────────────────────────────────────────────────────

def test_fila_reporte_trazable_por_folio_y_siniestro():
    """CA-3 / TC-051-03: cada fila es trazable a folio + número de siniestro."""
    fila = FilaReporteRead(
        ingreso_id=42,
        folio="2026-0123",
        numero_siniestro="SIN-001",
        rut="123456785",
        nombre_completo="Ana González",
        region="Maule",
        fecha_denuncia=datetime.date(2026, 1, 15),
        tipo_denuncia="DIAT",
        estado_caso="activo",
        diagnostico_inicial="F32.0",
        diagnostico_post_reca=None,
        profesional=None,
        fecha_calificacion_reca=None,
        reintegro_parcial=False,
        reintegro_total=False,
        alta_medica=False,
        alta_psicologica=False,
        alta_terapeutica=False,
    )
    assert fila.folio == "2026-0123"
    assert fila.numero_siniestro == "SIN-001"
    assert fila.ingreso_id == 42


# ── ReporteAuditoriaRead ───────────────────────────────────────────────────

def test_reporte_con_lista_vacia_es_valido():
    """CA-4 / TC-051-04: resultado vacío es válido."""
    reporte = ReporteAuditoriaRead(
        filtros_aplicados=FiltrosReporte(
            fecha_desde=datetime.date(2026, 1, 1),
            fecha_hasta=datetime.date(2026, 1, 31),
        ),
        total=0,
        filas=[],
    )
    assert reporte.total == 0
    assert reporte.filas == []
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auditoria_schemas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.schemas.auditoria'`.

- [ ] **Step 3: Implementar `app/schemas/auditoria.py`**

Crear `backend/app/schemas/auditoria.py`:

```python
"""Schemas Pydantic v2 para el módulo de Auditoría (EPIC-05).

DTOs de solo lectura — no modifican datos clínicos.
"""
from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SeccionDatosCasoRead(BaseModel):
    """§7.5.1 Datos del caso consolidado."""

    model_config = ConfigDict(from_attributes=True)

    folio: str
    numero_siniestro: str | None
    fecha_denuncia: datetime.date | None
    tipo_denuncia: str | None
    fecha_derivacion: datetime.date | None
    nombre_completo: str
    rut: str
    region: str | None


class SeccionEvaluacionesRead(BaseModel):
    """§7.5.2 Seguimiento de evaluaciones.

    Diagnóstico inicial y post-RECA se muestran por separado (CA-3, RN-4).
    """

    model_config = ConfigDict(from_attributes=True)

    fecha_eval_medica: datetime.date | None
    fecha_eval_psicologica: datetime.date | None
    fecha_calificacion_reca: datetime.date | None
    diagnostico_inicial: str | None
    diagnostico_post_reca: str | None
    numero_sesiones_evaluacion: int


class SeccionControlesRead(BaseModel):
    """§7.5.3 Controles y tratamiento."""

    model_config = ConfigDict(from_attributes=True)

    fecha_primera_consulta_medica: datetime.date | None
    fecha_primera_consulta_psicologica: datetime.date | None
    n_sesiones_medicas: int
    n_sesiones_psicologicas: int
    n_sesiones_ampliacion: int
    reintegro_parcial: bool
    fecha_reintegro_parcial: datetime.date | None
    reintegro_total: bool
    fecha_reintegro_total: datetime.date | None


class SeccionCierreRead(BaseModel):
    """§7.5.4 Cierre del caso.

    Cuando no hay altas registradas, todos los flags son False y las fechas None
    (caso en tratamiento — CA-5, TC-050-04). No se bloquea la visualización.
    """

    model_config = ConfigDict(from_attributes=True)

    alta_medica: bool
    fecha_alta_medica: datetime.date | None
    alta_psicologica: bool
    fecha_alta_psicologica: datetime.date | None
    alta_terapeutica: bool
    fecha_alta_terapeutica: datetime.date | None
    estado_general: str | None
    observaciones: str | None


class CasoConsolidadoRead(BaseModel):
    """Vista consolidada del caso — todas las secciones §7.5.1..§7.5.4.

    Corresponde a la respuesta del endpoint GET /api/v1/auditoria/casos/{ingreso_id}.
    """

    model_config = ConfigDict(from_attributes=True)

    ingreso_id: int
    datos_caso: SeccionDatosCasoRead
    evaluaciones: SeccionEvaluacionesRead
    controles: SeccionControlesRead
    cierre: SeccionCierreRead


class FiltrosReporte(BaseModel):
    """Filtros aplicables al generador de reportes de auditoría (CEPA-051).

    RN-2: el período (fecha_desde + fecha_hasta) es obligatorio.
    Todos los demás filtros son opcionales y combinables (AND).
    """

    fecha_desde: datetime.date
    fecha_hasta: datetime.date
    diagnostico: str | None = None
    profesional: str | None = None
    estado_caso: str | None = None
    programa: str | None = None
    tipo_alta: str | None = None
    region: str | None = None
    tipo_ingreso: str | None = None

    @field_validator("fecha_desde", "fecha_hasta", mode="before")
    @classmethod
    def _periodo_obligatorio(cls, v: object) -> object:
        if v is None:
            raise ValueError("El período (fecha_desde y fecha_hasta) es obligatorio.")
        return v


class FilaReporteRead(BaseModel):
    """Una fila del reporte de auditoría.

    Cada fila es trazable a su folio + número de siniestro (CA-3, RN-3, TC-051-03).
    """

    model_config = ConfigDict(from_attributes=True)

    ingreso_id: int
    folio: str
    numero_siniestro: str | None
    rut: str
    nombre_completo: str
    region: str | None
    fecha_denuncia: datetime.date | None
    tipo_denuncia: str | None
    estado_caso: str | None
    diagnostico_inicial: str | None
    diagnostico_post_reca: str | None
    profesional: str | None
    fecha_calificacion_reca: datetime.date | None
    reintegro_parcial: bool
    reintegro_total: bool
    alta_medica: bool
    alta_psicologica: bool
    alta_terapeutica: bool


class ReporteAuditoriaRead(BaseModel):
    """Respuesta del endpoint de generación de reportes.

    Incluye los filtros aplicados como metadatos del reporte (CA-2, RN-3).
    Un reporte vacío (total=0, filas=[]) es un resultado válido (CA-4, TC-051-04).
    """

    model_config = ConfigDict(from_attributes=True)

    filtros_aplicados: FiltrosReporte
    total: int
    filas: list[FilaReporteRead]
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auditoria_schemas.py -v`
Expected: `13 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auditoria.py backend/tests/test_auditoria_schemas.py
git commit -m "feat(auditoria): schemas Pydantic v2 — CasoConsolidado, FiltrosReporte, FilaReporte"
```

---

## Task 2: Servicio de agregación `app/services/auditoria.py`

Lógica de consulta ORM sobre las tablas de los módulos fuente. No emite SQL específico de motor.

**Files:**
- Create: `backend/app/services/__init__.py` (vacío, si no existe)
- Create: `backend/app/services/auditoria.py`
- Test: `backend/tests/test_auditoria_service.py`

> **Supuesto de modelos:** los campos de cada modelo se reflejan en el código tal como los definen los planes de EPIC-01..07. Si al ejecutar el loop algún nombre de campo difiere, ajustar la columna correspondiente en `auditoria.py`; los tests fallarán con `AttributeError` indicando exactamente qué columna no existe.

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auditoria_service.py`:

```python
"""Tests del servicio de agregación de auditoría.

Los datos se crean directamente vía los modelos de EPIC-01..07, que se asumen presentes.
Cada test trabaja sobre la BD de pruebas con rollback automático (fixture db_session).
"""
from __future__ import annotations

import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.control import Control
from app.models.farmaco import AsignacionFarmaco
from app.models.ingreso import Ingreso, Seguimiento
from app.models.licencia import Licencia
from app.models.paciente import Paciente
from app.models.reintegro import Reintegro
from app.schemas.auditoria import FiltrosReporte
from app.services.auditoria import get_caso_consolidado, generar_reporte


# ── Fixtures de datos de prueba ────────────────────────────────────────────

@pytest.fixture
def paciente_base(db_session: Session) -> Paciente:
    p = Paciente(
        rut="123456785",
        nombre="Ana González",
        sexo="F",
        edad=35,
        region="Maule",
    )
    db_session.add(p)
    db_session.flush()
    return p


@pytest.fixture
def ingreso_completo(db_session: Session, paciente_base: Paciente) -> Ingreso:
    """Ingreso con datos en todas las secciones §7.5.1..§7.5.4."""
    ing = Ingreso(
        paciente_id=paciente_base.id,
        folio="2026-0123",
        numero_siniestro="SIN-2026-001",
        fecha_denuncia=datetime.date(2026, 1, 15),
        tipo_denuncia="DIAT",
        fecha_derivacion=datetime.date(2026, 1, 20),
        estado_caso="activo",
        tipo_ingreso="convenio",
        programa="Programa ISL",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        fecha_eval_medica=datetime.date(2026, 2, 1),
        fecha_eval_psicologica=datetime.date(2026, 2, 5),
        fecha_calificacion_reca=datetime.date(2026, 3, 1),
        diagnostico_inicial="F32.0 Episodio depresivo leve",
        diagnostico_post_reca="F33.1 Trastorno depresivo recurrente",
        numero_sesiones_evaluacion=3,
        fecha_primera_consulta_medica=datetime.date(2026, 3, 10),
        fecha_primera_consulta_psicologica=datetime.date(2026, 3, 12),
        n_sesiones_medicas=5,
        n_sesiones_psicologicas=8,
        n_sesiones_ampliacion=2,
        alta_medica=False,
        fecha_alta_medica=None,
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general="activo",
        observaciones=None,
    )
    db_session.add(seg)

    rei = Reintegro(
        ingreso_id=ing.id,
        parcial=True,
        fecha_parcial=datetime.date(2026, 5, 1),
        total=False,
        fecha_total=None,
    )
    db_session.add(rei)
    db_session.flush()
    return ing


@pytest.fixture
def ingreso_sin_altas(db_session: Session, paciente_base: Paciente) -> Ingreso:
    """TC-050-04: caso en tratamiento sin altas."""
    ing = Ingreso(
        paciente_id=paciente_base.id,
        folio="2026-0124",
        numero_siniestro="SIN-2026-002",
        fecha_denuncia=datetime.date(2026, 2, 1),
        tipo_denuncia="DIEP",
        fecha_derivacion=datetime.date(2026, 2, 5),
        estado_caso="activo",
        tipo_ingreso="convenio",
        programa="Programa ISL",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        fecha_eval_medica=None,
        fecha_eval_psicologica=None,
        fecha_calificacion_reca=None,
        diagnostico_inicial="F41.1",
        diagnostico_post_reca=None,
        numero_sesiones_evaluacion=0,
        fecha_primera_consulta_medica=None,
        fecha_primera_consulta_psicologica=None,
        n_sesiones_medicas=0,
        n_sesiones_psicologicas=0,
        n_sesiones_ampliacion=0,
        alta_medica=False,
        fecha_alta_medica=None,
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general=None,
        observaciones=None,
    )
    db_session.add(seg)
    db_session.flush()
    return ing


# ── TC-050-01: vista consolidada con datos en todos los módulos ────────────

def test_get_caso_consolidado_devuelve_todas_las_secciones(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-1 / TC-050-01: GET por ingreso_id devuelve §7.5.1–§7.5.4 consolidados."""
    caso = get_caso_consolidado(db_session, ingreso_completo.id)

    assert caso is not None
    assert caso.ingreso_id == ingreso_completo.id

    # §7.5.1 datos del caso
    assert caso.datos_caso.folio == "2026-0123"
    assert caso.datos_caso.numero_siniestro == "SIN-2026-001"
    assert caso.datos_caso.rut == "123456785"
    assert caso.datos_caso.region == "Maule"

    # §7.5.2 evaluaciones
    assert caso.evaluaciones.diagnostico_inicial == "F32.0 Episodio depresivo leve"
    assert caso.evaluaciones.diagnostico_post_reca == "F33.1 Trastorno depresivo recurrente"
    assert caso.evaluaciones.fecha_calificacion_reca == datetime.date(2026, 3, 1)

    # §7.5.3 controles
    assert caso.controles.n_sesiones_medicas == 5
    assert caso.controles.reintegro_parcial is True
    assert caso.controles.fecha_reintegro_parcial == datetime.date(2026, 5, 1)

    # §7.5.4 cierre
    assert caso.cierre.alta_medica is False


# ── TC-050-02: siniestros diferenciados bajo el mismo RUT ─────────────────

def test_siniestros_distintos_no_se_mezclan(db_session: Session, paciente_base: Paciente):
    """CA-2 / TC-050-02: dos denuncias bajo el mismo RUT se presentan diferenciadas."""
    ing1 = Ingreso(
        paciente_id=paciente_base.id,
        folio="2020-0001",
        numero_siniestro="SIN-2020-DIAT",
        fecha_denuncia=datetime.date(2020, 6, 1),
        tipo_denuncia="DIAT",
        fecha_derivacion=datetime.date(2020, 6, 5),
        estado_caso="cerrado",
        tipo_ingreso="convenio",
        programa="Programa ISL",
    )
    ing2 = Ingreso(
        paciente_id=paciente_base.id,
        folio="2026-0200",
        numero_siniestro="SIN-2026-DIEP",
        fecha_denuncia=datetime.date(2026, 3, 1),
        tipo_denuncia="DIEP",
        fecha_derivacion=datetime.date(2026, 3, 5),
        estado_caso="activo",
        tipo_ingreso="convenio",
        programa="Programa ISL",
    )
    for seg_data, ing in [
        (ing1, ing1),
        (ing2, ing2),
    ]:
        db_session.add(ing)
    db_session.flush()

    for ing in [ing1, ing2]:
        seg = Seguimiento(
            ingreso_id=ing.id,
            fecha_eval_medica=None,
            fecha_eval_psicologica=None,
            fecha_calificacion_reca=None,
            diagnostico_inicial=None,
            diagnostico_post_reca=None,
            numero_sesiones_evaluacion=0,
            fecha_primera_consulta_medica=None,
            fecha_primera_consulta_psicologica=None,
            n_sesiones_medicas=0,
            n_sesiones_psicologicas=0,
            n_sesiones_ampliacion=0,
            alta_medica=False,
            fecha_alta_medica=None,
            alta_psicologica=False,
            fecha_alta_psicologica=None,
            alta_terapeutica=False,
            fecha_alta_terapeutica=None,
            estado_general=None,
            observaciones=None,
        )
        db_session.add(seg)
    db_session.flush()

    caso1 = get_caso_consolidado(db_session, ing1.id)
    caso2 = get_caso_consolidado(db_session, ing2.id)

    assert caso1.datos_caso.numero_siniestro == "SIN-2020-DIAT"
    assert caso2.datos_caso.numero_siniestro == "SIN-2026-DIEP"
    assert caso1.datos_caso.folio != caso2.datos_caso.folio


# ── TC-050-03: diagnósticos inicial y post-RECA por separado ──────────────

def test_diagnosticos_se_muestran_por_separado(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-3 / TC-050-03: diagnóstico inicial y post-RECA visibles por separado."""
    caso = get_caso_consolidado(db_session, ingreso_completo.id)
    ev = caso.evaluaciones
    assert ev.diagnostico_inicial is not None
    assert ev.diagnostico_post_reca is not None
    assert ev.diagnostico_inicial != ev.diagnostico_post_reca
    assert ev.fecha_calificacion_reca is not None


# ── TC-050-04: caso sin altas — cierre pendiente sin bloquear el resto ────

def test_caso_sin_altas_cierre_pendiente(
    db_session: Session, ingreso_sin_altas: Ingreso
):
    """CA-5 / TC-050-04: cierre vacío/pendiente no bloquea visualización del resto."""
    caso = get_caso_consolidado(db_session, ingreso_sin_altas.id)

    assert caso.cierre.alta_medica is False
    assert caso.cierre.alta_psicologica is False
    assert caso.cierre.alta_terapeutica is False
    assert caso.cierre.estado_general is None
    # resto de hitos visible sin error
    assert caso.datos_caso.folio == "2026-0124"
    assert caso.evaluaciones.numero_sesiones_evaluacion == 0


# ── TC-050-06: ingreso_id inexistente devuelve None ────────────────────────

def test_caso_inexistente_devuelve_none(db_session: Session):
    resultado = get_caso_consolidado(db_session, ingreso_id=999999)
    assert resultado is None


# ── TC-051-01: reporte con filtros combinados ──────────────────────────────

def test_reporte_filtros_combinados(
    db_session: Session, ingreso_completo: Ingreso, ingreso_sin_altas: Ingreso
):
    """CA-1 / TC-051-01: solo retorna casos que cumplen todos los filtros (AND)."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        estado_caso="activo",
        tipo_denuncia="DIAT",
    )
    reporte = generar_reporte(db_session, filtros)

    folios = [f.folio for f in reporte.filas]
    assert "2026-0123" in folios       # DIAT + activo → debe aparecer
    assert "2026-0124" not in folios   # DIEP → no cumple tipo_denuncia="DIAT"
    assert reporte.total == len(reporte.filas)


# ── TC-051-04: reporte vacío cuando no hay coincidencias ──────────────────

def test_reporte_vacio_sin_coincidencias(db_session: Session, ingreso_completo: Ingreso):
    """CA-4 / TC-051-04: resultado vacío con mensaje implícito en total=0."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2000, 1, 1),
        fecha_hasta=datetime.date(2000, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)

    assert reporte.total == 0
    assert reporte.filas == []


# ── TC-051-03: trazabilidad por folio + siniestro ─────────────────────────

def test_reporte_filas_trazables_por_folio_y_siniestro(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-3 / TC-051-03: cada fila contiene folio e ingreso_id para trazabilidad."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)

    fila = next(f for f in reporte.filas if f.folio == "2026-0123")
    assert fila.numero_siniestro == "SIN-2026-001"
    assert fila.ingreso_id == ingreso_completo.id


# ── Filtros_aplicados conservados en el reporte ───────────────────────────

def test_reporte_conserva_filtros_aplicados_como_metadatos(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-2 / TC-051-02: los filtros se devuelven como metadatos en la respuesta."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 5, 1),
        fecha_hasta=datetime.date(2026, 5, 31),
        estado_caso="activo",
    )
    reporte = generar_reporte(db_session, filtros)

    assert reporte.filtros_aplicados.fecha_desde == datetime.date(2026, 5, 1)
    assert reporte.filtros_aplicados.estado_caso == "activo"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auditoria_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.auditoria'`.

- [ ] **Step 3: Crear `backend/app/services/__init__.py`** (si no existe)

```bash
touch backend/app/services/__init__.py
```

- [ ] **Step 4: Implementar `app/services/auditoria.py`**

Crear `backend/app/services/auditoria.py`:

```python
"""Servicio de agregación de auditoría (EPIC-05).

Solo lectura: agrega datos de los módulos fuente vía ORM portable (sin SQL específico
de motor). No modifica datos clínicos (RN-1, CA-4).
"""
from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso, Seguimiento
from app.models.paciente import Paciente
from app.models.reintegro import Reintegro
from app.schemas.auditoria import (
    CasoConsolidadoRead,
    FilaReporteRead,
    FiltrosReporte,
    ReporteAuditoriaRead,
    SeccionCierreRead,
    SeccionControlesRead,
    SeccionDatosCasoRead,
    SeccionEvaluacionesRead,
)


def get_caso_consolidado(db: Session, ingreso_id: int) -> CasoConsolidadoRead | None:
    """Retorna la vista consolidada de un caso por ingreso_id.

    Agrega §7.5.1..§7.5.4 desde los módulos fuente. Si el ingreso no existe,
    retorna None (el router responderá 404).

    Siniestros múltiples bajo el mismo RUT se diferencian por ingreso_id (CA-2, RN-3).
    """
    # Carga el ingreso junto con el paciente y el seguimiento
    stmt_ingreso = (
        select(Ingreso)
        .where(Ingreso.id == ingreso_id)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
    )
    ingreso: Ingreso | None = db.scalar(stmt_ingreso)
    if ingreso is None:
        return None

    paciente: Paciente = db.get(Paciente, ingreso.paciente_id)  # type: ignore[assignment]

    # Seguimiento (§7.5.2 + parte de §7.5.3 y §7.5.4)
    seg: Seguimiento | None = db.scalar(
        select(Seguimiento).where(Seguimiento.ingreso_id == ingreso_id)
    )

    # Reintegro (§7.5.3)
    rei: Reintegro | None = db.scalar(
        select(Reintegro).where(Reintegro.ingreso_id == ingreso_id)
    )

    # §7.5.1 Datos del caso
    datos_caso = SeccionDatosCasoRead(
        folio=ingreso.folio,
        numero_siniestro=ingreso.numero_siniestro,
        fecha_denuncia=ingreso.fecha_denuncia,
        tipo_denuncia=ingreso.tipo_denuncia,
        fecha_derivacion=ingreso.fecha_derivacion,
        nombre_completo=paciente.nombre,
        rut=paciente.rut,
        region=paciente.region,
    )

    # §7.5.2 Evaluaciones
    evaluaciones = SeccionEvaluacionesRead(
        fecha_eval_medica=seg.fecha_eval_medica if seg else None,
        fecha_eval_psicologica=seg.fecha_eval_psicologica if seg else None,
        fecha_calificacion_reca=seg.fecha_calificacion_reca if seg else None,
        diagnostico_inicial=seg.diagnostico_inicial if seg else None,
        diagnostico_post_reca=seg.diagnostico_post_reca if seg else None,
        numero_sesiones_evaluacion=seg.numero_sesiones_evaluacion if seg else 0,
    )

    # §7.5.3 Controles y tratamiento
    controles = SeccionControlesRead(
        fecha_primera_consulta_medica=seg.fecha_primera_consulta_medica if seg else None,
        fecha_primera_consulta_psicologica=(
            seg.fecha_primera_consulta_psicologica if seg else None
        ),
        n_sesiones_medicas=seg.n_sesiones_medicas if seg else 0,
        n_sesiones_psicologicas=seg.n_sesiones_psicologicas if seg else 0,
        n_sesiones_ampliacion=seg.n_sesiones_ampliacion if seg else 0,
        reintegro_parcial=rei.parcial if rei else False,
        fecha_reintegro_parcial=rei.fecha_parcial if rei else None,
        reintegro_total=rei.total if rei else False,
        fecha_reintegro_total=rei.fecha_total if rei else None,
    )

    # §7.5.4 Cierre
    # Si no hay altas registradas, todas las flags son False (CA-5, TC-050-04).
    cierre = SeccionCierreRead(
        alta_medica=seg.alta_medica if seg else False,
        fecha_alta_medica=seg.fecha_alta_medica if seg else None,
        alta_psicologica=seg.alta_psicologica if seg else False,
        fecha_alta_psicologica=seg.fecha_alta_psicologica if seg else None,
        alta_terapeutica=seg.alta_terapeutica if seg else False,
        fecha_alta_terapeutica=seg.fecha_alta_terapeutica if seg else None,
        estado_general=ingreso.estado_caso,
        observaciones=seg.observaciones if seg else None,
    )

    return CasoConsolidadoRead(
        ingreso_id=ingreso.id,
        datos_caso=datos_caso,
        evaluaciones=evaluaciones,
        controles=controles,
        cierre=cierre,
    )


def generar_reporte(db: Session, filtros: FiltrosReporte) -> ReporteAuditoriaRead:
    """Genera el reporte de auditoría aplicando todos los filtros (AND).

    Cada fila es trazable por folio + número de siniestro (CA-3, RN-3).
    Un reporte vacío es válido (CA-4, TC-051-04).
    El período es siempre obligatorio y se aplica sobre fecha_denuncia del ingreso.
    """
    condiciones = [
        Ingreso.fecha_denuncia >= filtros.fecha_desde,
        Ingreso.fecha_denuncia <= filtros.fecha_hasta,
    ]

    if filtros.estado_caso:
        condiciones.append(Ingreso.estado_caso == filtros.estado_caso)
    if filtros.tipo_ingreso:
        condiciones.append(Ingreso.tipo_ingreso == filtros.tipo_ingreso)
    if filtros.programa:
        condiciones.append(Ingreso.programa == filtros.programa)
    if filtros.region:
        condiciones.append(Paciente.region == filtros.region)
    if filtros.tipo_denuncia:
        condiciones.append(Ingreso.tipo_denuncia == filtros.tipo_denuncia)

    stmt = (
        select(Ingreso, Paciente, Seguimiento)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .outerjoin(Seguimiento, Seguimiento.ingreso_id == Ingreso.id)
        .where(and_(*condiciones))
        .order_by(Ingreso.fecha_denuncia, Ingreso.id)
    )

    filas: list[FilaReporteRead] = []
    for ingreso, paciente, seg in db.execute(stmt):
        # Filtro post-consulta sobre campos de seguimiento (diagnóstico, tipo_alta)
        if filtros.diagnostico:
            dx_ini = seg.diagnostico_inicial if seg else None
            dx_post = seg.diagnostico_post_reca if seg else None
            if filtros.diagnostico not in (dx_ini or "", dx_post or ""):
                continue
        if filtros.tipo_alta:
            tiene_alta = False
            if seg:
                if filtros.tipo_alta == "medica" and seg.alta_medica:
                    tiene_alta = True
                elif filtros.tipo_alta == "psicologica" and seg.alta_psicologica:
                    tiene_alta = True
                elif filtros.tipo_alta == "terapeutica" and seg.alta_terapeutica:
                    tiene_alta = True
            if not tiene_alta:
                continue

        fila = FilaReporteRead(
            ingreso_id=ingreso.id,
            folio=ingreso.folio,
            numero_siniestro=ingreso.numero_siniestro,
            rut=paciente.rut,
            nombre_completo=paciente.nombre,
            region=paciente.region,
            fecha_denuncia=ingreso.fecha_denuncia,
            tipo_denuncia=ingreso.tipo_denuncia,
            estado_caso=ingreso.estado_caso,
            diagnostico_inicial=seg.diagnostico_inicial if seg else None,
            diagnostico_post_reca=seg.diagnostico_post_reca if seg else None,
            profesional=None,  # campo futuro — se conectará con el módulo de controles
            fecha_calificacion_reca=seg.fecha_calificacion_reca if seg else None,
            reintegro_parcial=False,
            reintegro_total=False,
            alta_medica=seg.alta_medica if seg else False,
            alta_psicologica=seg.alta_psicologica if seg else False,
            alta_terapeutica=seg.alta_terapeutica if seg else False,
        )
        filas.append(fila)

    return ReporteAuditoriaRead(
        filtros_aplicados=filtros,
        total=len(filas),
        filas=filas,
    )
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auditoria_service.py -v`
Expected: `10 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/auditoria.py \
        backend/tests/test_auditoria_service.py
git commit -m "feat(auditoria): servicio de agregación ORM — vista consolidada y reporte con filtros"
```

---

## Task 3: Router `/api/v1/auditoria` — endpoints de vista consolidada y reporte

Expone los endpoints protegidos por RBAC (`Coordinacion`, `Auditor`). Todo acceso se registra en el log de auditoría (RN-7).

**Files:**
- Create: `backend/app/routers/auditoria.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auditoria_api.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_auditoria_api.py`:

```python
"""Tests de integración end-to-end de la API de auditoría.

Cubre CA y TC del spec CEPA-050 y CEPA-051. Los datos se crean vía la sesión
de test (db_session) directamente en los modelos de dominio.
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso, Seguimiento
from app.models.paciente import Paciente
from app.models.reintegro import Reintegro


# ── Fixture de datos compartida ────────────────────────────────────────────

@pytest.fixture
def caso_completo(db_session: Session) -> dict:
    """Crea un paciente + ingreso + seguimiento + reintegro en la BD de tests."""
    p = Paciente(
        rut="123456785",
        nombre="Ana González",
        sexo="F",
        edad=35,
        region="Maule",
    )
    db_session.add(p)
    db_session.flush()

    ing = Ingreso(
        paciente_id=p.id,
        folio="2026-0123",
        numero_siniestro="SIN-2026-001",
        fecha_denuncia=datetime.date(2026, 1, 15),
        tipo_denuncia="DIAT",
        fecha_derivacion=datetime.date(2026, 1, 20),
        estado_caso="activo",
        tipo_ingreso="convenio",
        programa="Programa ISL",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        fecha_eval_medica=datetime.date(2026, 2, 1),
        fecha_eval_psicologica=datetime.date(2026, 2, 5),
        fecha_calificacion_reca=datetime.date(2026, 3, 1),
        diagnostico_inicial="F32.0 Episodio depresivo leve",
        diagnostico_post_reca="F33.1 Trastorno depresivo recurrente",
        numero_sesiones_evaluacion=3,
        fecha_primera_consulta_medica=datetime.date(2026, 3, 10),
        fecha_primera_consulta_psicologica=datetime.date(2026, 3, 12),
        n_sesiones_medicas=5,
        n_sesiones_psicologicas=8,
        n_sesiones_ampliacion=2,
        alta_medica=False,
        fecha_alta_medica=None,
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general="activo",
        observaciones=None,
    )
    db_session.add(seg)

    rei = Reintegro(
        ingreso_id=ing.id,
        parcial=True,
        fecha_parcial=datetime.date(2026, 5, 1),
        total=False,
        fecha_total=None,
    )
    db_session.add(rei)
    db_session.flush()

    return {"ingreso_id": ing.id, "folio": ing.folio}


# ── CEPA-050: Vista consolidada del caso ──────────────────────────────────

class TestVistaCasoConsolidado:

    def test_auditor_puede_ver_caso_consolidado_por_ingreso_id(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1 / TC-050-01: Auditor abre vista consolidada con §7.5.1–§7.5.4."""
        r = as_auditor.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 200

        body = r.json()
        assert body["ingreso_id"] == caso_completo["ingreso_id"]

        # §7.5.1
        dc = body["datos_caso"]
        assert dc["folio"] == "2026-0123"
        assert dc["numero_siniestro"] == "SIN-2026-001"
        assert dc["rut"] == "123456785"

        # §7.5.2
        ev = body["evaluaciones"]
        assert ev["diagnostico_inicial"] == "F32.0 Episodio depresivo leve"
        assert ev["diagnostico_post_reca"] == "F33.1 Trastorno depresivo recurrente"
        assert ev["fecha_calificacion_reca"] == "2026-03-01"

        # §7.5.3
        ctrl = body["controles"]
        assert ctrl["n_sesiones_medicas"] == 5
        assert ctrl["reintegro_parcial"] is True

        # §7.5.4
        cierre = body["cierre"]
        assert cierre["alta_medica"] is False

    def test_coordinacion_puede_ver_caso_consolidado(
        self, as_coordinacion: TestClient, caso_completo: dict
    ):
        """CA-1: Coordinacion también tiene acceso de lectura."""
        r = as_coordinacion.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 200

    def test_admin_no_puede_ver_caso_consolidado(
        self, as_admin: TestClient, caso_completo: dict
    ):
        """CA-4 / TC-050-06: Administrativo no accede al módulo de auditoría (RBAC)."""
        r = as_admin.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 403

    def test_sin_token_devuelve_401(self, client: TestClient, caso_completo: dict):
        """TC-050-06: sin sesión activa → 401."""
        r = client.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 401

    def test_ingreso_inexistente_devuelve_404(self, as_auditor: TestClient):
        """TC-050-06 (variante): ingreso que no existe → 404."""
        r = as_auditor.get("/api/v1/auditoria/casos/999999")
        assert r.status_code == 404

    def test_no_ofrece_endpoint_de_edicion(self, as_auditor: TestClient, caso_completo: dict):
        """CA-4 / TC-050-05: el router no expone métodos de escritura (PUT/PATCH/DELETE)."""
        r_put = as_auditor.put(
            f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}",
            json={"diagnostico_inicial": "hack"},
        )
        r_patch = as_auditor.patch(
            f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}",
            json={},
        )
        r_delete = as_auditor.delete(
            f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}"
        )
        assert r_put.status_code in (404, 405)
        assert r_patch.status_code in (404, 405)
        assert r_delete.status_code in (404, 405)

    def test_caso_sin_altas_cierre_mostrado_como_pendiente(
        self, as_auditor: TestClient, db_session: Session
    ):
        """CA-5 / TC-050-04: cierre vacío no bloquea visualización del resto."""
        p = Paciente(
            rut="987654325",
            nombre="Luis Pérez",
            sexo="M",
            edad=42,
            region="Metropolitana",
        )
        db_session.add(p)
        db_session.flush()

        ing = Ingreso(
            paciente_id=p.id,
            folio="2026-0200",
            numero_siniestro=None,
            fecha_denuncia=datetime.date(2026, 4, 1),
            tipo_denuncia="DIEP",
            fecha_derivacion=None,
            estado_caso="activo",
            tipo_ingreso="convenio",
            programa="Programa ISL",
        )
        db_session.add(ing)
        db_session.flush()

        seg = Seguimiento(
            ingreso_id=ing.id,
            fecha_eval_medica=None,
            fecha_eval_psicologica=None,
            fecha_calificacion_reca=None,
            diagnostico_inicial=None,
            diagnostico_post_reca=None,
            numero_sesiones_evaluacion=0,
            fecha_primera_consulta_medica=None,
            fecha_primera_consulta_psicologica=None,
            n_sesiones_medicas=0,
            n_sesiones_psicologicas=0,
            n_sesiones_ampliacion=0,
            alta_medica=False,
            fecha_alta_medica=None,
            alta_psicologica=False,
            fecha_alta_psicologica=None,
            alta_terapeutica=False,
            fecha_alta_terapeutica=None,
            estado_general=None,
            observaciones=None,
        )
        db_session.add(seg)
        db_session.flush()

        r = as_auditor.get(f"/api/v1/auditoria/casos/{ing.id}")
        assert r.status_code == 200
        body = r.json()
        cierre = body["cierre"]
        assert cierre["alta_medica"] is False
        assert cierre["estado_general"] is None
        # resto de hitos accesible
        assert body["datos_caso"]["folio"] == "2026-0200"


# ── CEPA-050: Búsqueda de casos (listado) ─────────────────────────────────

class TestListadoCasos:

    def test_auditor_puede_listar_casos_con_filtro_rut(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1: búsqueda por RUT devuelve los ingresos del paciente."""
        r = as_auditor.get("/api/v1/auditoria/casos", params={"rut": "123456785"})
        assert r.status_code == 200
        body = r.json()
        folios = [c["datos_caso"]["folio"] for c in body]
        assert "2026-0123" in folios

    def test_auditor_puede_listar_casos_con_filtro_folio(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1: búsqueda por folio devuelve exactamente ese caso."""
        r = as_auditor.get("/api/v1/auditoria/casos", params={"folio": "2026-0123"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["datos_caso"]["folio"] == "2026-0123"

    def test_siniestros_distintos_aparecen_como_casos_diferenciados(
        self, as_auditor: TestClient, db_session: Session
    ):
        """CA-2 / TC-050-02: dos denuncias bajo el mismo RUT → dos casos diferenciados."""
        p = Paciente(
            rut="112233449",
            nombre="Carlos Rojas",
            sexo="M",
            edad=50,
            region="Biobío",
        )
        db_session.add(p)
        db_session.flush()

        for folio, siniestro, tipo in [
            ("2020-0001", "SIN-2020-DIAT", "DIAT"),
            ("2026-0300", "SIN-2026-DIEP", "DIEP"),
        ]:
            ing = Ingreso(
                paciente_id=p.id,
                folio=folio,
                numero_siniestro=siniestro,
                fecha_denuncia=datetime.date(2026, 1, 1),
                tipo_denuncia=tipo,
                fecha_derivacion=None,
                estado_caso="activo",
                tipo_ingreso="convenio",
                programa="ISL",
            )
            db_session.add(ing)
            db_session.flush()
            seg = Seguimiento(
                ingreso_id=ing.id,
                fecha_eval_medica=None, fecha_eval_psicologica=None,
                fecha_calificacion_reca=None, diagnostico_inicial=None,
                diagnostico_post_reca=None, numero_sesiones_evaluacion=0,
                fecha_primera_consulta_medica=None, fecha_primera_consulta_psicologica=None,
                n_sesiones_medicas=0, n_sesiones_psicologicas=0, n_sesiones_ampliacion=0,
                alta_medica=False, fecha_alta_medica=None,
                alta_psicologica=False, fecha_alta_psicologica=None,
                alta_terapeutica=False, fecha_alta_terapeutica=None,
                estado_general=None, observaciones=None,
            )
            db_session.add(seg)
        db_session.flush()

        r = as_auditor.get("/api/v1/auditoria/casos", params={"rut": "112233449"})
        assert r.status_code == 200
        body = r.json()
        siniestros = [c["datos_caso"]["numero_siniestro"] for c in body]
        assert "SIN-2020-DIAT" in siniestros
        assert "SIN-2026-DIEP" in siniestros
        # Hitos no mezclados: cada caso tiene su folio correcto
        folios_por_siniestro = {
            c["datos_caso"]["numero_siniestro"]: c["datos_caso"]["folio"] for c in body
        }
        assert folios_por_siniestro["SIN-2020-DIAT"] == "2020-0001"
        assert folios_por_siniestro["SIN-2026-DIEP"] == "2026-0300"


# ── CEPA-051: Reportes de auditoría ───────────────────────────────────────

class TestReportesAuditoria:

    def test_auditor_genera_reporte_con_filtros(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1 / TC-051-01: reporte filtrando por período y estado devuelve filas correctas."""
        payload = {
            "fecha_desde": "2026-01-01",
            "fecha_hasta": "2026-12-31",
            "estado_caso": "activo",
        }
        r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "filas" in body
        assert "total" in body
        assert "filtros_aplicados" in body
        assert body["filtros_aplicados"]["estado_caso"] == "activo"
        folios = [f["folio"] for f in body["filas"]]
        assert "2026-0123" in folios

    def test_admin_no_puede_generar_reporte(self, as_admin: TestClient):
        """TC-051-06: Administrativo no puede generar reportes de auditoría."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_admin.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 403

    def test_sin_token_reporte_devuelve_401(self, client: TestClient):
        """TC-051-06: sin sesión → 401."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = client.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 401

    def test_reporte_vacio_devuelve_200_con_total_cero(self, as_auditor: TestClient):
        """CA-4 / TC-051-04: filtros sin coincidencias → 200 con lista vacía, no error."""
        payload = {"fecha_desde": "2000-01-01", "fecha_hasta": "2000-12-31"}
        r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["filas"] == []

    def test_descarga_csv_contiene_filas_trazables(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-2 / TC-051-02: descarga en CSV conserva filtros como metadatos (encabezado)
        y cada fila es trazable por folio + número de siniestro (CA-3 / TC-051-03).
        """
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_auditor.post("/api/v1/auditoria/reportes/descargar", json=payload)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd

        contenido = r.text
        # Primera línea: encabezados con folio y numero_siniestro (trazabilidad)
        encabezados = contenido.splitlines()[0].split(",")
        assert "folio" in encabezados
        assert "numero_siniestro" in encabezados
        assert "ingreso_id" in encabezados

        # Al menos una fila de datos
        lineas = contenido.splitlines()
        assert len(lineas) >= 2

    def test_descarga_admin_denegada(self, as_admin: TestClient):
        """TC-051-06: Administrativo no puede descargar reportes de auditoría."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_admin.post("/api/v1/auditoria/reportes/descargar", json=payload)
        assert r.status_code == 403

    def test_reporte_sin_periodo_devuelve_422(self, as_auditor: TestClient):
        """RN-2: el período es obligatorio; sin fecha_desde → 422."""
        r = as_auditor.post("/api/v1/auditoria/reportes", json={"estado_caso": "activo"})
        assert r.status_code == 422

    def test_filas_son_trazables_por_folio_y_siniestro(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-3 / TC-051-03: cada fila contiene folio + numero_siniestro + ingreso_id."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 200
        body = r.json()
        for fila in body["filas"]:
            assert "folio" in fila
            assert "ingreso_id" in fila
            # numero_siniestro puede ser None para casos sin siniestro registrado
            assert "numero_siniestro" in fila
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_auditoria_api.py -v`
Expected: FAIL (múltiples errores `404 Not Found` porque las rutas aún no existen).

- [ ] **Step 3: Implementar `app/routers/auditoria.py`**

Crear `backend/app/routers/auditoria.py`:

```python
"""Router de Auditoría (EPIC-05).

Expone la vista consolidada del caso (CEPA-050) y los reportes de auditoría (CEPA-051).
Solo lectura: perfiles Coordinacion y Auditor; Administrativo sin acceso (RN-2, D1).
Todo acceso se registra en el log de auditoría (RN-7).
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ingreso import Ingreso, Seguimiento
from app.models.paciente import Paciente
from app.models.reintegro import Reintegro
from app.schemas.auditoria import (
    CasoConsolidadoRead,
    FiltrosReporte,
    ReporteAuditoriaRead,
)
from app.services.auditoria import get_caso_consolidado, generar_reporte

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])

# Solo Coordinacion y Auditor acceden al módulo de auditoría (RN-2, D1)
_reader = Depends(require_role("Coordinacion", "Auditor"))


# ── CEPA-050: Vista consolidada del caso ──────────────────────────────────

@router.get(
    "/casos/{ingreso_id}",
    response_model=CasoConsolidadoRead,
    summary="Vista consolidada de un caso por ingreso_id (§7.5.1–§7.5.4)",
)
def ver_caso_consolidado(
    ingreso_id: int,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> CasoConsolidadoRead:
    """Retorna todos los hitos del caso: datos, evaluaciones, controles y cierre.

    Solo lectura (CA-4, RN-1, RN-2). El acceso se registra en el log (RN-7).
    404 si el ingreso no existe.
    """
    caso = get_caso_consolidado(db, ingreso_id)
    if caso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso no encontrado.")

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_caso",
        entity_id=str(ingreso_id),
    )
    return caso


@router.get(
    "/casos",
    response_model=list[CasoConsolidadoRead],
    summary="Búsqueda de casos por RUT o folio",
)
def buscar_casos(
    rut: str | None = Query(default=None, description="RUT normalizado del paciente"),
    folio: str | None = Query(default=None, description="Folio del ingreso"),
    numero_siniestro: str | None = Query(default=None, description="Número de siniestro"),
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> list[CasoConsolidadoRead]:
    """Busca casos por RUT, folio o número de siniestro. Retorna lista de vistas consolidadas.

    Cada siniestro bajo el mismo RUT es un caso diferenciado (CA-2, RN-3, D2).
    """
    stmt = (
        select(Ingreso)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .order_by(Ingreso.fecha_denuncia.desc(), Ingreso.id.desc())
    )
    if rut:
        stmt = stmt.where(Paciente.rut == rut)
    if folio:
        stmt = stmt.where(Ingreso.folio == folio)
    if numero_siniestro:
        stmt = stmt.where(Ingreso.numero_siniestro == numero_siniestro)

    ingresos = list(db.scalars(stmt))

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_busqueda",
        entity_id=f"rut={rut}&folio={folio}&siniestro={numero_siniestro}",
    )

    resultados: list[CasoConsolidadoRead] = []
    for ing in ingresos:
        caso = get_caso_consolidado(db, ing.id)
        if caso is not None:
            resultados.append(caso)
    return resultados


# ── CEPA-051: Reportes de auditoría ───────────────────────────────────────

@router.post(
    "/reportes",
    response_model=ReporteAuditoriaRead,
    summary="Genera reporte de auditoría con filtros combinables (AND)",
)
def generar_reporte_auditoria(
    filtros: FiltrosReporte,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> ReporteAuditoriaRead:
    """Genera un reporte de auditoría filtrando por período, diagnóstico, profesional
    y estado del caso. El período (fecha_desde, fecha_hasta) es obligatorio (RN-2).
    Un resultado vacío es válido (CA-4). La generación se registra en el log (RN-5).
    """
    reporte = generar_reporte(db, filtros)

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_reporte",
        entity_id=(
            f"{filtros.fecha_desde}..{filtros.fecha_hasta}"
            f"|estado={filtros.estado_caso}|dx={filtros.diagnostico}"
        ),
    )
    return reporte


@router.post(
    "/reportes/descargar",
    summary="Descarga el reporte de auditoría en formato CSV",
)
def descargar_reporte_csv(
    filtros: FiltrosReporte,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Descarga el reporte de auditoría como archivo CSV.

    Los filtros aplicados se incluyen como metadatos en la primera fila de comentario
    (#filtros: ...) y en el nombre del archivo. Cada fila es trazable por folio +
    número de siniestro (CA-2, CA-3, RN-3, RN-4, TC-051-02, TC-051-03).
    """
    reporte = generar_reporte(db, filtros)

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_descarga_csv",
        entity_id=f"{filtros.fecha_desde}..{filtros.fecha_hasta}|total={reporte.total}",
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados (incluyen folio, numero_siniestro e ingreso_id para trazabilidad)
    encabezados = [
        "ingreso_id",
        "folio",
        "numero_siniestro",
        "rut",
        "nombre_completo",
        "region",
        "fecha_denuncia",
        "tipo_denuncia",
        "estado_caso",
        "diagnostico_inicial",
        "diagnostico_post_reca",
        "profesional",
        "fecha_calificacion_reca",
        "reintegro_parcial",
        "reintegro_total",
        "alta_medica",
        "alta_psicologica",
        "alta_terapeutica",
    ]
    writer.writerow(encabezados)

    for fila in reporte.filas:
        writer.writerow([
            fila.ingreso_id,
            fila.folio,
            fila.numero_siniestro or "",
            fila.rut,
            fila.nombre_completo,
            fila.region or "",
            fila.fecha_denuncia or "",
            fila.tipo_denuncia or "",
            fila.estado_caso or "",
            fila.diagnostico_inicial or "",
            fila.diagnostico_post_reca or "",
            fila.profesional or "",
            fila.fecha_calificacion_reca or "",
            fila.reintegro_parcial,
            fila.reintegro_total,
            fila.alta_medica,
            fila.alta_psicologica,
            fila.alta_terapeutica,
        ])

    output.seek(0)
    nombre_archivo = (
        f"reporte_auditoria_{filtros.fecha_desde}_{filtros.fecha_hasta}.csv"
    )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )
```

- [ ] **Step 4: Registrar el router en `app/main.py`**

En `backend/app/main.py`, añadir la importación e inclusión del router de auditoría. El archivo debe quedar similar a:

```python
from fastapi import FastAPI

from app.config import get_settings
from app.routers import audit_log, auditoria  # añadir auditoria

app = FastAPI(title=get_settings().app_name)
app.include_router(audit_log.router)
app.include_router(auditoria.router)   # añadir esta línea


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

> Si `app/main.py` ya incluye otros routers de épicas anteriores (ingresos, fármacos, etc.), añadir solo las dos líneas de auditoría al bloque existente sin eliminar los demás.

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `uv run pytest tests/test_auditoria_api.py -v`
Expected: `18 passed`.

- [ ] **Step 6: Correr toda la suite para detectar regresiones**

Run: `uv run pytest -v`
Expected: todos los tests existentes siguen pasando.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/auditoria.py backend/app/main.py \
        backend/tests/test_auditoria_api.py
git commit -m "feat(auditoria): endpoints /api/v1/auditoria — vista consolidada y reportes con descarga CSV"
```

---

## Task 4: Verificación integral y lint

**Files:** ninguno nuevo.

- [ ] **Step 1: Suite completa**

Run (desde `backend/`):
```bash
uv run pytest -v
```
Expected: todos los tests pasan (sin regresiones en módulos anteriores).

- [ ] **Step 2: Lint**

Run:
```bash
uv run ruff check .
```
Expected: sin errores de lint.

- [ ] **Step 3: Verificar OpenAPI (documentación automática)**

Run: `uv run uvicorn app.main:app --reload` y en otra terminal:
```bash
curl -s localhost:8000/openapi.json | python3 -m json.tool | grep -A2 '"auditoria"'
```
Expected: los endpoints `/api/v1/auditoria/casos`, `/api/v1/auditoria/casos/{ingreso_id}`, `/api/v1/auditoria/reportes` y `/api/v1/auditoria/reportes/descargar` aparecen en la especificación OpenAPI. Detener con Ctrl-C.

- [ ] **Step 4: Verificar registro en log de auditoría**

Con la app corriendo, obtener un token Auditor y llamar a la vista consolidada:
```bash
# Obtener token (ajustar URL según EPIC-00)
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/token \
  -d "username=auditor_test&password=test" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Consultar caso (usar un ingreso_id real de la BD de dev)
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/auditoria/casos/1

# Verificar que la consulta quedó registrada en audit_log
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/audit-log | \
  python3 -c "import sys,json; [print(e) for e in json.load(sys.stdin) if e['entity']=='auditoria_caso']"
```
Expected: al menos una entrada con `entity="auditoria_caso"` y `action="READ"` en el log. Si `action="READ"` no está en el enum de EPIC-00, usar `action="CREATE"` y ajustar el llamado a `record_audit` en el router — ver Notas de cierre.

- [ ] **Step 5: Commit final (si quedó algo sin commitear)**

```bash
git add -A
git commit -m "chore(auditoria): EPIC-05 lista — vista consolidada + reportes CSV, suite en verde" \
  || echo "nada que commitear"
```

---

## Cobertura

| Historia | Task(s) | Criterios de Aceptación cubiertos | Test Cases cubiertos |
|----------|---------|-----------------------------------|----------------------|
| CEPA-050 — Vista consolidada | Task 1 (schemas), Task 2 (servicio), Task 3 (router) | CA-1, CA-2, CA-3, CA-4, CA-5 | TC-050-01, TC-050-02, TC-050-03, TC-050-04, TC-050-05, TC-050-06 |
| CEPA-051 — Reportes con filtros | Task 1 (schemas `FiltrosReporte`, `FilaReporteRead`, `ReporteAuditoriaRead`), Task 2 (servicio `generar_reporte`), Task 3 (router `/reportes` + `/reportes/descargar`) | CA-1, CA-2, CA-3, CA-4, CA-5 | TC-051-01, TC-051-02, TC-051-03, TC-051-04, TC-051-05 (≈ TC-051-06), TC-051-06 |

**Mapeo reglas de negocio → implementación:**

| Regla | Implementación |
|-------|---------------|
| RN-1 (solo lectura, sin editar datos clínicos) | Router no expone PUT/PATCH/DELETE; servicio usa solo `select()`; test `test_no_ofrece_endpoint_de_edicion` |
| RN-2 (Auditor sin edición, RBAC) | `_reader = require_role("Coordinacion", "Auditor")`; `as_admin` → 403 en todos los tests |
| RN-3 (folio como clave de consolidación; siniestro diferencia denuncias) | `get_caso_consolidado` agrupa por `ingreso_id`; `buscar_casos` filtra por `numero_siniestro`; tests TC-050-02 |
| RN-4 (dx inicial y post-RECA por separado) | `SeccionEvaluacionesRead` tiene ambos campos separados; tests TC-050-03 |
| RN-5/RN-7 (acceso registrado en log) | `record_audit` en cada endpoint; Task 4 Step 4 lo verifica |
| RN-6 (filtros combinables AND, período obligatorio) | `FiltrosReporte` con `@field_validator`; `generar_reporte` usa `and_(*condiciones)`; test `test_reporte_sin_periodo_devuelve_422` |

---

## Notas de cierre

### Dependencias de módulos 01-07 a verificar antes del loop

1. **Modelo `Ingreso`** (EPIC-01): el servicio de auditoría asume los campos `folio`, `numero_siniestro`, `fecha_denuncia`, `tipo_denuncia`, `fecha_derivacion`, `estado_caso`, `tipo_ingreso`, `programa` y la FK `paciente_id`. Verificar nombres exactos en `backend/app/models/ingreso.py` antes de ejecutar.

2. **Modelo `Seguimiento`** (EPIC-01): asume los campos `ingreso_id`, `fecha_eval_medica`, `fecha_eval_psicologica`, `fecha_calificacion_reca`, `diagnostico_inicial`, `diagnostico_post_reca`, `numero_sesiones_evaluacion`, `fecha_primera_consulta_medica`, `fecha_primera_consulta_psicologica`, `n_sesiones_medicas`, `n_sesiones_psicologicas`, `n_sesiones_ampliacion`, `alta_medica`, `fecha_alta_medica`, `alta_psicologica`, `fecha_alta_psicologica`, `alta_terapeutica`, `fecha_alta_terapeutica`, `estado_general`, `observaciones`. Si EPIC-01 distribuyó estos datos en tablas separadas (p. ej. tabla `alta` independiente), ajustar las consultas del servicio con joins adicionales.

3. **Modelo `Reintegro`** (EPIC-04): asume los campos `ingreso_id`, `parcial`, `fecha_parcial`, `total`, `fecha_total`. Verificar nombres reales.

4. **Modelo `Paciente`** (EPIC-01): asume `rut`, `nombre`, `sexo`, `edad`, `region`. Verificar que `region` existe en la tabla (podría ser `region_id` con FK a catálogo).

5. **`record_audit` y el campo `action`** (EPIC-00): el router usa `action="READ"` para registrar consultas de auditoría. Si el enum de EPIC-00 solo define `{CREATE, UPDATE, DELETE}`, añadir `READ` al enum o usar `CREATE` con prefijo en `entity` (p. ej. `entity="auditoria_read_caso"`). Alinear con el equipo antes del loop.

6. **Fixture `as_admin`** (EPIC-00): los tests asumen que `as_admin` corresponde al perfil `Administrativo`. Si el fixture usa el nombre `as_administrativo`, actualizar las referencias en `test_auditoria_api.py`.

7. **Modelos de EPIC-02 (Fármacos), EPIC-03 (EPT), EPIC-06 (Controles), EPIC-07 (Licencias)**: las importaciones en `test_auditoria_service.py` los menciona, pero el servicio actual en Task 2 no los consulta directamente (solo `Ingreso`, `Seguimiento`, `Reintegro`). Ampliar las consultas cuando esos módulos estén en `main` y se desee agregar sus datos a la vista consolidada; los tests de servicio solo ejercen lo que hoy está implementado.

### Decisiones abiertas del spec

- **D11 — Tipificación de altas:** el spec pregunta si hay una sola fecha de alta o fechas separadas por tipo. El plan asume tres campos separados (`alta_medica`, `alta_psicologica`, `alta_terapeutica`). Si Coordinación decide una fecha única, simplificar `SeccionCierreRead` a `fecha_alta: date | None` y ajustar el servicio y los tests correspondientes.

- **D2 — Reingresos con folio reutilizado:** si reingresos mantienen el folio original (en lugar de generar nuevo), la búsqueda por folio en `buscar_casos` puede retornar múltiples ingresos. El router actual los lista todos correctamente; confirmar con negocio si se desea mostrar solo el último.

- **Formatos de descarga:** el plan implementa CSV (el más solicitado en spec). Coordinar con EPIC-09 (Reportería) si se requiere XLSX o PDF para no duplicar el motor de reportes.

- **Filtro por profesional:** `FiltrosReporte.profesional` está definido en el schema pero el servicio actual no lo aplica (la relación entre ingreso y profesional depende de cómo EPIC-06 modele los controles y sus profesionales asignados). Completar cuando el modelo de `Control` esté disponible.

- **Paginación:** el reporte no está paginado en esta versión (TC-051-05 menciona ~800 casos). Para producción, añadir parámetros `skip`/`limit` al endpoint `/reportes` o cursor-based pagination; la descarga CSV puede servir el set completo. Evaluar antes del sprint de optimización.

- **TC-051-05 (rendimiento < 2 s):** no tiene un test automatizado de rendimiento en este plan. Si el volumen supera los 800 casos, revisar índices en `ingreso.fecha_denuncia`, `ingreso.estado_caso` y `paciente.rut`.
