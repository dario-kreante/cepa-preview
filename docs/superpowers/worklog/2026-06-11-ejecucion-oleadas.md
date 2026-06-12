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

## Oleada 3 — Épicas de dominio (2026-06-11)

**Cambio de proceso (D-W4):** a partir de aquí, un implementador sonnet por épica completa
(en vez de lotes haiku) + 1 revisión Fable por épica — mejor relación costo/fiabilidad con
planes literales largos. Épicas secuenciales (main.py y cadena Alembic compartidos), con
revisión de la épica N en paralelo a la implementación de la N+1 (BDs scratch separadas).

- **EPIC-02 Fármacos** ✅ APROBADA sin correcciones (207 tests acumulados, +55).
  Desviaciones validadas: schemas `*Body` sin id de path (el plan era internamente
  inconsistente — patrón aprobado y reutilizado en épicas siguientes); 7 RUTs corregidos
  (revisor recomputó los 8 módulo-11); migraciones 0020–0024. Menor pendiente de spec:
  semántica de `vigente` en indicaciones (el plan nunca lo apaga) — revisar con negocio.
- **EPIC-03 EPT** ✅ APROBADA (251, +44). email-validator agregado (sancionado por el plan);
  `ContactoEptPayload`; fixture movida a conftest. Única corrección: borrar
  `conftest_ept.py` muerto (hecho en `e50b3e1`). TC-032-02 (emisión de alertas) delegada a
  EPIC-10 por el propio spec.
- **EPIC-04 Reintegro** ✅ APROBADA (308, +57) con 2 brechas de spec heredadas del plan,
  corregidas en `1369f58` (354 tests): RN-2 cierre valida también vs `fecha_caso`; RN-4
  `verifica_medidas=True` exige `fecha_verificacion`; `TipoAlta` consolidado como re-export
  (riesgo de divergencia D11). Menor declarado: PATCH /cierre con semántica replace
  (heredado del plan; revisar si se quiere exclude_unset).
- **EPIC-06 Controles** ✅ APROBADA sin correcciones (349, +41). El plan mencionaba
  migraciones 0061/0062 que ninguna Task creaba — una sola 0060 con todas las columnas es
  la lectura correcta (validado por revisor columna a columna). TC-060-03 delegado a
  EPIC-01, TC-061-02 a EPIC-10 (sancionado por spec).
- **EPIC-07 Licencias** ✅ APROBADA sin correcciones (407 tests, +53). El revisor confirmó que
  el TipoLicencia restringido {1,5,6} en `enums_licencia.py` es lo que dictan plan Y spec
  (RN-3); el de controles modela digitación manual con extra_sistema — NO consolidar.
  Fechas y 6 RUTs del plan corregidos (todos los DV originales eran inválidos).
  Menores para backlog: RN-5 advertencia de días no bloqueante (decisión del plan, confirmar
  con Coordinación); ISL de extra-sistema queda "pendiente" en vez de "no aplica".
- **QA funcional Oleada 3 (BD cepa, usuario root + ana/Administrativo):** registro
  farmacológico 201 + esquema (frecuencia c/24h) 201, caso EPT 201 (nota: writer EPT es solo
  rol Administrativo según plan), caso reintegro 201, control médico 201, licencia 201 con
  acumulado correcto (15 días vigentes, sin solapamiento). Todas las rutas reales validadas
  vía OpenAPI.
- **Pendiente cross-épica detectado por revisores:** poblar las ranuras de `vista_360`
  (farmacos/licencias/controles/reintegro siguen vacías — ningún plan de oleada 3 lo
  prescribió; evaluar al cerrar EPIC-09 Reportería).

## Oleada 4 — Transversales (2026-06-11/12)

Mismo patrón D-W4 (sonnet por épica + revisión Fable). Dos interrupciones por límite de
sesión (EPIC-11 y EPIC-12 a mitad de trabajo) — el trabajo huérfano se recuperó, se
verificó y se committeó con traza explícita.

- **EPIC-05 Auditoría** ⚠️→✅ (487→536 tests tras fixes). Plan anterior al código: el
  implementador adaptó nombres de campos al modelo real (sancionado por el roadmap). La
  revisión encontró 1 CRÍTICO — las trazas `record_audit(READ)` nunca se persistían (sin
  `db.commit()` en los GET) — más filtros diagnostico/profesional ignorados, deducción
  errónea de reintegro parcial/total (debía usar el enum EstadoReintegro), fecha_denuncia
  mapeada a fecha_ingreso en vez de fecha_diep_diat, y CSV sin sanitizar (formula
  injection). Todo corregido en `64fbf27`. **Decisión:** contadores de sesiones → `None`
  (el dato no existe en el modelo; 0 afirmaría dato real ante fiscalización).
- **EPIC-08 Agendamiento** ⚠️→✅ (504→542). Aprobada con fixes: citas excluidas por reposo
  eran confirmables (RN-1), candidatos desde controles vencidos obsoletos (ahora último
  control por ingreso + proximo_agendado=False), ventana de recetas sin tope + fecha_envio
  como proxy de "gestionada" (RN-6), N+1 de reposos → batch. El batch usó `ANY(:pids)`
  (Postgres-only) — corregido por el orquestador a IN expandible (`65d73ce`, D15).
  **Limitación documentada:** pool único de candidatos (sin scoping por profesional;
  control_medico no tiene profesional_id) — resolver vía medico_tratante antes de uso
  multi-profesional.
- **EPIC-09 Reportería** ❌→⚠️→✅ (588→658). **Rechazo inicial:** la épica reportaba sobre
  tablas huérfanas que nadie escribía (`cita`, `plan_tratamiento`) y 9 columnas de
  dimensión en `ingreso` sin poblar (3 duplicando a `paciente`). **Decisiones DD-1..6 del
  orquestador:** materializar `Cita` al confirmar propuesta (EPIC-08) + PATCH de estado;
  endpoint de escritura para plan de tratamiento; migración correctiva 11000 eliminando
  sexo/region/comuna/tramo_etario de ingreso (JOIN a Paciente + tramo derivado por CASE);
  dimensiones pobladas vía IngresoCreate; período solo sobre tablas de hechos. Re-revisión
  aprobó con 2 fixes que aplicó el orquestador (`55208cc`): ingreso ACTIVO al materializar
  cita; fecha_desde/hasta del dashboard dejaron de ser no-ops.
- **EPIC-10 Alertas** ❌→✅ (640→682). **Rechazo inicial demoledor:** los 5 constructores de
  hitos en SQL crudo referenciaban tablas/columnas inexistentes (except anchos lo
  ocultaban → el job siempre generaba 0 alertas pareciendo sano), trazas no persistidas,
  destinatario de correo imposible (usuario sin email). **Rework (DD-A..F):** constructores
  ORM reales por los 6 tipos + test de integración por tipo, auditoría antes del commit,
  migración 11001 (usuario.email; usuario_id nullable — destinatario = profesional_id del
  ingreso, PA documentada), idempotencia por (caso, tipo, plazo_objetivo) RN-4,
  transiciones validadas, SMTP inerte sin marcar email_enviado. Re-revisión: APROBADA.
  Menores M1/M2 corregidos después (último control por ingreso; caso_tipo control_medico).
- **EPIC-11 Config/Calidad** ⚠️→✅ (721→770). Implementada por agente interrumpido (sin
  reporte); revisión exhaustiva post-mortem: APROBADA con 4 importantes, corregidos en
  `1f609fb`: auditar publicaciones bloqueadas (RN-5), validación RN-4 en confirm del PDF
  (obligatorios + dominios), endurecimiento PDF (límite 10MB, 50 páginas, pages-loop dentro
  del try), y tests reales de la heurística de mapeo + DI del parser.
  **Brechas de spec registradas (heredadas del plan):** TC-111-04/05 (validación de captura
  operacional contra el formulario publicado) sin endpoint de captura.
- **EPIC-12 API Integración** ⚠️→✅ (760→774). Tasks 1-4 del agente interrumpido + Task 5
  recuperada del working tree (verificada completa contra el plan por el revisor) + Task 6
  (IMED, agente fresco). Revisión: APROBADA con 2 importantes de efectividad de tests,
  corregidos en `2ab73a8`: la guardia D12 parcheaba el target equivocado (vacua — ahora
  parchea el binding del servicio y un pull positivo prueba que el mock entra al flujo) y
  el test de rate-limit no ejercitaba la app real (ahora 429 sobre app.main.app).
  D12 verificado: cliente SALUTEM read-only stub, cero llamadas de red, sin credenciales.
- **Fix transversal:** ODAs vencidas usaba fecha UTC (adelantaba el día desde las ~20h de
  Chile); ahora fecha operacional local (`296f2bf`).

### Verificación final integral (2026-06-12)
- **774 tests verdes**, ruff limpio, `alembic upgrade head` + `downgrade base` desde BD
  **vacía** OK (head 1220, cadena lineal 0001→…→1220).
- Humo Oleada 4 (BD cepa): v2/health, dashboard, auditoría consolidada, ODAs vencidas,
  panel de alertas, tareas → 200; **ejecutar-job generó 1 alerta real** sobre la ODA del
  humo de Oleada 3 (motor end-to-end probado con datos reales del flujo).

### Issues pendientes para backlog (detectados por revisores, fuera de alcance de los planes)
1. Export CSV/PDF en reportes 091/092/093/094/097 (precedente: StreamingResponse de EPIC-05).
2. Estadísticas de fármacos (CEPA-095 CA-3) — ausente también del plan.
3. Endpoint de captura operacional con validación contra formulario publicado (TC-111-04/05).
4. Scoping por profesional en agendamiento (mapeo medico_tratante).
5. Vistas consolidadas CEPA-096 completas (hoy: solo tabla de configuración de ventanas).
6. Poblar ranuras vista-360 (farmacos/licencias/controles/reintegro).
7. Política global de auditoría de lecturas sensibles (hoy: EPIC-05/09 auditan generación
   de reportes; el resto de GETs no).
8. Festivos chilenos en cálculos de días hábiles (alertas/agendamiento).
9. Drift de la BD dev `cepa` en downgrade (migrada antes de 0011b) — solo afecta esa BD.
10. TipoLicencia ISL "no aplica" para licencias extra-sistema (CEPA-073 RN-4).

## Post-PR — Fix de portabilidad Oracle (job gated, 2026-06-12)

El job **Oracle gated** del CI (allowed-to-fail, existe precisamente para atrapar fugas de
portabilidad D15) falló en `alembic upgrade head` con **ORA-01408: such column list already
indexed** en `CREATE INDEX ix_paciente_rut`. Postgres tolera un índice explícito sobre una
columna que ya tiene UNIQUE constraint; Oracle no (el unique ya crea un índice implícito).

**Alcance (7 tablas con el mismo patrón redundante):** paciente.rut, ingreso.folio,
reg_farmacologico.ingreso_id, proceso_ept.caso_ept_id, plazo_ept.caso_ept_id,
plan_tratamiento.ingreso_id, form_definition.form_key — todas tenían un `create_index`
explícito sobre una columna ya cubierta por su unique constraint (y `unique=True, index=True`
en el modelo).

**Fix:** se eliminó el índice redundante en las 7 migraciones y el `index=True` redundante
en los 6 modelos (el UNIQUE ya provee el índice en ambos motores). Caso especial
`ingreso.folio`: como `0011b` le quita la unicidad (reingresos), su índice no-único se
**mueve** de `0011` a `0011b` — así nunca coexisten uq + ix sobre folio (ni en upgrade ni en
downgrade). `folio` conserva `index=True` en el modelo (en estado final no es único pero sí
indexado).

**Verificación:** 774 tests Postgres verdes, ciclo `upgrade head`/`downgrade base` desde BD
vacía OK, ruff limpio. La confirmación final contra Oracle la da el propio job gated del CI.
Nota: se editaron migraciones ya committeadas porque ninguna corrió en producción (todo
dev/CI) y el objetivo declarado de la épica es portabilidad real Oracle⇄Postgres.

### Segundo fix de portabilidad Oracle — tipo JSON (2026-06-12)

Resuelto el ORA-01408, el job Oracle reveló el siguiente agujero: `sa.JSON()` (tipo genérico
de SQLAlchemy) **no compila en Oracle** — `OracleTypeCompiler` no implementa `visit_JSON`
(`UnsupportedCompilationError`). Las convenciones D15 de la Fundación listaban `JSON` como
tipo portable, pero no lo es en el dialecto Oracle thin de SQLAlchemy 2.0.

**Solución:** `app/db/types.py::PortableJSON` (TypeDecorator) — delega al JSON nativo en
PostgreSQL y serializa a `Text`/CLOB en Oracle (`json.dumps`/`json.loads` en la capa de app).
Transparente en Postgres. Aplicado a las 4 columnas JSON del sistema: `imed_payload.datos`,
`ficha_clinica.contenido`, `form_definition.domain_values`, `ventana_proceso.columnas_visibles`
(modelos + migraciones). Convención D15 del roadmap actualizada para prohibir `sa.JSON` directo.

**Verificación:** 774 tests Postgres verdes (incluido round-trip JSON real en form-config/IMED/
fichas), ciclo upgrade/downgrade desde cero OK, ruff limpio. Confirmación Oracle: job gated del CI.

### Portabilidad Oracle — iteraciones 3-5 (queries + tests, 2026-06-12)

Tras los índices y JSON, el job Oracle gated reveló (y se corrigieron) más fugas D15:

- **Booleanos en queries (`ORA-00908: IS 0/1`):** `.is_(True)`/`.is_(False)` compila a `col IS 1`
  en Oracle (inválido; columnas Boolean = NUMBER(1)). Reemplazado por `== true()`/`== false()`
  (compila a `col = 1`/`= 0`, válido en ambos). Afectó oda, licencias acumulado/alerta,
  reporte_licencias, agendamiento.
- **SQL crudo en agendamiento (`= FALSE`):** 4 queries `text()` con literales booleanos
  Postgres-only en `_cargar_candidatos`/`_cargar_reposos_batch` → reescritas a SQLAlchemy Core
  (subquery MAX por ingreso, joins, `== false()`, `.distinct()`). No hay literal booleano
  portable en SQL crudo → la regla es construir con el ORM/Core.
- **Helpers de test con INSERT crudo Postgres-only:** `now()` (no existe en Oracle),
  `true`/`false`, `RETURNING id` (Oracle exige `RETURNING ... INTO` → `ORA-00925`) →
  reescritos con el ORM (ControlMedico/RegistroFarmacologico/Receta/AuditLog). El test de
  inmutabilidad mantiene el UPDATE/DELETE crudo (es su objetivo) pero inserta vía ORM.
- **Oracle `''` = NULL (`ORA-01400`):** `field_def.field_type` era NOT NULL pero un draft puede
  tener tipo vacío (`""`), que Oracle convierte a NULL. → columna nullable (migración 1221) +
  el validador ya trataba None/"" igual. Cambio aditivo, Postgres idéntico.
- **Smoke de tablas Postgres-only:** `get_table_names()` + `in` (lowercase) → `has_table()`
  (normaliza case/schema por dialecto).

**Lección D15 (actualizada en convenciones):** además de tipos genéricos, la portabilidad real
exige (a) no índices redundantes sobre columnas únicas, (b) `PortableJSON` en vez de `sa.JSON`,
(c) booleanos vía `== true()/false()` nunca `.is_(bool)` ni literales SQL, (d) nada de `now()`/
`RETURNING`/`true`/`false` en `text()` crudo — usar ORM/Core, (e) cuidado con `''`=NULL de Oracle.
Estado: migraciones y queries de producción portables; suite de tests portable. Confirmación
final: job Oracle gated del CI.
