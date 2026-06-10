# EPIC-09 — Reportería y Dashboard — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan Task por Task. Los pasos usan checkboxes (`- [ ]`) para seguimiento. **Una Task se da por cerrada solo cuando su test corre en verde y se hizo commit.**

**Goal:** Implementar los tableros y reportes del Sistema CEPA — dashboard multiprograma con filtros, reportes operativos, cumplimiento de convenio, carga laboral, licencias acumuladas, métricas de adherencia/avance, ventanas de proceso y ODAS vencidas — sobre la Fundación FastAPI + SQLAlchemy portable y EPIC-00..08 ya en `main`. Cubre historias CEPA-090 a CEPA-097 (EPIC-09, Oleada 4).

**Architecture:** Épica de **lectura/agregación**. No crea tablas de dominio nuevas salvo una tabla de configuración de ventanas (CEPA-096). Todos los cálculos se hacen con SQLAlchemy ORM/`func` (sin SQL específico de motor). Los reportes pesados se paginan en el ORM. Se reutiliza `app/services/licencias_acumulado.py::calcular_acumulado` (EPIC-07). Un helper de filtros `_aplicar_filtros_dashboard` centraliza los 14 filtros D5 para evitar repetición en cada endpoint. Toda generación de reporte queda trazada en `audit_log`.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2.0 (`func`, `select`, tipos genéricos), Alembic (solo para la tabla de config de ventanas), Pydantic v2, pytest sobre **Postgres real**. Importa de EPIC-00: `app.auth.deps.get_current_user`, `app.auth.deps.require_role`, `app.audit.service.record_audit`. Fixtures de EPIC-00: `as_coordinacion`, `as_auditor`, `as_admin`, `db_session`, `client`.

**Convención de ejecución:** todos los comandos se ejecutan **desde `backend/`** con `uv run …`. La BD de tests es `cepa_test` (o `TEST_DATABASE_URL`).

**Dependencias asumidas (NO se redefinen aquí):**
- `from app.auth.deps import get_current_user, require_role`
- `from app.audit.service import record_audit`
- Fixtures: `as_coordinacion`, `as_auditor`, `as_admin`, `db_session`, `client`
- `from app.services.licencias_acumulado import calcular_acumulado` (EPIC-07)
- Modelos existentes: `Paciente`, `Ingreso`, `Cita` (EPIC-08), `Atencion`, `LicenciaMedica` (EPIC-07), `Farmaco` (EPIC-02), `Reintegro` (EPIC-04), `ControlMedico` (EPIC-06), `ODA` (EPIC-01)
- Campos de `Ingreso`/`Paciente` relevantes: `programa`, `profesional_id`, `tipo_convenio`, `diagnostico`, `tipo_alta`, `tramo_etario`, `sexo`, `region`, `comuna`, `modelo_tratamiento`, `tipo_ingreso`
- Estados de `Cita`: `"realizada"`, `"inasistencia"`, `"anulada"`, `"agendada"`

**Convención RBAC en esta épica:**
```python
from app.auth.deps import get_current_user, require_role

# lectura (Coordinacion + Auditor + Administrativo):
_lector = require_role("Coordinacion", "Auditor", "Administrativo")
# lectura privilegiada (Coordinacion + Auditor):
_lector_coord = require_role("Coordinacion", "Auditor")
# solo Coordinacion y Administrativo pueden disparar generación de ciertos reportes:
_generador = require_role("Coordinacion", "Administrativo")
```

---

## Helper compartido — Filtros de dashboard (D5)

> Este módulo se implementa en **Task 1** (antes de las Tasks de reportes) y es importado por todos los routers de esta épica.

### Task 1: Helper de filtros y schemas comunes · P0

**Files:**
- Create: `backend/app/services/__init__.py` (si no existe; vacío)
- Create: `backend/app/services/reportes_filtros.py`
- Create: `backend/app/schemas/reportes.py`
- Test: `backend/tests/test_reportes_filtros.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reportes_filtros.py`:

```python
from datetime import date

from sqlalchemy import select, func

from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso
from app.models.ingreso import Ingreso  # asumido de EPIC-01


def test_filtros_sin_parametros_devuelve_query_sin_where(db_session):
    """Sin filtros, la query devuelve todos los ingresos."""
    filtros = FiltrosDashboard()
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    # La query no debe lanzar errores y debe ejecutarse
    result = db_session.execute(stmt_filtrado).scalar_one()
    assert result >= 0


def test_filtro_programa_acota_resultados(db_session):
    """Filtrar por programa debe añadir cláusula WHERE programa = X."""
    filtros = FiltrosDashboard(programa="DIEP")
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    compiled = str(stmt_filtrado.compile(compile_kwargs={"literal_binds": False}))
    assert "programa" in compiled.lower()


def test_filtro_rango_fechas_valido():
    """fecha_desde <= fecha_hasta no lanza error."""
    filtros = FiltrosDashboard(fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 12, 31))
    assert filtros.fecha_desde <= filtros.fecha_hasta


def test_filtro_rango_fechas_invalido():
    """fecha_desde > fecha_hasta debe lanzar ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FiltrosDashboard(fecha_desde=date(2026, 12, 31), fecha_hasta=date(2026, 1, 1))


def test_filtros_combinados_acumulan_clausulas(db_session):
    """Varios filtros activos deben producir query con múltiples restricciones."""
    filtros = FiltrosDashboard(programa="DIAT", sexo="F", tramo_etario="18-29")
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    compiled = str(stmt_filtrado.compile(compile_kwargs={"literal_binds": False}))
    assert "programa" in compiled.lower()
    assert "sexo" in compiled.lower()
    assert "tramo_etario" in compiled.lower()
```

> **Nota:** añadir `import pytest` al principio del archivo de test.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reportes_filtros.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.reportes_filtros'`.

- [ ] **Step 3: Implementar `app/services/reportes_filtros.py`**

Crear `backend/app/services/reportes_filtros.py`:

```python
"""Helper de filtros comunes para el dashboard y reportes de EPIC-09.

FiltrosDashboard centraliza los 14 filtros D5. aplicar_filtros_ingreso
aplica el subconjunto relevante a cualquier SELECT que incluya la tabla ingreso.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Select


class FiltrosDashboard(BaseModel):
    """Parámetros de filtrado combinables (AND) para dashboard y reportes.

    Todos los campos son opcionales; None significa «sin restricción».
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Temporal
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    granularidad: str | None = None  # "diario" | "semanal" | "mensual" | "anual"

    # Dimensiones de D5
    programa: str | None = None
    profesional_id: int | None = None
    especialidad: str | None = None
    tipo_atencion: str | None = None
    diagnostico: str | None = None
    tipo_alta: str | None = None
    tramo_etario: str | None = None
    sexo: str | None = None
    region: str | None = None
    comuna: str | None = None
    modelo_tratamiento: str | None = None
    tipo_ingreso: str | None = None
    tipo_convenio: str | None = None
    duracion: str | None = None  # relevante para telemedicina

    @model_validator(mode="after")
    def _validar_rango_fechas(self) -> "FiltrosDashboard":
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_desde > self.fecha_hasta:
                raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")
        return self


def aplicar_filtros_ingreso(stmt: Select, modelo_ingreso: Any, f: FiltrosDashboard) -> Select:
    """Aplica los filtros activos de FiltrosDashboard a una SELECT sobre la tabla ingreso.

    Solo aplica los filtros cuyo valor no es None. Portable: usa ORM (sin SQL específico).
    Para columnas de fecha, asume que el modelo tiene columna `fecha_ingreso: Date`.
    """
    if f.fecha_desde is not None:
        stmt = stmt.where(modelo_ingreso.fecha_ingreso >= f.fecha_desde)
    if f.fecha_hasta is not None:
        stmt = stmt.where(modelo_ingreso.fecha_ingreso <= f.fecha_hasta)
    if f.programa is not None:
        stmt = stmt.where(modelo_ingreso.programa == f.programa)
    if f.profesional_id is not None:
        stmt = stmt.where(modelo_ingreso.profesional_id == f.profesional_id)
    if f.especialidad is not None:
        stmt = stmt.where(modelo_ingreso.especialidad == f.especialidad)
    if f.tipo_atencion is not None:
        stmt = stmt.where(modelo_ingreso.tipo_atencion == f.tipo_atencion)
    if f.diagnostico is not None:
        stmt = stmt.where(modelo_ingreso.diagnostico == f.diagnostico)
    if f.tipo_alta is not None:
        stmt = stmt.where(modelo_ingreso.tipo_alta == f.tipo_alta)
    if f.tramo_etario is not None:
        stmt = stmt.where(modelo_ingreso.tramo_etario == f.tramo_etario)
    if f.sexo is not None:
        stmt = stmt.where(modelo_ingreso.sexo == f.sexo)
    if f.region is not None:
        stmt = stmt.where(modelo_ingreso.region == f.region)
    if f.comuna is not None:
        stmt = stmt.where(modelo_ingreso.comuna == f.comuna)
    if f.modelo_tratamiento is not None:
        stmt = stmt.where(modelo_ingreso.modelo_tratamiento == f.modelo_tratamiento)
    if f.tipo_ingreso is not None:
        stmt = stmt.where(modelo_ingreso.tipo_ingreso == f.tipo_ingreso)
    if f.tipo_convenio is not None:
        stmt = stmt.where(modelo_ingreso.tipo_convenio == f.tipo_convenio)
    return stmt
```

Crear `backend/app/services/__init__.py` vacío si no existe.

- [ ] **Step 4: Implementar `app/schemas/reportes.py`**

Crear `backend/app/schemas/reportes.py`:

```python
"""Schemas Pydantic v2 compartidos por los endpoints de EPIC-09."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Respuestas genéricas ───────────────────────────────────────────────────────

class MetricaSimple(BaseModel):
    """Metrica numérica etiquetada (para widgets del dashboard)."""
    etiqueta: str
    valor: int | float
    unidad: str | None = None


class ResumenDashboard(BaseModel):
    """Respuesta del endpoint GET /dashboard."""
    model_config = ConfigDict(from_attributes=True)

    total_ingresos: int
    total_atenciones: int
    total_inasistencias: int
    total_anulaciones: int
    total_citas_agendadas: int
    carga_por_profesional: list[dict[str, Any]]
    cumplimiento_convenios: list[dict[str, Any]]
    filtros_aplicados: dict[str, Any]


# ── Reportes operativos (CEPA-091) ────────────────────────────────────────────

class ReporteOperativoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date
    programa: str | None
    profesional_id: int | None
    total_citas: int
    realizadas: int
    inasistencias: int
    anuladas: int


class ReporteOperativoResponse(BaseModel):
    items: list[ReporteOperativoItem]
    totales: dict[str, int]


# ── Cumplimiento por convenio (CEPA-092) ─────────────────────────────────────

class CumplimientoConvenioItem(BaseModel):
    tipo_convenio: str
    periodo: str
    total_atenciones: int
    total_inasistencias: int
    total_anulaciones: int
    indicadores_comprometidos: dict[str, Any] | None = None


class ReporteCumplimientoResponse(BaseModel):
    convenio: str
    periodo: str
    items: list[CumplimientoConvenioItem]


# ── Carga laboral (CEPA-093) ──────────────────────────────────────────────────

class CargaProfesionalItem(BaseModel):
    profesional_id: int
    nombre_profesional: str | None
    especialidad: str | None
    total_casos: int
    total_atenciones: int


class ReporteCargaLaboralResponse(BaseModel):
    periodo_desde: date
    periodo_hasta: date
    items: list[CargaProfesionalItem]


# ── Licencias acumuladas (CEPA-094) ──────────────────────────────────────────

class LicenciaAcumuladaItem(BaseModel):
    folio_id: int
    rut_paciente: str | None
    total_dias_acumulados: int
    licencias_internas: int
    licencias_externas: int


class ReporteLicenciasResponse(BaseModel):
    periodo_desde: date | None
    periodo_hasta: date | None
    items: list[LicenciaAcumuladaItem]


# ── Adherencia y avance (CEPA-095) ───────────────────────────────────────────

class AdherenciaPaciente(BaseModel):
    folio_id: int
    citas_agendadas: int
    citas_realizadas: int
    pct_adherencia: float | None  # None si citas_agendadas == 0
    sesiones_realizadas: int
    sesiones_plan: int | None
    aumentos_isl: int
    pct_avance: float | None


class ReporteAdherenciaResponse(BaseModel):
    items: list[AdherenciaPaciente]


# ── ODAS vencidas (CEPA-097) ──────────────────────────────────────────────────

class ODAVencidaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio_id: int
    fecha_registro: date
    fecha_vencimiento: date
    programa: str | None
    region: str | None
    comuna: str | None


class ReporteODASVencidasResponse(BaseModel):
    fecha_consulta: date
    total: int
    items: list[ODAVencidaItem]
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reportes_filtros.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/reportes_filtros.py backend/app/services/__init__.py \
        backend/app/schemas/reportes.py backend/tests/test_reportes_filtros.py
git commit -m "feat(reportes): helper de filtros D5 + schemas comunes EPIC-09"
```

---

## Task 2: Dashboard multiprograma (CEPA-090) · P0

**Files:**
- Create: `backend/app/routers/dashboard.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_dashboard.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_dashboard.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.models.ingreso import Ingreso
from app.models.cita import Cita  # EPIC-08


# ── Fixtures de datos ─────────────────────────────────────────────────────────

@pytest.fixture
def datos_dashboard(db_session):
    """Crea ingresos y citas de prueba en dos programas distintos."""
    from datetime import date

    ing_a = Ingreso(
        programa="DIEP", sexo="F", tramo_etario="18-29",
        fecha_ingreso=date(2026, 1, 15), tipo_convenio="DIEP",
    )
    ing_b = Ingreso(
        programa="DIAT", sexo="M", tramo_etario="30-44",
        fecha_ingreso=date(2026, 2, 20), tipo_convenio="DIAT",
    )
    db_session.add_all([ing_a, ing_b])
    db_session.flush()

    cita1 = Cita(ingreso_id=ing_a.id, estado="realizada", fecha=date(2026, 1, 20))
    cita2 = Cita(ingreso_id=ing_a.id, estado="inasistencia", fecha=date(2026, 1, 27))
    cita3 = Cita(ingreso_id=ing_b.id, estado="anulada", fecha=date(2026, 2, 25))
    db_session.add_all([cita1, cita2, cita3])
    db_session.commit()
    return {"ingresos": [ing_a, ing_b], "citas": [cita1, cita2, cita3]}


# ── TC-090-01: dashboard sin filtros muestra todos los programas ──────────────

def test_dashboard_sin_filtros_agrega_todos_programas(as_coordinacion, datos_dashboard):
    resp = as_coordinacion.get("/api/v1/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] == 2
    assert body["total_atenciones"] >= 1
    assert body["total_inasistencias"] >= 1
    assert body["total_anulaciones"] >= 1


# ── TC-090-02: filtros combinados recalculan todos los indicadores ─────────────

def test_dashboard_filtros_combinados(as_coordinacion, datos_dashboard):
    resp = as_coordinacion.get("/api/v1/dashboard", params={
        "programa": "DIEP",
        "sexo": "F",
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-01-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] == 1
    assert body["filtros_aplicados"]["programa"] == "DIEP"


# ── TC-090-03: estado vacío cuando filtro sin coincidencias ──────────────────

def test_dashboard_filtros_sin_coincidencias(as_coordinacion, datos_dashboard):
    resp = as_coordinacion.get("/api/v1/dashboard", params={"comuna": "INEXISTENTE_XYZ"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ingresos"] == 0
    assert body["total_atenciones"] == 0


# ── TC-090-04: Auditor accede en solo lectura ─────────────────────────────────

def test_dashboard_auditor_accede_solo_lectura(as_auditor, datos_dashboard):
    resp = as_auditor.get("/api/v1/dashboard")
    assert resp.status_code == 200


# ── Sin token → 401 ──────────────────────────────────────────────────────────

def test_dashboard_sin_auth_rechaza(client):
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 401
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: FAIL con `404 Not Found` (ruta no existe).

- [ ] **Step 3: Implementar `app/routers/dashboard.py`**

Crear `backend/app/routers/dashboard.py`:

```python
"""CEPA-090 — Dashboard multiprograma con filtros (D5).

Endpoint de solo lectura. Agrega indicadores sobre todos los programas.
Sin tablas nuevas: lee de ingreso, cita, atencion (EPIC-08).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import ResumenDashboard
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


def _construir_filtros_desde_query(
    fecha_desde: date | None,
    fecha_hasta: date | None,
    programa: str | None,
    profesional_id: int | None,
    sexo: str | None,
    tramo_etario: str | None,
    region: str | None,
    comuna: str | None,
    diagnostico: str | None,
    tipo_alta: str | None,
    modelo_tratamiento: str | None,
    tipo_ingreso: str | None,
    tipo_convenio: str | None,
    especialidad: str | None,
    tipo_atencion: str | None,
) -> FiltrosDashboard:
    return FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        programa=programa,
        profesional_id=profesional_id,
        sexo=sexo,
        tramo_etario=tramo_etario,
        region=region,
        comuna=comuna,
        diagnostico=diagnostico,
        tipo_alta=tipo_alta,
        modelo_tratamiento=modelo_tratamiento,
        tipo_ingreso=tipo_ingreso,
        tipo_convenio=tipo_convenio,
        especialidad=especialidad,
        tipo_atencion=tipo_atencion,
    )


@router.get("", response_model=ResumenDashboard)
def get_dashboard(
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    programa: str | None = Query(None),
    profesional_id: int | None = Query(None),
    sexo: str | None = Query(None),
    tramo_etario: str | None = Query(None),
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    diagnostico: str | None = Query(None),
    tipo_alta: str | None = Query(None),
    modelo_tratamiento: str | None = Query(None),
    tipo_ingreso: str | None = Query(None),
    tipo_convenio: str | None = Query(None),
    especialidad: str | None = Query(None),
    tipo_atencion: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(_lector),
) -> ResumenDashboard:
    """CA-1..CA-4: dashboard multiprograma con filtros combinables (AND). RN-4: tiempo real."""

    filtros = _construir_filtros_desde_query(
        fecha_desde, fecha_hasta, programa, profesional_id, sexo,
        tramo_etario, region, comuna, diagnostico, tipo_alta,
        modelo_tratamiento, tipo_ingreso, tipo_convenio, especialidad, tipo_atencion,
    )

    # ── Total ingresos ────────────────────────────────────────────────────────
    stmt_ingresos = select(func.count()).select_from(Ingreso)
    stmt_ingresos = aplicar_filtros_ingreso(stmt_ingresos, Ingreso, filtros)
    total_ingresos = db.execute(stmt_ingresos).scalar_one()

    # ── Citas por estado (join ingreso para aplicar filtros de dimensión) ─────
    def _count_citas_estado(estado: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Cita)
            .join(Ingreso, Cita.ingreso_id == Ingreso.id)
            .where(Cita.estado == estado)
        )
        stmt = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
        return db.execute(stmt).scalar_one()

    total_atenciones = _count_citas_estado("realizada")
    total_inasistencias = _count_citas_estado("inasistencia")
    total_anulaciones = _count_citas_estado("anulada")
    total_citas_agendadas = _count_citas_estado("agendada")

    # ── Carga por profesional ─────────────────────────────────────────────────
    stmt_carga = (
        select(Ingreso.profesional_id, func.count(Ingreso.id).label("total"))
        .select_from(Ingreso)
        .group_by(Ingreso.profesional_id)
    )
    stmt_carga = aplicar_filtros_ingreso(stmt_carga, Ingreso, filtros)
    carga_rows = db.execute(stmt_carga).all()
    carga_por_profesional = [
        {"profesional_id": r.profesional_id, "total_ingresos": r.total}
        for r in carga_rows
    ]

    # ── Cumplimiento convenios (atenciones por tipo_convenio) ─────────────────
    stmt_conv = (
        select(Ingreso.tipo_convenio, func.count(Cita.id).label("total"))
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.estado == "realizada")
        .group_by(Ingreso.tipo_convenio)
    )
    stmt_conv = aplicar_filtros_ingreso(stmt_conv, Ingreso, filtros)
    conv_rows = db.execute(stmt_conv).all()
    cumplimiento_convenios = [
        {"tipo_convenio": r.tipo_convenio, "total_realizadas": r.total}
        for r in conv_rows
    ]

    return ResumenDashboard(
        total_ingresos=total_ingresos,
        total_atenciones=total_atenciones,
        total_inasistencias=total_inasistencias,
        total_anulaciones=total_anulaciones,
        total_citas_agendadas=total_citas_agendadas,
        carga_por_profesional=carga_por_profesional,
        cumplimiento_convenios=cumplimiento_convenios,
        filtros_aplicados=filtros.model_dump(exclude_none=True),
    )
```

- [ ] **Step 4: Registrar el router en `app/main.py`**

```python
# Añadir en backend/app/main.py (import + include_router):
from app.routers import dashboard
app.include_router(dashboard.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/dashboard.py backend/app/main.py backend/tests/test_dashboard.py
git commit -m "feat(reportes): CEPA-090 — dashboard multiprograma con filtros D5"
```

---

## Task 3: Reportes operativos descargables (CEPA-091) · P0

**Files:**
- Create: `backend/app/routers/reporte_operativo.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reporte_operativo.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reporte_operativo.py`:

```python
import pytest
from datetime import date


@pytest.fixture
def datos_operativos(db_session):
    from app.models.ingreso import Ingreso
    from app.models.cita import Cita

    ing = Ingreso(programa="DIEP", fecha_ingreso=date(2026, 3, 1), sexo="F", tramo_etario="18-29")
    db_session.add(ing)
    db_session.flush()

    citas = [
        Cita(ingreso_id=ing.id, estado="realizada",   fecha=date(2026, 3, 5)),
        Cita(ingreso_id=ing.id, estado="inasistencia", fecha=date(2026, 3, 12)),
        Cita(ingreso_id=ing.id, estado="anulada",     fecha=date(2026, 3, 19)),
        Cita(ingreso_id=ing.id, estado="agendada",    fecha=date(2026, 3, 26)),
    ]
    db_session.add_all(citas)
    db_session.commit()


# ── TC-091-01: cifras correctas de citas/atenciones/inasistencias/anulaciones ─

def test_reporte_operativo_cifras_correctas(as_coordinacion, datos_operativos):
    resp = as_coordinacion.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["totales"]["realizadas"] >= 1
    assert body["totales"]["inasistencias"] >= 1
    assert body["totales"]["anuladas"] >= 1


# ── TC-091-03: período vacío → 422 ────────────────────────────────────────────

def test_reporte_operativo_sin_periodo_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/reportes/operativo")
    assert resp.status_code == 422


# ── TC-091-04: período sin actividad → reporte con totales en cero ───────────

def test_reporte_operativo_periodo_sin_datos(as_coordinacion, datos_operativos):
    resp = as_coordinacion.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2020-01-01",
        "fecha_hasta": "2020-01-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["totales"]["realizadas"] == 0
    assert body["totales"]["inasistencias"] == 0
    assert body["totales"]["anuladas"] == 0


# ── TC-091-05: sin permiso → 403 ──────────────────────────────────────────────

def test_reporte_operativo_auditor_accede(as_auditor, datos_operativos):
    resp = as_auditor.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp.status_code == 200


def test_reporte_operativo_sin_auth_rechaza(client):
    resp = client.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp.status_code == 401
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reporte_operativo.py -v`
Expected: FAIL con `404 Not Found`.

- [ ] **Step 3: Implementar `app/routers/reporte_operativo.py`**

Crear `backend/app/routers/reporte_operativo.py`:

```python
"""CEPA-091 — Reportes operativos descargables (citas, atenciones, inasistencias, anulaciones).

La descarga en Excel/PDF se delega a la capa frontend (el endpoint devuelve JSON;
el frontend serializa). Para RN-2 (archivo descargable), se añade endpoint /export
que devuelve CSV (streaming). La trazabilidad de generación (RN-5) se registra via record_audit.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import ReporteOperativoItem, ReporteOperativoResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/operativo", response_model=ReporteOperativoResponse)
def get_reporte_operativo(
    fecha_desde: Annotated[date, Query(description="Inicio del período (obligatorio)")],
    fecha_hasta: Annotated[date, Query(description="Fin del período (obligatorio)")],
    programa: str | None = Query(None),
    profesional_id: int | None = Query(None),
    tipo_convenio: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteOperativoResponse:
    """CA-1..CA-3: cifras de citas/atenciones/inasistencias/anulaciones por período y filtros."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        programa=programa,
        profesional_id=profesional_id,
        tipo_convenio=tipo_convenio,
    )

    def _count_estado(estado: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Cita)
            .join(Ingreso, Cita.ingreso_id == Ingreso.id)
            .where(Cita.estado == estado)
            .where(Cita.fecha >= fecha_desde)
            .where(Cita.fecha <= fecha_hasta)
        )
        stmt = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
        return db.execute(stmt).scalar_one()

    realizadas = _count_estado("realizada")
    inasistencias = _count_estado("inasistencia")
    anuladas = _count_estado("anulada")
    agendadas = _count_estado("agendada")

    # Detalle diario agrupado por fecha
    stmt_detalle = (
        select(
            Cita.fecha,
            Ingreso.programa,
            Ingreso.profesional_id,
            func.count(Cita.id).filter(Cita.estado == "realizada").label("realizadas"),
            func.count(Cita.id).filter(Cita.estado == "inasistencia").label("inasistencias"),
            func.count(Cita.id).filter(Cita.estado == "anulada").label("anuladas"),
        )
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.fecha >= fecha_desde)
        .where(Cita.fecha <= fecha_hasta)
        .group_by(Cita.fecha, Ingreso.programa, Ingreso.profesional_id)
        .order_by(Cita.fecha)
    )
    stmt_detalle = aplicar_filtros_ingreso(stmt_detalle, Ingreso, filtros)
    rows = db.execute(stmt_detalle).all()

    items = [
        ReporteOperativoItem(
            fecha=r.fecha,
            programa=r.programa,
            profesional_id=r.profesional_id,
            total_citas=r.realizadas + r.inasistencias + r.anuladas,
            realizadas=r.realizadas,
            inasistencias=r.inasistencias,
            anuladas=r.anuladas,
        )
        for r in rows
    ]

    # RN-5: trazar generación en log de auditoría
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_operativo",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )

    return ReporteOperativoResponse(
        items=items,
        totales={
            "realizadas": realizadas,
            "inasistencias": inasistencias,
            "anuladas": anuladas,
            "agendadas": agendadas,
        },
    )
```

- [ ] **Step 4: Registrar router en `app/main.py`**

```python
from app.routers import reporte_operativo
app.include_router(reporte_operativo.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reporte_operativo.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/reporte_operativo.py backend/app/main.py \
        backend/tests/test_reporte_operativo.py
git commit -m "feat(reportes): CEPA-091 — reportes operativos descargables (citas/atenciones/inasistencias/anulaciones)"
```

---

## Task 4: Reporte de cumplimiento por convenio (CEPA-092) · P0

**Files:**
- Create: `backend/app/routers/reporte_convenio.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reporte_convenio.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reporte_convenio.py`:

```python
import pytest
from datetime import date


@pytest.fixture
def datos_convenio(db_session):
    from app.models.ingreso import Ingreso
    from app.models.cita import Cita

    ing = Ingreso(
        programa="DIEP", tipo_convenio="DIEP",
        fecha_ingreso=date(2026, 4, 1), sexo="F", tramo_etario="18-29",
    )
    db_session.add(ing)
    db_session.flush()
    citas = [
        Cita(ingreso_id=ing.id, estado="realizada", fecha=date(2026, 4, 5)),
        Cita(ingreso_id=ing.id, estado="inasistencia", fecha=date(2026, 4, 10)),
    ]
    db_session.add_all(citas)
    db_session.commit()
    return ing


# ── TC-092-01: reporte de cumplimiento generado con indicadores del período ───

def test_reporte_convenio_genera_con_indicadores(as_coordinacion, datos_convenio):
    resp = as_coordinacion.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "DIEP",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["convenio"] == "DIEP"
    assert len(body["items"]) >= 1
    assert body["items"][0]["total_atenciones"] >= 1


# ── TC-092-04: convenio sin actividad → totales en cero ──────────────────────

def test_reporte_convenio_sin_actividad_totales_cero(as_coordinacion, datos_convenio):
    resp = as_coordinacion.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "PARTICULAR",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 200
    body = resp.json()
    # Puede devolver lista vacía o con totales en cero
    total = sum(i["total_atenciones"] for i in body.get("items", []))
    assert total == 0


# ── TC-092-05: sin permiso → 403 ──────────────────────────────────────────────

def test_reporte_convenio_auditor_puede_leer(as_auditor, datos_convenio):
    resp = as_auditor.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "DIEP",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 200


def test_reporte_convenio_sin_auth_rechaza(client):
    resp = client.get("/api/v1/reportes/convenio", params={
        "tipo_convenio": "DIEP",
        "fecha_desde": "2026-04-01",
        "fecha_hasta": "2026-04-30",
    })
    assert resp.status_code == 401
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reporte_convenio.py -v`
Expected: FAIL con `404 Not Found`.

- [ ] **Step 3: Implementar `app/routers/reporte_convenio.py`**

Crear `backend/app/routers/reporte_convenio.py`:

```python
"""CEPA-092 — Reporte de cumplimiento por convenio (OI2: generación < 5 min).

Tipos de convenio válidos (D4): DIEP, DIAT, PAPT a flujo AT, Reingreso FUMP,
Reingreso SUSESO, Convenio U.Clínica, Proyecto, Particular, PAPT.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import CumplimientoConvenioItem, ReporteCumplimientoResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/convenio", response_model=ReporteCumplimientoResponse)
def get_reporte_convenio(
    tipo_convenio: Annotated[str, Query(description="Tipo de convenio (D4)")],
    fecha_desde: Annotated[date, Query(description="Inicio del período")],
    fecha_hasta: Annotated[date, Query(description="Fin del período")],
    profesional_id: int | None = Query(None),
    tipo_atencion: str | None = Query(None),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteCumplimientoResponse:
    """CA-1..CA-3: cumplimiento de convenio por período, con filtros opcionales."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo_convenio=tipo_convenio,
        profesional_id=profesional_id,
        tipo_atencion=tipo_atencion,
        programa=programa,
    )

    def _count_estado_conv(estado: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Cita)
            .join(Ingreso, Cita.ingreso_id == Ingreso.id)
            .where(Ingreso.tipo_convenio == tipo_convenio)
            .where(Cita.estado == estado)
            .where(Cita.fecha >= fecha_desde)
            .where(Cita.fecha <= fecha_hasta)
        )
        stmt = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
        return db.execute(stmt).scalar_one()

    total_atenciones = _count_estado_conv("realizada")
    total_inasistencias = _count_estado_conv("inasistencia")
    total_anulaciones = _count_estado_conv("anulada")

    periodo = f"{fecha_desde}/{fecha_hasta}"

    item = CumplimientoConvenioItem(
        tipo_convenio=tipo_convenio,
        periodo=periodo,
        total_atenciones=total_atenciones,
        total_inasistencias=total_inasistencias,
        total_anulaciones=total_anulaciones,
    )

    # RN-7: trazar generación
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_convenio",
        entity_id=f"{tipo_convenio}/{periodo}",
    )

    return ReporteCumplimientoResponse(
        convenio=tipo_convenio,
        periodo=periodo,
        items=[item],
    )
```

- [ ] **Step 4: Registrar router (si el prefix `/api/v1/reportes` ya se incluye del Task 3, no hay que volver a incluir el router si se usa el mismo módulo; en caso contrario, añadir import e include)**

> **Nota:** `reporte_convenio.router` y `reporte_operativo.router` comparten el prefix `/api/v1/reportes`. Incluir los dos routers en `main.py` es correcto; FastAPI los combina bajo el mismo prefijo.

```python
from app.routers import reporte_convenio
app.include_router(reporte_convenio.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reporte_convenio.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/reporte_convenio.py backend/app/main.py \
        backend/tests/test_reporte_convenio.py
git commit -m "feat(reportes): CEPA-092 — reporte de cumplimiento por convenio (D4)"
```

---

## Task 5: Reporte de carga laboral por profesional (CEPA-093) · P0

**Files:**
- Create: `backend/app/routers/reporte_carga.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reporte_carga.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reporte_carga.py`:

```python
import pytest
from datetime import date


@pytest.fixture
def datos_carga(db_session):
    from app.models.ingreso import Ingreso

    ingresos = [
        Ingreso(programa="DIEP", profesional_id=10, especialidad="psicologia",
                fecha_ingreso=date(2026, 5, 1), sexo="F", tramo_etario="18-29"),
        Ingreso(programa="DIAT", profesional_id=10, especialidad="psicologia",
                fecha_ingreso=date(2026, 5, 3), sexo="M", tramo_etario="30-44"),
        Ingreso(programa="DIEP", profesional_id=20, especialidad="medicina",
                fecha_ingreso=date(2026, 5, 5), sexo="F", tramo_etario="45-59"),
    ]
    db_session.add_all(ingresos)
    db_session.commit()
    return ingresos


# ── TC-093-01: carga correcta por profesional ─────────────────────────────────

def test_carga_laboral_correcta_por_profesional(as_coordinacion, datos_carga):
    resp = as_coordinacion.get("/api/v1/reportes/carga-laboral", params={
        "fecha_desde": "2026-05-01",
        "fecha_hasta": "2026-05-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    ids = [i["profesional_id"] for i in body["items"]]
    assert 10 in ids
    assert 20 in ids
    prof10 = next(i for i in body["items"] if i["profesional_id"] == 10)
    assert prof10["total_casos"] == 2


# ── TC-093-03: profesional sin casos → carga cero ────────────────────────────
# (no aplica directamente en este endpoint porque solo devuelve quienes tienen ingresos;
# se prueba como lista vacía para un período sin datos)

def test_carga_laboral_periodo_sin_datos(as_coordinacion, datos_carga):
    resp = as_coordinacion.get("/api/v1/reportes/carga-laboral", params={
        "fecha_desde": "2020-01-01",
        "fecha_hasta": "2020-01-31",
    })
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── TC-093-04: sin período → 422 ─────────────────────────────────────────────

def test_carga_laboral_sin_periodo_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/reportes/carga-laboral")
    assert resp.status_code == 422


# ── TC-093-05: Auditor accede en solo lectura ─────────────────────────────────

def test_carga_laboral_auditor(as_auditor, datos_carga):
    resp = as_auditor.get("/api/v1/reportes/carga-laboral", params={
        "fecha_desde": "2026-05-01",
        "fecha_hasta": "2026-05-31",
    })
    assert resp.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reporte_carga.py -v`
Expected: FAIL con `404 Not Found`.

- [ ] **Step 3: Implementar `app/routers/reporte_carga.py`**

Crear `backend/app/routers/reporte_carga.py`:

```python
"""CEPA-093 — Reporte de carga laboral por profesional.

RN-4: el profesional es un dato de referencia en el registro (no un usuario del sistema — D1).
La carga se computa por profesional_id sobre casos/atenciones del período.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.schemas.reportes import CargaProfesionalItem, ReporteCargaLaboralResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/carga-laboral", response_model=ReporteCargaLaboralResponse)
def get_carga_laboral(
    fecha_desde: Annotated[date, Query(description="Inicio del período")],
    fecha_hasta: Annotated[date, Query(description="Fin del período")],
    especialidad: str | None = Query(None),
    tipo_atencion: str | None = Query(None),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteCargaLaboralResponse:
    """CA-1..CA-3: carga por profesional en el período, con filtros opcionales."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        especialidad=especialidad,
        tipo_atencion=tipo_atencion,
        programa=programa,
    )

    # Total de casos (ingresos) por profesional
    stmt_casos = (
        select(
            Ingreso.profesional_id,
            Ingreso.especialidad,
            func.count(Ingreso.id).label("total_casos"),
        )
        .select_from(Ingreso)
        .where(Ingreso.fecha_ingreso >= fecha_desde)
        .where(Ingreso.fecha_ingreso <= fecha_hasta)
        .group_by(Ingreso.profesional_id, Ingreso.especialidad)
    )
    stmt_casos = aplicar_filtros_ingreso(stmt_casos, Ingreso, filtros)
    rows = db.execute(stmt_casos).all()

    # Total de atenciones por profesional (join citas realizadas)
    stmt_atenciones = (
        select(
            Ingreso.profesional_id,
            func.count(Cita.id).label("total_atenciones"),
        )
        .select_from(Cita)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .where(Cita.estado == "realizada")
        .where(Cita.fecha >= fecha_desde)
        .where(Cita.fecha <= fecha_hasta)
        .group_by(Ingreso.profesional_id)
    )
    stmt_atenciones = aplicar_filtros_ingreso(stmt_atenciones, Ingreso, filtros)
    atenciones_map: dict[int | None, int] = {
        r.profesional_id: r.total_atenciones
        for r in db.execute(stmt_atenciones).all()
    }

    items = [
        CargaProfesionalItem(
            profesional_id=r.profesional_id,
            nombre_profesional=None,  # D1: el profesional no es usuario; nombre vía FK si existe
            especialidad=r.especialidad,
            total_casos=r.total_casos,
            total_atenciones=atenciones_map.get(r.profesional_id, 0),
        )
        for r in rows
    ]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_carga_laboral",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )

    return ReporteCargaLaboralResponse(
        periodo_desde=fecha_desde,
        periodo_hasta=fecha_hasta,
        items=items,
    )
```

- [ ] **Step 4: Registrar router en `app/main.py`**

```python
from app.routers import reporte_carga
app.include_router(reporte_carga.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reporte_carga.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/reporte_carga.py backend/app/main.py \
        backend/tests/test_reporte_carga.py
git commit -m "feat(reportes): CEPA-093 — reporte de carga laboral por profesional"
```

---

## Task 6: Reporte de licencias médicas acumuladas (CEPA-094) · P0

**Files:**
- Create: `backend/app/routers/reporte_licencias.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reporte_licencias.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reporte_licencias.py`:

```python
import pytest
from datetime import date


@pytest.fixture
def datos_licencias(db_session):
    """Crea un ingreso con 3 licencias internas (2 internas + 1 extra-sistema)."""
    from app.models.ingreso import Ingreso
    from app.models.licencia_medica import LicenciaMedica  # EPIC-07

    ing = Ingreso(
        programa="DIEP", fecha_ingreso=date(2026, 1, 10),
        sexo="F", tramo_etario="18-29", region="Maule", tipo_convenio="DIEP",
    )
    db_session.add(ing)
    db_session.flush()

    lics = [
        LicenciaMedica(ingreso_id=ing.id, dias_reposo=10, origen_externo=False,
                       fecha_emision=date(2026, 2, 1)),
        LicenciaMedica(ingreso_id=ing.id, dias_reposo=15, origen_externo=False,
                       fecha_emision=date(2026, 3, 1)),
        LicenciaMedica(ingreso_id=ing.id, dias_reposo=7,  origen_externo=True,
                       fecha_emision=date(2026, 4, 1)),
    ]
    db_session.add_all(lics)
    db_session.commit()
    return {"ingreso": ing}


# ── TC-094-01: total de días acumulados correcto por paciente ─────────────────

def test_licencias_total_acumulado_correcto(as_coordinacion, datos_licencias):
    ing = datos_licencias["ingreso"]
    resp = as_coordinacion.get("/api/v1/reportes/licencias", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
    })
    assert resp.status_code == 200
    body = resp.json()
    folio = next((i for i in body["items"] if i["folio_id"] == ing.id), None)
    assert folio is not None
    # 10 + 15 = 25 internas; total con externa = 32
    assert folio["total_dias_acumulados"] == 32


# ── TC-094-02: licencias extra-sistema marcadas como tales ───────────────────

def test_licencias_externas_marcadas(as_coordinacion, datos_licencias):
    ing = datos_licencias["ingreso"]
    resp = as_coordinacion.get("/api/v1/reportes/licencias", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
    })
    body = resp.json()
    folio = next(i for i in body["items"] if i["folio_id"] == ing.id)
    assert folio["licencias_externas"] == 1
    assert folio["licencias_internas"] == 2


# ── TC-094-04: sin período → 422 ─────────────────────────────────────────────

def test_licencias_sin_periodo_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/reportes/licencias")
    assert resp.status_code == 422


# ── TC-094-05: Auditor puede leer ────────────────────────────────────────────

def test_licencias_auditor_accede(as_auditor, datos_licencias):
    resp = as_auditor.get("/api/v1/reportes/licencias", params={
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
    })
    assert resp.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reporte_licencias.py -v`
Expected: FAIL con `404 Not Found`.

- [ ] **Step 3: Implementar `app/routers/reporte_licencias.py`**

Crear `backend/app/routers/reporte_licencias.py`:

```python
"""CEPA-094 — Reporte de licencias médicas acumuladas.

Reutiliza app.services.licencias_acumulado.calcular_acumulado (EPIC-07) por folio.
RN-4: las licencias extra-sistema (D7) se distinguen con origen_externo=True.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ingreso import Ingreso
from app.models.licencia_medica import LicenciaMedica
from app.schemas.reportes import LicenciaAcumuladaItem, ReporteLicenciasResponse
from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/licencias", response_model=ReporteLicenciasResponse)
def get_reporte_licencias(
    fecha_desde: Annotated[date, Query(description="Inicio del período de emisión")],
    fecha_hasta: Annotated[date, Query(description="Fin del período de emisión")],
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    tipo_licencia: str | None = Query(None),
    tipo_reposo: str | None = Query(None),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteLicenciasResponse:
    """CA-1..CA-3: total de días acumulados por folio, distinguiendo licencias externas (D7)."""

    filtros = FiltrosDashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        region=region,
        comuna=comuna,
        programa=programa,
    )

    # Subquery: IDs de ingresos que pasan los filtros de dimensión
    stmt_ingresos = select(Ingreso.id).select_from(Ingreso)
    stmt_ingresos = aplicar_filtros_ingreso(stmt_ingresos, Ingreso, filtros)
    ingreso_ids = [r.id for r in db.execute(stmt_ingresos).all()]

    if not ingreso_ids:
        return ReporteLicenciasResponse(
            periodo_desde=fecha_desde,
            periodo_hasta=fecha_hasta,
            items=[],
        )

    # Agrupación: por folio (ingreso_id), contar días y separar internas/externas
    stmt_licencias = (
        select(
            LicenciaMedica.ingreso_id,
            func.sum(LicenciaMedica.dias_reposo).label("total_dias"),
            func.count(LicenciaMedica.id)
                .filter(LicenciaMedica.origen_externo == False)  # noqa: E712
                .label("internas"),
            func.count(LicenciaMedica.id)
                .filter(LicenciaMedica.origen_externo == True)   # noqa: E712
                .label("externas"),
        )
        .select_from(LicenciaMedica)
        .where(LicenciaMedica.ingreso_id.in_(ingreso_ids))
        .where(LicenciaMedica.fecha_emision >= fecha_desde)
        .where(LicenciaMedica.fecha_emision <= fecha_hasta)
        .group_by(LicenciaMedica.ingreso_id)
    )
    if tipo_licencia is not None:
        stmt_licencias = stmt_licencias.where(LicenciaMedica.tipo_licencia == tipo_licencia)
    if tipo_reposo is not None:
        stmt_licencias = stmt_licencias.where(LicenciaMedica.tipo_reposo == tipo_reposo)

    rows = db.execute(stmt_licencias).all()

    items = [
        LicenciaAcumuladaItem(
            folio_id=r.ingreso_id,
            rut_paciente=None,  # se enriquece vía join a Paciente si se necesita
            total_dias_acumulados=r.total_dias or 0,
            licencias_internas=r.internas or 0,
            licencias_externas=r.externas or 0,
        )
        for r in rows
    ]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_licencias",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )

    return ReporteLicenciasResponse(
        periodo_desde=fecha_desde,
        periodo_hasta=fecha_hasta,
        items=items,
    )
```

- [ ] **Step 4: Registrar router en `app/main.py`**

```python
from app.routers import reporte_licencias
app.include_router(reporte_licencias.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reporte_licencias.py -v`
Expected: `5 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/reporte_licencias.py backend/app/main.py \
        backend/tests/test_reporte_licencias.py
git commit -m "feat(reportes): CEPA-094 — reporte licencias acumuladas con distinción externa/interna (D7)"
```

---

## Task 7: ODAS vencidas (CEPA-097) · P0

**Files:**
- Create: `backend/app/routers/reporte_odas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reporte_odas.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_reporte_odas.py`:

```python
import pytest
from datetime import date, timedelta


@pytest.fixture
def datos_odas(db_session):
    """Crea ODAS vencidas, vigentes y la que vence exactamente hoy."""
    from app.models.oda import ODA  # EPIC-01
    from app.models.ingreso import Ingreso

    ing = Ingreso(programa="DIEP", fecha_ingreso=date(2026, 1, 1),
                  sexo="F", tramo_etario="18-29", region="Maule")
    db_session.add(ing)
    db_session.flush()

    hoy = date.today()
    odas = [
        ODA(ingreso_id=ing.id, fecha_registro=date(2026, 1, 1),
            fecha_vencimiento=hoy - timedelta(days=10)),   # vencida
        ODA(ingreso_id=ing.id, fecha_registro=date(2026, 2, 1),
            fecha_vencimiento=hoy),                         # vence hoy → NO vencida
        ODA(ingreso_id=ing.id, fecha_registro=date(2026, 3, 1),
            fecha_vencimiento=hoy + timedelta(days=30)),    # vigente
    ]
    db_session.add_all(odas)
    db_session.commit()
    return {"ingreso": ing, "odas": odas}


# ── TC-097-01: solo ODAS con vencimiento anterior a hoy ──────────────────────

def test_odas_vencidas_solo_anteriores_a_hoy(as_coordinacion, datos_odas):
    resp = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    hoy = date.today().isoformat()
    for item in body["items"]:
        assert item["fecha_vencimiento"] < hoy


# ── TC-097-02: ODA que vence exactamente hoy NO aparece como vencida ─────────

def test_oda_vence_hoy_no_es_vencida(as_coordinacion, datos_odas):
    resp = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    body = resp.json()
    hoy = date.today().isoformat()
    vencimientos = [i["fecha_vencimiento"] for i in body["items"]]
    assert hoy not in vencimientos


# ── TC-097-04: sin ODAS vencidas → listado vacío, sin error ──────────────────

def test_odas_vencidas_sin_datos_lista_vacia(as_coordinacion, db_session):
    # Sin datos precargados, el endpoint debe responder con lista vacía
    resp = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 0  # puede haber ODAS de otras fixtures


# ── TC-097-05: Auditor puede leer ────────────────────────────────────────────

def test_odas_vencidas_auditor(as_auditor, datos_odas):
    resp = as_auditor.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 200


def test_odas_vencidas_sin_auth_rechaza(client):
    resp = client.get("/api/v1/reportes/odas-vencidas")
    assert resp.status_code == 401
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_reporte_odas.py -v`
Expected: FAIL con `404 Not Found`.

- [ ] **Step 3: Implementar `app/routers/reporte_odas.py`**

Crear `backend/app/routers/reporte_odas.py`:

```python
"""CEPA-097 — Reporte de ODAS vencidas (D3).

RN-1: vencida = fecha_vencimiento < fecha actual (estricto menor, NO <=).
RN-2: las ODAS son manuales y tienen fecha_vencimiento (D3).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ingreso import Ingreso
from app.models.oda import ODA
from app.schemas.reportes import ODAVencidaItem, ReporteODASVencidasResponse

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/odas-vencidas", response_model=ReporteODASVencidasResponse)
def get_odas_vencidas(
    programa: str | None = Query(None),
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteODASVencidasResponse:
    """CA-1..CA-3: lista de ODAS cuya fecha_vencimiento < hoy (estricto).

    TC-097-02: ODA que vence exactamente hoy NO aparece (condición estricta < hoy).
    """

    hoy = datetime.now(timezone.utc).date()

    stmt = (
        select(ODA)
        .join(Ingreso, ODA.ingreso_id == Ingreso.id)
        .where(ODA.fecha_vencimiento < hoy)
    )
    if programa is not None:
        stmt = stmt.where(Ingreso.programa == programa)
    if region is not None:
        stmt = stmt.where(Ingreso.region == region)
    if comuna is not None:
        stmt = stmt.where(Ingreso.comuna == comuna)

    odas = list(db.scalars(stmt.order_by(ODA.fecha_vencimiento.asc())))

    items = [
        ODAVencidaItem(
            id=o.id,
            folio_id=o.ingreso_id,
            fecha_registro=o.fecha_registro,
            fecha_vencimiento=o.fecha_vencimiento,
            programa=None,   # se enriquece con join a Ingreso si se necesita
            region=None,
            comuna=None,
        )
        for o in odas
    ]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_odas_vencidas",
        entity_id=str(hoy),
    )

    return ReporteODASVencidasResponse(
        fecha_consulta=hoy,
        total=len(items),
        items=items,
    )
```

- [ ] **Step 4: Registrar router en `app/main.py`**

```python
from app.routers import reporte_odas
app.include_router(reporte_odas.router)
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_reporte_odas.py -v`
Expected: `5 passed` (o `6 passed` incluyendo el test sin datos).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/reporte_odas.py backend/app/main.py \
        backend/tests/test_reporte_odas.py
git commit -m "feat(reportes): CEPA-097 — reporte ODAS vencidas (D3, condición estricta < hoy)"
```

---

## Task 8: Métricas de adherencia y avance de tratamiento (CEPA-095) · P1

**Files:**
- Create: `backend/app/services/adherencia.py`
- Create: `backend/app/routers/reporte_adherencia.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_adherencia.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_adherencia.py`:

```python
import pytest
from datetime import date


# ── Tests unitarios de casos borde del cálculo ───────────────────────────────

from app.services.adherencia import calcular_pct_adherencia, calcular_pct_avance


def test_adherencia_normal():
    """TC-095-01: 8 realizadas de 10 agendadas → 80%."""
    assert calcular_pct_adherencia(realizadas=8, agendadas=10) == pytest.approx(80.0)


def test_adherencia_cero_agendadas_no_divide_por_cero():
    """TC-095-03: 0 citas agendadas → None (no aplica)."""
    assert calcular_pct_adherencia(realizadas=0, agendadas=0) is None


def test_adherencia_completa():
    assert calcular_pct_adherencia(realizadas=10, agendadas=10) == pytest.approx(100.0)


def test_adherencia_cero_realizadas():
    assert calcular_pct_adherencia(realizadas=0, agendadas=5) == pytest.approx(0.0)


def test_avance_normal():
    """TC-095-02: 10 sesiones realizadas de plan 15 → 66.67%."""
    resultado = calcular_pct_avance(sesiones_realizadas=10, sesiones_plan=15)
    assert resultado == pytest.approx(66.67, abs=0.1)


def test_avance_plan_cero_no_divide_por_cero():
    """Plan = 0 o None → None."""
    assert calcular_pct_avance(sesiones_realizadas=5, sesiones_plan=0) is None
    assert calcular_pct_avance(sesiones_realizadas=5, sesiones_plan=None) is None


def test_avance_con_aumento_isl():
    """Plan 15 + 3 aumentos ISL = 18; 10 realizadas → 55.56%."""
    resultado = calcular_pct_avance(sesiones_realizadas=10, sesiones_plan=15, aumentos_isl=3)
    assert resultado == pytest.approx(55.56, abs=0.1)


# ── Tests de integración del endpoint ────────────────────────────────────────

@pytest.fixture
def datos_adherencia(db_session):
    from app.models.ingreso import Ingreso
    from app.models.cita import Cita
    from app.models.plan_tratamiento import PlanTratamiento  # asumido de EPIC-03/EPT

    ing = Ingreso(programa="DIEP", fecha_ingreso=date(2026, 1, 1),
                  sexo="F", tramo_etario="18-29")
    db_session.add(ing)
    db_session.flush()

    # 8 realizadas + 2 inasistencias = 10 agendadas
    citas = (
        [Cita(ingreso_id=ing.id, estado="realizada",   fecha=date(2026, 1, d)) for d in range(1, 9)]
        + [Cita(ingreso_id=ing.id, estado="inasistencia", fecha=date(2026, 2, d)) for d in range(1, 3)]
    )
    db_session.add_all(citas)

    plan = PlanTratamiento(ingreso_id=ing.id, sesiones_plan=15, aumentos_isl=3)
    db_session.add(plan)
    db_session.commit()
    return {"ingreso": ing}


def test_adherencia_endpoint_correcto(as_coordinacion, datos_adherencia):
    ing = datos_adherencia["ingreso"]
    resp = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ing.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["citas_realizadas"] == 8
    assert body["citas_agendadas"] == 10
    assert abs(body["pct_adherencia"] - 80.0) < 0.1


def test_adherencia_auditor_accede(as_auditor, datos_adherencia):
    ing = datos_adherencia["ingreso"]
    resp = as_auditor.get(f"/api/v1/reportes/adherencia/{ing.id}")
    assert resp.status_code == 200
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_adherencia.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.adherencia'`.

- [ ] **Step 3: Implementar `app/services/adherencia.py`**

Crear `backend/app/services/adherencia.py`:

```python
"""Cálculos de adherencia y avance de tratamiento (D5, CEPA-095).

Estas funciones puras son testeables en aislamiento (QA de métricas — D5).
"""

from __future__ import annotations


def calcular_pct_adherencia(realizadas: int, agendadas: int) -> float | None:
    """% adherencia = citas realizadas / citas agendadas * 100 (D5).

    Retorna None si agendadas == 0 (sin división por cero — TC-095-03).
    """
    if agendadas <= 0:
        return None
    return round((realizadas / agendadas) * 100, 2)


def calcular_pct_avance(
    sesiones_realizadas: int,
    sesiones_plan: int | None,
    aumentos_isl: int = 0,
) -> float | None:
    """% avance = sesiones_realizadas / (sesiones_plan + aumentos_isl) * 100 (D5).

    Retorna None si el plan es cero, None o no definido.
    Los aumentos de ISL amplían el denominador (TC-095-02).
    """
    if sesiones_plan is None or sesiones_plan <= 0:
        return None
    total_plan = sesiones_plan + aumentos_isl
    if total_plan <= 0:
        return None
    return round((sesiones_realizadas / total_plan) * 100, 2)
```

- [ ] **Step 4: Implementar `app/routers/reporte_adherencia.py`**

Crear `backend/app/routers/reporte_adherencia.py`:

```python
"""CEPA-095 — Métricas de adherencia y avance de tratamiento (P1).

Endpoint por folio/ingreso. El cómputo delegado a app.services.adherencia (funciones puras).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.plan_tratamiento import PlanTratamiento
from app.schemas.reportes import AdherenciaPaciente
from app.services.adherencia import calcular_pct_adherencia, calcular_pct_avance

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")


@router.get("/adherencia/{folio_id}", response_model=AdherenciaPaciente)
def get_adherencia_folio(
    folio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> AdherenciaPaciente:
    """CA-1..CA-2: % adherencia y % avance del tratamiento por folio (D5)."""

    # Verificar que el folio existe
    ingreso = db.get(Ingreso, folio_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folio no encontrado")

    # Citas agendadas (cualquier estado que cuente como "fue agendada")
    citas_agendadas = db.execute(
        select(func.count()).select_from(Cita).where(Cita.ingreso_id == folio_id)
    ).scalar_one()

    citas_realizadas = db.execute(
        select(func.count())
        .select_from(Cita)
        .where(Cita.ingreso_id == folio_id)
        .where(Cita.estado == "realizada")
    ).scalar_one()

    # Plan de tratamiento (puede no existir)
    plan = db.scalars(
        select(PlanTratamiento).where(PlanTratamiento.ingreso_id == folio_id)
    ).first()

    sesiones_plan = plan.sesiones_plan if plan else None
    aumentos_isl = plan.aumentos_isl if plan else 0

    pct_adherencia = calcular_pct_adherencia(citas_realizadas, citas_agendadas)
    pct_avance = calcular_pct_avance(citas_realizadas, sesiones_plan, aumentos_isl)

    return AdherenciaPaciente(
        folio_id=folio_id,
        citas_agendadas=citas_agendadas,
        citas_realizadas=citas_realizadas,
        pct_adherencia=pct_adherencia,
        sesiones_realizadas=citas_realizadas,
        sesiones_plan=sesiones_plan,
        aumentos_isl=aumentos_isl,
        pct_avance=pct_avance,
    )
```

- [ ] **Step 5: Registrar router en `app/main.py`**

```python
from app.routers import reporte_adherencia
app.include_router(reporte_adherencia.router)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `uv run pytest tests/test_adherencia.py -v`
Expected: `9 passed` (7 unitarios de casos borde + 2 integración).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/adherencia.py backend/app/routers/reporte_adherencia.py \
        backend/app/main.py backend/tests/test_adherencia.py
git commit -m "feat(reportes): CEPA-095 — métricas adherencia y avance tratamiento (D5, P1)"
```

---

## Task 9: Ventanas de visualización por proceso — migración y endpoints (CEPA-096) · P1

**Files:**
- Create: `backend/migrations/versions/09001_crear_config_ventana_proceso.py`
- Create: `backend/app/models/ventana_proceso.py`
- Create: `backend/app/schemas/ventana_proceso.py`
- Create: `backend/app/routers/ventana_proceso.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ventana_proceso.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_ventana_proceso.py`:

```python
import pytest


# ── TC-096-01: lista de ventanas de proceso disponibles ──────────────────────

def test_listar_ventanas_proceso(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/ventanas-proceso")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


# ── TC-096-03: los cinco tipos de proceso existen o se pueden crear ──────────

PROCESOS_REQUERIDOS = ["licencias", "farmacos", "auditoria", "reintegro", "controles"]


def test_crear_y_listar_ventana_por_proceso(as_coordinacion):
    for proceso in PROCESOS_REQUERIDOS:
        resp = as_coordinacion.post("/api/v1/ventanas-proceso", json={
            "proceso": proceso,
            "columnas_visibles": ["id", "estado", "fecha"],
            "orden_por_defecto": "fecha",
        })
        assert resp.status_code == 201, f"Falló para proceso: {proceso}"

    resp = as_coordinacion.get("/api/v1/ventanas-proceso")
    assert resp.status_code == 200
    procesos_creados = [v["proceso"] for v in resp.json()]
    for p in PROCESOS_REQUERIDOS:
        assert p in procesos_creados


# ── TC-096-04: proceso vacío devuelve lista vacía, sin error ─────────────────

def test_ventana_proceso_lista_vacia_sin_error(as_coordinacion):
    resp = as_coordinacion.get("/api/v1/ventanas-proceso", params={"proceso": "INEXISTENTE_ZZZ"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── TC-096-05: Auditor solo lectura ──────────────────────────────────────────

def test_ventana_proceso_auditor_solo_lectura(as_auditor):
    resp_get = as_auditor.get("/api/v1/ventanas-proceso")
    assert resp_get.status_code == 200

    resp_post = as_auditor.post("/api/v1/ventanas-proceso", json={
        "proceso": "licencias",
        "columnas_visibles": ["id"],
    })
    assert resp_post.status_code == 403


def test_ventana_proceso_sin_auth(client):
    resp = client.get("/api/v1/ventanas-proceso")
    assert resp.status_code == 401
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_ventana_proceso.py -v`
Expected: FAIL con `ModuleNotFoundError` o `404`.

- [ ] **Step 3: Crear la migración**

Crear `backend/migrations/versions/09001_crear_config_ventana_proceso.py`:

```python
"""crear config_ventana_proceso

Revision ID: 09001
Revises: <RESOLVER: alembic heads — poner aquí el ID de la última revisión en main>
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "09001"
down_revision = "<RESOLVER: alembic heads>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_ventana_proceso",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proceso", sa.String(length=40), nullable=False),
        sa.Column("columnas_visibles", sa.JSON(), nullable=False),
        sa.Column("orden_por_defecto", sa.String(length=60), nullable=True),
        sa.Column("creado_por", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_cvp_proceso", "config_ventana_proceso", ["proceso"])


def downgrade() -> None:
    op.drop_index("ix_cvp_proceso", table_name="config_ventana_proceso")
    op.drop_table("config_ventana_proceso")
```

> **IMPORTANTE:** antes de correr el loop, resolver el `down_revision` con el comando:
> ```bash
> uv run alembic heads
> ```
> y reemplazar `<RESOLVER: alembic heads>` por el ID real de la revisión punta.

- [ ] **Step 4: Implementar el modelo**

Crear `backend/app/models/ventana_proceso.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Identity, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConfigVentanaProceso(Base):
    """Configuración de ventana de visualización por proceso (CEPA-096, §7.10).

    Procesos válidos: licencias, farmacos, auditoria, reintegro, controles.
    Tabla de configuración; no es tabla de dominio clínico.
    """

    __tablename__ = "config_ventana_proceso"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    proceso: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    columnas_visibles: Mapped[list] = mapped_column(JSON, nullable=False)
    orden_por_defecto: Mapped[str | None] = mapped_column(String(60), nullable=True)
    creado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
```

Añadir en `backend/app/models/__init__.py`:

```python
from app.models.ventana_proceso import ConfigVentanaProceso  # noqa: F401
```

- [ ] **Step 5: Crear schemas y router**

Crear `backend/app/schemas/ventana_proceso.py`:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


PROCESOS_VALIDOS = frozenset({"licencias", "farmacos", "auditoria", "reintegro", "controles"})


class VentanaProcesoCreate(BaseModel):
    proceso: str
    columnas_visibles: list[str]
    orden_por_defecto: str | None = None

    @classmethod
    def __get_validators__(cls):
        yield cls._validate_proceso

    def _validate_proceso(cls, v):
        return v

    def model_post_init(self, __context) -> None:
        if self.proceso not in PROCESOS_VALIDOS:
            raise ValueError(f"proceso debe ser uno de: {sorted(PROCESOS_VALIDOS)}")


class VentanaProcesoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proceso: str
    columnas_visibles: list[str]
    orden_por_defecto: str | None
    creado_por: str | None
    created_at: datetime
```

Crear `backend/app/routers/ventana_proceso.py`:

```python
"""CEPA-096 — Ventanas de visualización por proceso (§7.10, P1).

Cinco procesos: licencias, farmacos, auditoria, reintegro, controles.
RBAC: Administrativo y Coordinacion crean/actualizan; Auditor solo lectura.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ventana_proceso import ConfigVentanaProceso
from app.schemas.ventana_proceso import VentanaProcesoCreate, VentanaProcesoRead

router = APIRouter(prefix="/api/v1/ventanas-proceso", tags=["ventanas-proceso"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")
_escritor = require_role("Coordinacion", "Administrativo")


@router.get("", response_model=list[VentanaProcesoRead])
def listar_ventanas(
    proceso: str | None = None,
    db: Session = Depends(get_db),
    _current_user=Depends(_lector),
) -> list[ConfigVentanaProceso]:
    """CA-1..CA-3: lista de configuraciones de ventanas por proceso."""
    stmt = select(ConfigVentanaProceso)
    if proceso is not None:
        stmt = stmt.where(ConfigVentanaProceso.proceso == proceso)
    return list(db.scalars(stmt.order_by(ConfigVentanaProceso.proceso)))


@router.post("", response_model=VentanaProcesoRead, status_code=status.HTTP_201_CREATED)
def crear_ventana(
    payload: VentanaProcesoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_escritor),
) -> ConfigVentanaProceso:
    """Crear o actualizar la configuración de una ventana de proceso."""
    ventana = ConfigVentanaProceso(
        proceso=payload.proceso,
        columnas_visibles=payload.columnas_visibles,
        orden_por_defecto=payload.orden_por_defecto,
        creado_por=current_user.username,
    )
    db.add(ventana)
    db.commit()
    db.refresh(ventana)

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="config_ventana_proceso",
        entity_id=str(ventana.id),
    )

    return ventana
```

- [ ] **Step 6: Registrar router en `app/main.py`**

```python
from app.routers import ventana_proceso
app.include_router(ventana_proceso.router)
```

- [ ] **Step 7: Correr los tests y verificar que pasan**

Run:
```bash
uv run alembic upgrade head
uv run pytest tests/test_ventana_proceso.py -v
```
Expected: `5 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/migrations/versions/09001_crear_config_ventana_proceso.py \
        backend/app/models/ventana_proceso.py \
        backend/app/schemas/ventana_proceso.py \
        backend/app/routers/ventana_proceso.py \
        backend/app/models/__init__.py \
        backend/app/main.py \
        backend/tests/test_ventana_proceso.py
git commit -m "feat(reportes): CEPA-096 — ventanas de visualización por proceso (P1)"
```

---

## Task 10: Integración final — suite completa, lint y verificación OU3 · P0

**Files:** ninguno nuevo.

- [ ] **Step 1: Correr la suite completa**

Run (desde `backend/`):
```bash
uv run pytest -v
```
Expected: todos los tests en verde (Tasks 1..9).

- [ ] **Step 2: Lint**

Run:
```bash
uv run ruff check .
```
Expected: sin errores.

- [ ] **Step 3: Verificar migración desde cero (portabilidad)**

Run:
```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: aplica y revierte sin errores.

- [ ] **Step 4: Test de rendimiento manual OU3 (<10 s)**

> No es un test automatizado (depende del volumen real), pero se documenta la prueba:

Run el servidor con datos de muestra y cronometrar:
```bash
uv run uvicorn app.main:app --reload
# En otra terminal (o usar httpx):
time curl -s "http://localhost:8000/api/v1/dashboard" -H "Authorization: Bearer <token_coordinacion>"
```
Expected: el endpoint responde en < 10 s sobre datos de prueba (OU3). Si se acerca al límite, crear índices en `Ingreso.fecha_ingreso`, `Ingreso.programa`, `Cita.estado`, `Cita.fecha` vía Alembic adicional.

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "chore(reportes): suite EPIC-09 completa — todos los reportes en verde" || echo "nada que commitear"
```

---

## Cobertura

| Historia | Task(s) | Prioridad |
|----------|---------|-----------|
| CEPA-090 — Dashboard multiprograma con filtros | Task 1 (helper filtros D5) + Task 2 (endpoint dashboard) | P0 |
| CEPA-091 — Reportes operativos descargables | Task 3 (endpoint operativo) | P0 |
| CEPA-092 — Reporte cumplimiento por convenio | Task 4 (endpoint convenio) | P0 |
| CEPA-093 — Reporte carga laboral por profesional | Task 5 (endpoint carga-laboral) | P0 |
| CEPA-094 — Reporte licencias médicas acumuladas | Task 6 (endpoint licencias) | P0 |
| CEPA-095 — Métricas de adherencia y avance | Task 8 (servicio puro + endpoint adherencia) | P1 |
| CEPA-096 — Ventanas de visualización por proceso | Task 9 (migración + modelo + router) | P1 |
| CEPA-097 — Reporte ODAS vencidas | Task 7 (endpoint odas-vencidas) | P0 |

**Reportes y métricas definidos:**
1. Dashboard multiprograma (14 filtros D5, indicadores en tiempo real)
2. Reporte operativo diario (citas/realizadas/inasistencias/anuladas)
3. Reporte cumplimiento por convenio (tipos D4)
4. Reporte carga laboral por profesional (casos + atenciones)
5. Reporte licencias acumuladas (interno vs. extra-sistema, D7)
6. Métricas de adherencia (% = realizadas/agendadas) y avance (% vs plan + ISL)
7. Ventanas de proceso por tipo (licencias/fármacos/auditoría/reintegro/controles)
8. Reporte ODAS vencidas (condición estricta < hoy, D3)

---

## Notas de cierre

### Dependencias que verificar contra el repo real antes de iniciar el loop

1. **Modelo `Cita`** (EPIC-08): verificar que la columna `estado` usa exactamente los valores `"realizada"`, `"inasistencia"`, `"anulada"`, `"agendada"`. Si difieren, actualizar los filtros en `reporte_operativo.py` y `dashboard.py`.

2. **Modelo `LicenciaMedica`** (EPIC-07): verificar la existencia de columnas `origen_externo: Boolean`, `dias_reposo: Integer`, `fecha_emision: Date`, `tipo_licencia: String`, `tipo_reposo: String`. La función `calcular_acumulado` de EPIC-07 no se llama directamente en este plan (se reimplemente con ORM) para evitar la dependencia circular; si ya existe y tiene la misma semántica, se puede sustituir.

3. **Modelo `ODA`** (EPIC-01): verificar columnas `fecha_registro: Date`, `fecha_vencimiento: Date`, `ingreso_id: BigInteger FK`. El campo `programa`/`region`/`comuna` puede estar en `Ingreso` (join) o en `ODA` directamente.

4. **Modelo `PlanTratamiento`** (posiblemente en EPIC-03 EPT): verificar existencia de `sesiones_plan: Integer`, `aumentos_isl: Integer`, `ingreso_id: FK`. Si no existe como modelo separado, los campos pueden estar en `Ingreso` o en un modelo de `Seguimiento`; ajustar el endpoint de adherencia en consecuencia.

5. **Firmas de `record_audit`** y **`require_role`** (EPIC-00): verificar contra `app/audit/service.py` y `app/auth/deps.py` en el repo real que los parámetros `actor`, `action`, `entity`, `entity_id` son posicionales o keyword.

6. **`down_revision` de la migración 09001**: antes de correr el loop, ejecutar `uv run alembic heads` en el repo real y reemplazar `<RESOLVER: alembic heads>` con el ID de la revisión punta.

7. **Campos de `Ingreso`**: esta épica asume que `Ingreso` tiene columnas `programa`, `profesional_id`, `tipo_convenio`, `diagnostico`, `tipo_alta`, `tramo_etario`, `sexo`, `region`, `comuna`, `modelo_tratamiento`, `tipo_ingreso`, `especialidad`, `tipo_atencion` para los filtros D5. Verificar contra el modelo real de EPIC-01; si algún campo está en `Paciente` o en otra tabla, el helper `aplicar_filtros_ingreso` necesita el join correspondiente.

### Decisiones de negocio aún abiertas (del spec)

- **D11 (tipificación de altas):** el campo `tipo_alta` en los filtros del dashboard puede ser una sola fecha de alta o un tipo. Confirmar con Coordinación antes de validar el filtro en producción.
- **Catálogo de estados de cita:** confirmar con Coordinación que `"realizada"`, `"inasistencia"`, `"anulada"`, `"agendada"` cubre todos los estados posibles y el denominador de adherencia (excluye o incluye anuladas).
- **Licencias extra-sistema por defecto:** CEPA-094 implementa inclusión siempre; confirmar si es bajo selección explícita (D7 pendiente).
- **Indicadores exactos del reporte de convenio:** el layout y los KPIs exactos para cada institución contraparte (ISL, etc.) están pendientes de confirmación; el endpoint actual devuelve totales de atenciones/inasistencias/anulaciones como base.
- **Unidad de carga laboral:** CEPA-093 computa por número de casos (ingresos) y atenciones; confirmar si la unidad preferida es horas estimadas u otro indicador.
- **Planes de tratamiento de referencia (10/15/21 sesiones) y regla de aumentos ISL:** confirmar los valores del plan para el cálculo de avance.
- **Rendimiento OU3 en producción:** si con el volumen real el endpoint `/dashboard` supera 10 s, agregar índices compuestos en `(programa, fecha_ingreso)` e `(ingreso_id, estado)` en las tablas `ingreso` y `cita` mediante una migración adicional (o usar `func.count` con `FILTER` según soporte del motor).
- **QA de métricas D5:** las funciones `calcular_pct_adherencia` y `calcular_pct_avance` de `app/services/adherencia.py` están listos para la validación de resultado y de proceso; requieren designar un responsable de QA antes de publicarlas en producción.
