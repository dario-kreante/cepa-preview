# Worklog — Ejecución de planes Sistema CEPA (2026-06-11)

Traza de decisiones, dudas y desvíos durante la ejecución autónoma de los planes
(`docs/superpowers/plans/`). Metodología: superpowers:subagent-driven-development +
TDD. Implementadores con modelos económicos (haiku/sonnet); revisiones de spec y
calidad con modelos capaces (Fable/Opus).

## Entorno

- **Postgres:** no había server local (solo `libpq`). Docker Desktop estaba instalado pero
  apagado → se arrancó y se levantó contenedor `cepa-pg` (postgres:16, usuario/clave `cepa`,
  bases `cepa` y `cepa_test`, puerto 5432). **Decisión:** contenedor en vez de
  `brew install postgresql@16` para no instalar servicios permanentes en la máquina del usuario.
- **Rama:** trabajo en worktree `claude/kind-black-2f7844`.
- **Data sensible:** el dominio es clínico/psicosocial (Universidad de Talca). Regla operativa:
  ningún dato real de pacientes en fixtures/tests/commits; solo datos sintéticos obvios
  (RUTs de ejemplo válidos pero ficticios, nombres genéricos).

## Decisiones de proceso

- **D-W1:** Los planes traen código literal y pasos bite-sized → las tasks mecánicas se agrupan
  en lotes por subagente implementador (modelo económico) para no quemar presupuesto en
  dispatches triviales; cada lote recibe revisión de spec + calidad con modelo capaz.
- **D-W2:** "Port al stack de las specs" = crear `backend/` (FastAPI+SQLAlchemy portable) según
  el plan de Fundación. El frontend actual (React CDN sin build) se mantiene como preview y se
  valida visualmente con QA preview por épica.
- **D-W3:** Validación visual por épica: levantar `uvicorn` + abrir el preview (index.html) y
  verificar contra el spec de la épica con preview tools antes de cerrar cada plan.

## Oleada 0 — Fundación backend ✅ (2026-06-11)

- **Ejecución:** Tasks 1–7 (implementador haiku) + Tasks 8–9 (implementador haiku) + Task 10
  (verificación integral por el orquestador). Revisión spec+calidad de Tasks 1–7 con Fable:
  **APROBADA** — match byte a byte con el plan salvo 1 desviación legítima.
- **Desviación F-1 (bug del plan):** en `tests/test_audit_log_model.py` el plan escribía
  `default.arg()`; SQLAlchemy 2.0.50 envuelve los callables sin argumentos y exige `ctx`
  → se usa `default.arg(None)`. Verificado empíricamente por el revisor; preserva la intención.
- **Resultado:** 12 tests verdes contra Postgres real, `ruff` limpio, ciclo
  `alembic upgrade head`/`downgrade base` OK, humo manual del servidor OK
  (`/health`, POST/GET `/api/v1/audit-log` con persistencia real en BD `cepa`).
- **Incidente de verificación (no es bug):** el primer humo falló con `UndefinedTable` porque
  (a) la suite de tests deja `cepa_test` en `downgrade base` al terminar (by design), y
  (b) quedó un uvicorn zombi ocupando el puerto 8123 apuntando a `cepa_test`. Resuelto
  matando el proceso y corriendo contra la BD `cepa` migrada.
- **Notas menores del revisor (sin acción, fuera de alcance del plan):** DeprecationWarning de
  Alembic por `path_separator` ausente en `alembic.ini`; deprecation de Starlette/httpx en
  TestClient.
- Commits: `0ea29fb…ba39367` (9 commits, mensajes exactos del plan).
