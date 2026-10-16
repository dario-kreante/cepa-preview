# Pacientes borrador pendientes de folio — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada persona atendida en el CEPA según SALUTEM que no existe en el SIGE se crea sola como paciente "Pendiente de folio", aparece en una lista para admins con alerta y señal, y se completa registrando su folio (lo que crea su ingreso).

**Architecture:** Nuevo estado de registro en `paciente` (migración 1330, campos demográficos opcionales). Un paso nuevo del sync (`borradores.py`) crea los borradores al final de cada ciclo desde la copia de SALUTEM, con fecha de corte. La API suma la lista, el descarte y el alta de ingreso con `paciente_id`; el frontend suma la pantalla, la señal y el flujo de completar.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic (Postgres en tests, Oracle 19c en las VMs), pytest; React 19 + TS + TanStack Query + openapi-fetch, Vitest + MSW 2.

**Spec:** `docs/superpowers/specs/2026-10-16-pacientes-borrador-folio-design.md`

## Global Constraints

- Solo lectura sobre SALUTEM (v4 D12).
- Portabilidad D15: identificadores ≤ 30 caracteres; Oracle: booleanos con `== false()`, nunca expresiones booleanas en SELECT/GROUP BY.
- Estados de registro exactos: `completo` · `pendiente_folio` · `descartado`. Orígenes: `SIGE` · `SALUTEM`.
- Setting `SALUTEM_BORRADORES_DESDE` (fecha ISO `AAAA-MM-DD`); vacía = no se crean borradores.
- Tipo de alerta `paciente_pendiente_folio`, `caso_tipo = "paciente"`, `usuario_id = NULL`, `ventana_dias = 0`; título visible "Paciente nuevo pendiente de folio".
- Lista, descartar y completar: **solo Administrativo y Coordinación** (Auditor → 403). El Auditor sí ve la señal en buscador y ficha.
- Actor de auditoría del sync: `sistema:salutem-sync` (constante `ACTOR` existente en `app/services/salutem_sync/alertas_control.py`).
- Textos visibles en español. Señal: "Falta folio". Aviso en ficha: "Este paciente viene de SALUTEM y le falta el folio para completar su registro". Botón: "Completar registro". Menú: "Pendientes de folio".
- Commits en español, Conventional Commits, con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests backend: desde `backend/` con `"/Users/darioramirez/Proyectos Dev/CEPA Preview/backend/.venv/bin/pytest" <tests> -q -p no:warnings -o addopts=""`. Frontend desde `frontend/`: `npx vitest run`, `npm run typecheck`, `npm run lint`, `npm run build`. Un solo servidor MSW global (`server.use`).

## Review Focus

- **Persona sin RUT (`sin_id_…`) de punta a punta** — debe poder quedar como borrador, verse en la lista con su identificación de SALUTEM y completarse sin RUT → test en Tarea 2 (creación), Tarea 3 (lista) y Tarea 4 (completar sin RUT).
- **Pantallas existentes con un paciente sin RUT/sexo/edad/región** — el buscador y la ficha no deben romperse ni mostrar "null" → test en Tarea 6 (render con nulos muestra "—").
- **Completar con un RUT que ya tiene otro paciente** — 409 con mensaje claro, el borrador sigue pendiente → test en Tarea 4.
- **Ciclo siguiente tras completar** — el ingreso nuevo hace que la vinculación traiga sus atenciones (vía `ingresos_desde`) → test en Tarea 4 (vincular tras completar une las fichas).
- **`SALUTEM_BORRADORES_DESDE` inválida** — no crea borradores, registra el error y el ciclo termina → test en Tarea 2.

---

### Tarea 1: Modelo — estado de registro del paciente (migración 1330)

**Files:**
- Modify: `backend/app/domain/enums.py` (enums nuevos), `backend/app/models/paciente.py`, `backend/app/schemas/ingreso.py:112-124` (`PacienteRead`)
- Create: `backend/migrations/versions/1330_paciente_estado_registro.py`
- Test: `backend/tests/test_paciente_model.py` (casos nuevos)

**Interfaces:**
- Produces: `EstadoRegistroPaciente(str, Enum)` con `COMPLETO="completo"`, `PENDIENTE_FOLIO="pendiente_folio"`, `DESCARTADO="descartado"`; `OrigenPaciente(str, Enum)` con `SIGE="SIGE"`, `SALUTEM="SALUTEM"`. `Paciente` suma `estado_registro: str` (default `completo`), `origen: str` (default `SIGE`), `motivo_descarte: str | None` (300), `descartado_por: str | None` (80), `descartado_en: datetime | None` (tz); `rut`, `sexo`, `edad`, `region` pasan a `X | None`. `PacienteRead` suma `estado_registro: str`, `origen: str` y vuelve opcionales `rut`, `sexo`, `edad`, `region`.

- [ ] **Step 1: Tests que fallan** — `test_un_paciente_nuevo_queda_completo_y_de_origen_sige` (crear `Paciente` con los campos de hoy → `estado_registro == "completo"`, `origen == "SIGE"`); `test_un_borrador_admite_rut_sexo_edad_y_region_nulos` (crear con solo `nombre`, `estado_registro="pendiente_folio"`, `origen="SALUTEM"`, `salutem_persona_id=1180505` → flush sin error); `test_dos_borradores_sin_rut_no_chocan_por_unique` (dos pacientes con `rut=None` → flush sin error).
- [ ] **Step 2:** correr `tests/test_paciente_model.py` → FAIL (columna inexistente / NOT NULL).
- [ ] **Step 3:** enums, modelo y migración `1330` (`down_revision = "1320"`): `add_column` de los 5 campos (los NOT NULL con `server_default`), índice `ix_paciente_estado_registro`, `alter_column(..., nullable=True)` para `rut`, `sexo`, `edad`, `region`; `downgrade` revierte (borradores con nulos impiden bajar: documentarlo en el docstring). `PacienteRead` con los opcionales.
- [ ] **Step 4:** correr `tests/test_paciente_model.py tests/salutem_sync/test_migracion.py` y la suite completa → PASS (la sesión de tests aplica y revierte todas las migraciones).
- [ ] **Step 5: Commit** `feat(pacientes): estado de registro y datos opcionales para pacientes borrador`

### Tarea 2: Sync — crear borradores desde SALUTEM, con alerta

**Files:**
- Create: `backend/app/services/salutem_sync/borradores.py`
- Modify: `backend/app/config.py` (setting), `backend/app/domain/enums_alertas.py` (tipo), `backend/app/services/alertas.py` (`VENTANAS_DEFAULT`), `backend/app/services/salutem_sync/orquestador.py` (llamada tras `vincular`, todos los modos)
- Test: `backend/tests/salutem_sync/test_borradores.py`; `backend/tests/salutem_sync/test_orquestador.py` (un caso)

**Interfaces:**
- Consumes: `cruce_con_paciente()` (`app/services/salutem_sync/filtro.py`), `SalutemPersona`/`SalutemAtencion` (`app/models/salutem_copia.py`), `hoy_en_santiago` (`incremental.py`), `cargar_ventanas`, `ACTOR`.
- Produces: `Settings.salutem_borradores_desde: str = ""` y propiedad `salutem_borradores_desde_fecha -> date | None` (ValueError si el formato es inválido); `TipoAlerta.PACIENTE_PENDIENTE_FOLIO = "paciente_pendiente_folio"`; `crear_borradores(db: Session, ahora: datetime, desde: date | None) -> ResultadoBorradores(creados: int, errores: list[str])`; `paciente_desde_persona(persona: SalutemPersona, hoy: date) -> Paciente` (sin persistir; mapeo de la spec §2); `resolver_alerta_borrador(db: Session, paciente_id: int) -> None` (la usan las Tareas 3 y 4).

- [ ] **Step 1: Tests que fallan** (en `test_borradores.py`, fixture `AHORA` de `tests/salutem_sync/conftest.py`, corte `date(2026, 9, 1)`; guardar personas/atenciones con `copia.guardar_persona` / `copia.guardar_atencion` como en `test_alertas_control.py`):
  - `test_crea_un_borrador_por_persona_atendida_desde_el_corte` → 1 paciente `pendiente_folio`/`SALUTEM` con `salutem_persona_id`, y 1 alerta `paciente_pendiente_folio` con `caso_tipo="paciente"`, `usuario_id is None`.
  - `test_mapea_los_datos_de_salutem` — persona `{"nombres": "HUMBERTO", "apellidos": "ESCOBAR PRUEBA", "identificacion": "12345678-5", "sexo": "HOMBRE", "fechaNacimiento": "14-07-1967", "comuna": "Talca"}` → `nombre == "HUMBERTO ESCOBAR PRUEBA"`, `rut == "123456785"`, `sexo == "M"`, `edad == 59`, `comuna == "Talca"`, `region is None`.
  - `test_persona_sin_rut_queda_sin_rut` — identificación `sin_id_1141409`, `tipoIdentificacion` "SIN IDENTIFICACION" → `rut is None`; RUT inválido → `rut is None`; `sexo` "MUJER" → `"F"`; valor raro → `"otro"`; sin fecha → `edad is None`.
  - `test_sin_corte_no_crea_nada`; `test_ignora_atenciones_anteriores_al_corte_y_no_atendidas`.
  - `test_no_duplica_en_el_ciclo_siguiente`; `test_no_recrea_un_descartado`; `test_no_crea_si_ya_cruza_con_un_paciente_por_rut_o_por_id`.
  - `test_tipo_de_alerta_apagado_crea_el_borrador_sin_alerta` (fila `ConfigAlerta(tipo="paciente_pendiente_folio", dias=0, habiles=False, activo=False)`).
  - `test_un_error_en_una_persona_no_detiene_a_las_demas` (forzar con `monkeypatch` que `paciente_desde_persona` falle para un id).
  - `test_corte_invalido_no_crea_y_registra_el_error` (setting `"16/10/2026"` vía orquestador o `Settings`) → 0 creados, 1 error con el texto del valor.
  - En `test_orquestador.py`: `test_cada_modo_crea_borradores_despues_de_vincular` (monkeypatch de `orquestador.crear_borradores`, modos `caliente` y `tibia` → llamado una vez cada uno con `AHORA`).
- [ ] **Step 2:** correr `tests/salutem_sync/test_borradores.py` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3:** implementar. Candidatas: `select(SalutemPersona)` con `exists()` de `SalutemAtencion` (misma persona, `desaparecida_en IS NULL`, `fecha_cita >= desde`) y `~exists()` de `Paciente` que cumpla `cruce_con_paciente()`; filtrar `estadoCitaId == ATENDIDO` en Python sobre `contenido` (portable). Una persona por `db.begin_nested()`; auditoría `CREATE paciente`. Alerta solo si `cargar_ventanas(db)["paciente_pendiente_folio"]["activo"]`. `VENTANAS_DEFAULT` suma el tipo `{"dias": 0, "habiles": False}`. En `orquestador.correr`, tras `vincular` en todos los modos: `crear_borradores(db, ahora(), desde)`; un `ValueError` del setting se agrega a `errores` sin abortar.
- [ ] **Step 4:** correr `tests/salutem_sync` y `tests/test_alertas*.py tests/test_config_alertas.py` → PASS (actualizar los tests que cuentan tipos de alerta: 10 → 11).
- [ ] **Step 5: Commit** `feat(salutem-sync): crear pacientes borrador pendientes de folio desde SALUTEM`

### Tarea 3: API — lista de pendientes, descartar y buscador

**Files:**
- Create: `backend/app/services/pacientes_borrador.py`, `backend/app/schemas/paciente_borrador.py`
- Modify: `backend/app/routers/pacientes.py` (dos rutas, **antes** de `/{paciente_id}`), `backend/app/services/busqueda.py` (`buscar_pacientes`)
- Test: `backend/tests/test_pacientes_borrador_api.py`

**Interfaces:**
- Consumes: Tarea 1 (estados), Tarea 2 (`resolver_alerta_borrador`).
- Produces: `GET /api/v1/pacientes/pendientes-folio` → `list[PacientePendienteRead]` con `id`, `nombre`, `rut: str | None`, `identificacion_salutem: str | None`, `salutem_persona_id: int | None`, `creado_en: datetime`, `primera_atencion: date | None`, `ultima_atencion: date | None`, `atenciones: int`, `especialidades: list[str]` (distintas, máx. 5), orden `creado_en` ascendente. `POST /api/v1/pacientes/{paciente_id}/descartar` con `DescarteIn(motivo: str` 1–300`)` → `PacienteRead`. Servicios `listar_pendientes(db) -> list[PacientePendienteRead]`, `descartar(db, paciente_id: int, motivo: str, actor: str) -> Paciente`.

- [ ] **Step 1: Tests que fallan:** lista con un borrador con 2 atenciones (resumen correcto, especialidades), sin RUT muestra `identificacion_salutem == "sin_id_1141409"`; completos y descartados no aparecen; Auditor → 403, Administrativo y Coordinación → 200; descartar sin motivo → 422, con motivo → `estado_registro == "descartado"`, `motivo_descarte`, `descartado_por == username`, alerta resuelta, auditoría `UPDATE paciente`; descartar un `completo` → 409; `GET /buscar?q=<nombre>` devuelve el borrador con `estado_registro == "pendiente_folio"` y **no** devuelve el descartado.
- [ ] **Step 2:** correr → FAIL (404 en las rutas).
- [ ] **Step 3:** implementar. Resumen desde `SalutemAtencion` por `persona_id` (agregados en Python sobre las filas de la persona: pocas). `buscar_pacientes` filtra `Paciente.estado_registro != "descartado"`.
- [ ] **Step 4:** correr el archivo nuevo + `tests/test_busqueda_api.py tests/test_pacientes*.py` → PASS.
- [ ] **Step 5: Commit** `feat(pacientes): lista de pendientes de folio y descarte de borradores`

### Tarea 4: Completar el registro = crear el ingreso del borrador

**Files:**
- Modify: `backend/app/schemas/ingreso.py` (`IngresoCreate`), `backend/app/services/ingreso.py` (`crear_ingreso`, `_obtener_o_crear_paciente`)
- Test: `backend/tests/test_ingreso_completar_borrador.py`

**Interfaces:**
- Consumes: Tareas 1–3.
- Produces: `IngresoCreate.paciente_id: int | None = None`; `IngresoCreate.rut: str | None` con validador de modelo: obligatorio salvo que venga `paciente_id` (la regla "el paciente no tiene RUT" se valida en el servicio). Con `paciente_id`: 404 si no existe; 409 si no está `pendiente_folio`; si llega un RUT que tiene otro paciente → 409 "El RUT … ya pertenece a otro paciente. Si es la misma persona, descarta este borrador."; si no llega RUT y el borrador tampoco tiene → se permite; si el borrador tiene RUT y no llega → se conserva el del borrador.

- [ ] **Step 1: Tests que fallan:** completar con folio manual → ingreso con ese folio, paciente `completo` con los datos enviados, alerta `paciente_pendiente_folio` resuelta; con folio automático (sin `folio`) → folio correlativo; borrador sin RUT completado sin RUT → 201; sin `paciente_id` y sin RUT → 422; RUT de otro paciente → 409 y el borrador sigue `pendiente_folio`; `paciente_id` de un `completo` o `descartado` → 409; tras completar, `vincular(db, ahora, ingresos_desde=<antes del ingreso>)` crea las `FichaClinica` del folio desde la copia de SALUTEM (Review Focus).
- [ ] **Step 2:** correr → FAIL.
- [ ] **Step 3:** implementar. `crear_ingreso` toma el paciente por `paciente_id` cuando viene (en vez de buscar por RUT), actualiza sus datos, crea el ingreso con `_resolver_folio` igual que hoy, pone `estado_registro = "completo"` y llama `resolver_alerta_borrador`.
- [ ] **Step 4:** correr el archivo nuevo + `tests/test_ingreso*.py tests/test_folio*.py` y la suite completa → PASS.
- [ ] **Step 5: Commit** `feat(ingresos): completar el registro de un paciente borrador registrando su folio`

### Tarea 5: Frontend — pantalla "Pendientes de folio"

**Files:**
- Modify: `frontend/src/types/api.ts` (regenerado), `frontend/src/app/shell/nav.ts`, `frontend/src/app/router.tsx`
- Create: `frontend/src/features/pacientes-borrador/api.ts`, `hooks.ts`, `PendientesFolioPage.tsx`, `DescartarBorradorDialog.tsx`, `PendientesFolioPage.test.tsx`

**Interfaces:**
- Consumes: rutas de la Tarea 3.
- Produces: `listarPendientesFolio(): Promise<PacientePendienteRead[]>`, `descartarBorrador(id: number, motivo: string): Promise<PacienteRead>`, `usePendientesFolio()` (queryKey `["pacientes", "pendientes-folio"]`), `useDescartarBorrador()` (invalida esa clave y `["alertas"]`). Ruta `/pendientes-folio` dentro de `ProtectedRoute rolesEscritura`; item de menú "Pendientes de folio" en "Módulos clínicos" con `roles: ["Administrativo", "Coordinacion"]` y contador (badge con la cantidad cuando > 0).

- [ ] **Step 1: Regenerar tipos:** desde `backend/` exportar `app.openapi()` a `/tmp/cepa-openapi.json`; desde `frontend/` `npx openapi-typescript /tmp/cepa-openapi.json -o src/types/api.ts`; revisar que el diff solo traiga lo de las Tareas 1–4.
- [ ] **Step 2: Tests que fallan** (`PendientesFolioPage.test.tsx`): lista con un borrador sin RUT muestra nombre, `sin_id_1141409`, "15-10-2026" como primera atención y "Médico/a"; "Completar registro" navega a `/ingresos/nuevo?paciente=<id>`; "Descartar" exige motivo y hace `POST …/descartar` con `{motivo}`; lista vacía muestra "No hay pacientes pendientes de folio"; el item de menú no aparece para Auditor y muestra el contador para Administrativo.
- [ ] **Step 3:** correr → FAIL. **Step 4:** implementar. **Step 5:** `npx vitest run src/features/pacientes-borrador src/app` + `npm run typecheck` → PASS.
- [ ] **Step 6: Commit** `feat(pacientes): pantalla de pacientes pendientes de folio`

### Tarea 6: Frontend — señal "Falta folio", completar registro y alerta

**Files:**
- Modify: `frontend/src/features/ingresos/IngresosListaPage.tsx` (resultados del buscador), `frontend/src/features/ingresos/PatientSheet.tsx` (ficha), `frontend/src/features/ingresos/AltaIngresoPage.tsx` + `ingresoSchema.ts` (precarga con `?paciente=`), `frontend/src/components/shell/AlertsPanel.tsx` (título y destino), los componentes que formatean RUT/sexo/edad/región en esas pantallas
- Test: `IngresosListaPage.test.tsx`, `PatientSheet.test.tsx`, `AltaIngresoPage.test.tsx`, `AlertsPanel.test.tsx` (casos nuevos)

**Interfaces:**
- Consumes: Tarea 5 (`PacienteRead` con `estado_registro`), Tarea 4 (`IngresoCreate.paciente_id`).
- Produces: distintivo "Falta folio" cuando `estado_registro === "pendiente_folio"`; en la ficha, el aviso de la spec y el botón "Completar registro" (solo escritores) → `/ingresos/nuevo?paciente=<id>`; `AltaIngresoPage` con `?paciente=<id>` precarga nombre/RUT/sexo/edad/región/comuna/contacto desde `GET /api/v1/pacientes/{id}`, envía `paciente_id` y, si el paciente no tiene RUT, deja el RUT opcional mostrando la identificación de SALUTEM; `TITULOS_ALERTA["paciente_pendiente_folio"] = "Paciente nuevo pendiente de folio"` y clic → `/pendientes-folio`.

- [ ] **Step 1: Tests que fallan:** buscador muestra "Falta folio" para un borrador y no para un completo; un borrador con `rut/sexo/edad/region` nulos se ve con "—" y sin "null" (Review Focus); ficha de un borrador muestra el aviso y "Completar registro" (no para Auditor); alta con `?paciente=7` precarga el nombre y envía `paciente_id: 7` en el `POST /api/v1/ingresos`; borrador sin RUT permite enviar sin RUT; alerta `paciente_pendiente_folio` se titula "Paciente nuevo pendiente de folio" y navega a `/pendientes-folio`.
- [ ] **Step 2:** correr → FAIL. **Step 3:** implementar. **Step 4:** `npx vitest run` completo, `npm run typecheck`, `npm run lint` (sin errores nuevos), `npm run build` → PASS.
- [ ] **Step 5: Commit** `feat(pacientes): señal Falta folio y completar registro desde la ficha`

### Tarea 7: Verificación, runbook y despliegue

**Files:**
- Modify: `docs/operacion/salutem-sync.md` (sección "Pacientes borrador")

- [ ] **Step 1:** suites completas backend y frontend (comandos de Global Constraints) → todo verde.
- [ ] **Step 2:** runbook: qué hace el paso de borradores, `SALUTEM_BORRADORES_DESDE` (vacía = apagado; configurar con el día de activación en el `.env` de cada VM), migración 1330 **primero en la Oracle de QA**, que en las VMs solo aplica a las personas de `SALUTEM_SYNC_PERSONAS_PERMITIDAS`, y cómo descartar.
- [ ] **Step 3: Commit** `docs(salutem-sync): pacientes borrador pendientes de folio`
- [ ] **Step 4 (con el usuario):** desplegar en QA y luego en dev con los scripts `aplicar.sh` existentes (migración 1330), configurar `SALUTEM_BORRADORES_DESDE` en cada `.env` (lo hace el usuario o con su aprobación), y validar con una persona de prueba nueva: aparece en "Pendientes de folio" con alerta; al completar con folio, en el ciclo siguiente se unen sus atenciones.
