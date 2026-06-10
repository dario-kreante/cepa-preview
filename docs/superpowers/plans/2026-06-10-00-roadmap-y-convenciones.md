# Roadmap maestro y convenciones — Planes de implementación Sistema CEPA

> **Propósito:** ordenar la construcción del backend por dependencias y fijar las **convenciones
> compartidas** que TODO plan de épica debe seguir. Está pensado para ejecutarse con loops agénticos
> (subagent-driven-development / executing-plans), un plan a la vez.

> ⚠️ **Madurez de los planes:** los planes de épica se generaron antes de existir el código. Son
> **borradores v1**: sólidos en estructura y cobertura de las historias, pero el código exacto debe
> revisarse contra el repo real justo antes de cada loop (especialmente firmas que dependan de la
> Fundación y de EPIC-00). Tratar cada plan como punto de partida, no como verdad inmutable.

## Orden de dependencias (oleadas)

```
Oleada 0  ── Fundación backend (FastAPI + SQLAlchemy portable)      [ya planificada]
                 │
Oleada 1  ── EPIC-00  Plataforma, Auth (JWT) y RBAC + Log auditoría  (bloquea a todos)
                 │
Oleada 2  ── EPIC-01  Ingresos y Pacientes  (raíz del dominio: folio/paciente)
                 │
Oleada 3  ── (en paralelo, todos cuelgan del ingreso/folio)
             EPIC-02 Fármacos · EPIC-03 EPT · EPIC-04 Reintegro ·
             EPIC-06 Controles · EPIC-07 Licencias
                 │
Oleada 4  ── (transversales, dependen de que exista dominio)
             EPIC-05 Auditoría (vista consolidada) · EPIC-08 Agendamiento ·
             EPIC-09 Reportería/Dashboard · EPIC-10 Alertas · EPIC-11 Config/Calidad ·
             EPIC-12 API de Integración
```

**Regla de ejecución de loops:** completar y mergear una oleada antes de empezar la siguiente.
Dentro de la Oleada 3, las épicas pueden correr en loops paralelos (tocan tablas distintas), pero
cada una asume Fundación + EPIC-00 + EPIC-01 ya en `main`.

## Inventario de planes

| Plan | Épica | Oleada | Depende de | Archivo |
|------|-------|--------|-----------|---------|
| Fundación | — | 0 | — | `2026-06-10-backend-foundation-fastapi-sqlalchemy.md` |
| EPIC-00 | Auth/RBAC/Audit | 1 | Fundación | `2026-06-10-epic-00-plataforma-auth-rbac.md` |
| EPIC-01 | Ingresos | 2 | EPIC-00 | `2026-06-10-epic-01-ingresos.md` |
| EPIC-02 | Fármacos | 3 | EPIC-01 | `2026-06-10-epic-02-farmacos.md` |
| EPIC-03 | EPT | 3 | EPIC-01 | `2026-06-10-epic-03-ept.md` |
| EPIC-04 | Reintegro | 3 | EPIC-01 | `2026-06-10-epic-04-reintegro.md` |
| EPIC-06 | Controles | 3 | EPIC-01 | `2026-06-10-epic-06-controles.md` |
| EPIC-07 | Licencias | 3 | EPIC-01 | `2026-06-10-epic-07-licencias.md` |
| EPIC-05 | Auditoría | 4 | EPIC-01..07 | `2026-06-10-epic-05-auditoria.md` |
| EPIC-08 | Agendamiento | 4 | EPIC-01,06 | `2026-06-10-epic-08-agendamiento.md` |
| EPIC-09 | Reportería | 4 | EPIC-01..07 | `2026-06-10-epic-09-reporteria-dashboard.md` |
| EPIC-10 | Alertas | 4 | EPIC-01,03,07 | `2026-06-10-epic-10-alertas-notificaciones.md` |
| EPIC-11 | Config/Calidad | 4 | EPIC-01 | `2026-06-10-epic-11-config-calidad.md` |
| EPIC-12 | API Integración | 4 | EPIC-01,07 | `2026-06-10-epic-12-api.md` |

---

## Convenciones compartidas (OBLIGATORIAS en todo plan)

### Estructura del proyecto (de la Fundación)
```
backend/
  app/
    config.py            # Settings (DATABASE_URL)
    db/base.py           # Base (DeclarativeBase)
    db/session.py        # engine, SessionLocal, get_db   (único módulo que conoce el motor)
    models/<modulo>.py   # modelos SQLAlchemy
    schemas/<modulo>.py  # Pydantic v2
    routers/<modulo>.py  # APIRouter, prefijo /api/v1/...
    main.py              # incluye routers
  migrations/versions/   # Alembic (una revisión por historia que cambia el esquema)
  tests/                 # pytest + conftest (fixtures: client, db_session, auth)
```
- Gestor: **uv**. Comandos `uv run pytest|alembic|uvicorn …` ejecutados **desde `backend/`**.

### Reglas de portabilidad de BD (D15) — innegociables en cada modelo/migración
- Solo tipos genéricos de SQLAlchemy (`String`, `Numeric`, `DateTime(timezone=True)`, `Boolean`,
  `JSON`, `BigInteger`, `Integer`, `Date`, `Text`). Nunca tipos/SQL específicos de un motor.
- PK subrogada con `Identity(always=False)` sobre `BigInteger`.
- Identificadores de tabla/columna en **minúscula y ≤30 caracteres**.
- Fechas/tiempos en **UTC**, `DateTime(timezone=True)`; helper `_utcnow()` (de la Fundación).
- Sin `ON CONFLICT`/`MERGE`/`ROWNUM`; upserts y paginación en capa de aplicación / ORM.
- Una migración Alembic por historia que cree/altere tablas; debe pasar el **job Oracle gated** del CI.

### Auth y RBAC (definidos por EPIC-00 — los demás planes los ASUMEN, no los redefinen)
EPIC-00 expone estas dependencias en `app/auth/deps.py`; los planes de dominio las importan:

```python
from app.auth.deps import get_current_user, require_role
# get_current_user -> CurrentUser  (id, username, role)
# require_role(*roles: str) -> dependencia que exige uno de los roles dados
```
- Roles válidos (v4 D1): `"Coordinacion"`, `"Administrativo"`, `"Auditor"`. No existe "Clinico".
- **Auditor es solo lectura:** endpoints de escritura usan `Depends(require_role("Administrativo", "Coordinacion"))`;
  endpoints de lectura permiten además `"Auditor"`.
- Gestión de usuarios/roles: solo `"Coordinacion"`.
- Endpoints protegidos requieren `Depends(get_current_user)`; sin token válido → `401`.
- Rol sin permiso → `403`.

### Auditoría (de EPIC-00 / CEPA-003) — los planes de dominio la INVOCAN
Toda operación de escritura registra traza con el helper de EPIC-00:

```python
from app.audit.service import record_audit
record_audit(db, actor=current_user.username, action="CREATE", entity="ingreso", entity_id=str(obj.id))
```
- `action` ∈ {`CREATE`,`UPDATE`,`DELETE`}. La traza es append-only.

### Convenciones de API
- Prefijo de versión: `/api/v1/<recurso>`; recursos en kebab-case plural (p. ej. `/api/v1/licencias`).
- Request/response JSON; errores con códigos HTTP estándar (`400/401/403/404/409/422/429`).
- Schemas Pydantic v2 (`model_config = ConfigDict(from_attributes=True)` en los `*Read`).
- RUT: validar dígito verificador (módulo 11) en un util compartido `app/util/rut.py` (lo crea EPIC-01;
  los demás lo importan).

### Convenciones de tests (conftest extendido por EPIC-00)
Fixtures disponibles para los planes de dominio (las define/extiende EPIC-00):
- `client` — `TestClient` con `get_db` sobreescrito a la sesión de test.
- `db_session` — sesión con rollback por test (`join_transaction_mode="create_savepoint"`).
- `as_admin`, `as_coordinacion`, `as_auditor` — clientes autenticados con cada rol (headers JWT puestos).
- Tests **contra Postgres real** (nunca SQLite). Cada historia con criterios de aceptación Gherkin se
  traduce a tests; cada Test Case (TC-…) del spec debe tener al menos un test correspondiente.

### Formato de cada plan (writing-plans)
- Header obligatorio con `Goal / Architecture / Tech Stack` y la línea "For agentic workers".
- **Una historia (CEPA-0XX) ≈ una o más Tasks.** Cada Task con `Files:` (rutas exactas) y pasos
  TDD bite-sized (escribir test que falla → correr y ver fallar → implementar mínimo → correr y ver
  pasar → commit). **Código completo, sin placeholders.**
- Commits por historia/Task con Conventional Commits.
- Mapear explícitamente Tasks ↔ historias del spec; al final, sección "Cobertura" que liste cada
  CEPA-0XX y la(s) Task(s) que la implementan.
- Idioma español, tono y estructura como los specs de `docs/issues/`.

### Caveats que cada plan debe declarar en sus "Notas de cierre"
- Qué firmas dependen de EPIC-00/Fundación y deben verificarse contra el código real antes del loop.
- Decisiones de negocio aún abiertas del spec (p. ej. tipificación de altas D11, consentimiento D9).
