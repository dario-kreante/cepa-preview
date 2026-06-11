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

## Oleada 1 — EPIC-00 Auth/RBAC/Auditoría

Ejecución en 4 lotes (implementadores haiku, revisión Fable por lote):

- **Lote A (Tasks 1–4)** ✅ deps pyjwt/pwdlib, config auth, hashing argon2, JWT, modelo
  usuario + migración 0002. Revisión Fable: APROBADO, match exacto con el plan; migración
  0002 verificada en BD scratch. Nota menor del revisor: `jwt_secret` con default de
  desarrollo (el plan lo acepta; cambiar en prod).
- **Lote B (Tasks 5–8)** ✅ audit_log extendido (rol/valores) + trigger de inmutabilidad
  portable (migración 0003, dialecto PG/Oracle), `record_audit` sin commit, deps RBAC
  (401/403), fixtures as_admin/as_coordinacion/as_auditor. Revisión Fable: APROBADO;
  verificó empíricamente que UPDATE/DELETE sobre audit_log son rechazados por el trigger.
  Menores heredados del plan: imports sin uso en test_fixtures_auth.py, espacio extra en
  el mensaje del trigger.
- **Lote C (Tasks 9–12 + 13 adelantada)** — el implementador ejecutó también la Task 13
  (reescritura del router audit-log) y un commit extra `72f40d7` (limpieza de imports) no
  previsto en el plan. **Decisión:** se aceptó condicionado a revisión Fable estricta del
  rango completo (en curso al escribir esta entrada).
- **Task 14** ✅ seed idempotente de usuario Coordinación (`app/scripts/seed_admin.py`),
  72 tests verdes.
- **Lote C — revisión Fable: APROBADO.** Match literal con el plan en Tasks 9–13; el borrado
  de `test_audit_log_api.py` SÍ estaba prescrito por la Task 13 (la adelantada era válida).
  El commit extra `72f40d7` solo elimina imports genuinamente muertos que el plan incluyó
  por error — aceptado. Menores señalados (heredados del plan, sin acción): `valor_nuevo`
  construido con f-string en `routers/usuarios.py` (JSON malformado si el username tuviera
  comillas); falta test para "access token usado como refresh" (verificado manualmente: 401).
- **Task 15** ✅ ejecutada por el orquestador: 72 tests verdes, ruff limpio, ciclo
  `downgrade base`/`upgrade head` OK (0001→0003), humo manual completo contra BD `cepa`
  (seed root → login → POST /usuarios 201 → audit-log lista LOGIN/CREATE), OpenAPI expone
  auth/usuarios/audit-log y `/docs` responde 200.

### Dudas/decisiones de negocio que el plan deja abiertas (heredadas, para review humano)
- Valores definitivos de N intentos/bloqueo/vigencias de tokens (hoy: 5 / 15 min / 15 min
  access / 7 días refresh) — confirmar con Coordinación/TI UTalca.
- Auditoría de lecturas sensibles (action="READ") — decisión transversal pendiente.
- TLS se delega al proxy (TC-001-06) — documentado en runbook, no en FastAPI.
- Política de retención del log — fuera de alcance de EPIC-00.

## Oleada 2 — EPIC-01 Ingresos y Pacientes ✅ (2026-06-11)

Ejecución en 4 lotes (haiku) + Task 12 por el orquestador; 4 revisiones Fable.

- **Lote A (Tasks 1–4)** APROBADO. Desviaciones validadas: (1) los RUT de ejemplo del plan
  eran inválidos por módulo 11 → sustituidos por sintéticos válidos (el revisor recomputó los
  DV a mano); (2) se difirieron las relationships a modelos futuros en `Ingreso` (el plan las
  traía con forward refs rotas) → instrucción obligatoria de re-agregarlas en Tasks 8/10/11
  (cumplida); (3) revisiones 0010/0011 correctas (el plan lo dejaba parametrizado).
- **Lote B (Tasks 5–7)** APROBADO CON CORRECCIONES (aplicadas en `990f076`):
  - **Decisión de diseño importante:** se eliminó el unique global de `ingreso.folio`
    (migración `0011b`) porque el spec exige reingresos que MANTIENEN el folio
    (CEPA-011 RN-2/RN-3, D2); el plan tenía una contradicción interna y el revisor falló a
    favor del spec. Unicidad por servicio.
  - Corrección exigida: el reingreso debe ser EXPLÍCITO (`es_reingreso=True`) — el
    implementador lo había relajado. Restaurado al literal del plan.
  - `IngresoRead` retipado con enums; limpieza de lint.
- **Lote C (Tasks 8–9)** APROBADO con 1 corrección (revert del future-import en rut.py que el
  implementador re-introdujo con justificación falsa — churn repetido, revertido en `6cc8c79`).
- **Lote D (Tasks 10–11)** APROBADO. El implementador olvidó commitear las relaciones
  odas/consentimiento en `ingreso.py` (recuperado por el orquestador en `6cc8c79`). El RUT
  "10.000.05K" es checksum-válido aunque esté mal formateado (el normalizador lo acepta).
  Nota de proceso del revisor: el commit `0e4a2a1` no es importable aislado (bisect).
- **Task 12** ✅ 152 tests verdes, ruff limpio, `downgrade base → upgrade head` OK,
  sin SQL específico de motor (grep ON CONFLICT/MERGE/ROWNUM limpio).
- **QA funcional end-to-end (BD cepa):** login → ingreso 201 (folio F-2026-0001) → búsqueda →
  vista-360 → seguimiento + validación de plazo → ODA (alerta por vencer funciona con
  ventana 5 días) → iniciar-tratamiento bloqueado 409 sin consentimiento → firmado → 200 →
  cierre con alta terapéutica 200.
- **Deuda conocida:** la BD dev `cepa` migrada antes de `0011b` tiene drift en downgrade
  (uq ya existente) — no afecta upgrade ni producción desde cero.
- Decisiones de negocio abiertas heredadas del plan: D11 (una fecha_alta), D9 (evidencia de
  consentimiento como string), D2 (confirmar folio en reingresos), ventana ODAS 5 días
  (parametrizar en EPIC-11), catálogos regiones/diagnósticos como string libre (D5).
