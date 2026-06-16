# SIGE — Ciclo 3: Controles médicos (EPIC-06) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Pasos con checkbox (`- [ ]`).

**Goal:** Portar el módulo **Controles médicos** al `frontend/`, conectado al backend, con las mejoras del documento (lista estilo Variante 1: Fecha control, Próximo control, **Semana control**, **Días LM**, **Reposo total/parcial**, **GAF** mini-bar, **RECA** estado, médico; filtros preset; acciones alta / próximo control / subform licencia+GAF+RECA), reemplazando el placeholder.

**Architecture:** Reusa la Fundación v2 + el patrón ya consolidado en Ciclos 1-2 (shell, design system, apiClient tipado, TanStack Query, MSW). El backend de controles es **por-ingreso** (no hay listado global): la página es **paciente/ingreso-driven** igual que Fármacos — busca paciente (reusa `buscarPacientes`/`useBuscarPacientes`), resuelve el `ingreso_id` primario vía `useVista360(pacienteId)` → `vista.ingresos?.[0]?.id`, y lista los controles de ese ingreso. Estilo de referencia: `frontend/ui-base-v2/src/pages/SimplePages.tsx` (componente `Controles`) + el módulo `features/farmacos` como plantilla estructural directa.

**Tech Stack:** igual que Ciclos 1-2. Contratos (verificar nombres/campos exactos en `frontend/src/types/api.ts`):
- `POST /api/v1/controles-medicos` → `ControlMedicoCreate` (`ingreso_id`, `fecha_control`, `medico_tratante`, `region_derivacion`) → `ControlMedicoRead`. **`semana_control` se autocalcula en backend** (no se envía).
- `GET /api/v1/controles-medicos/por-ingreso/{ingreso_id}` → `ControlMedicoRead[]`.
- `GET /api/v1/controles-medicos/{control_id}` → `ControlMedicoRead`.
- `PATCH /api/v1/controles-medicos/{control_id}/proximo-control` → `ProximoControlUpdate` (`proximo_control: date`, `proximo_agendado: bool`) → `ControlMedicoRead`.
- `PATCH /api/v1/controles-medicos/{control_id}/licencia` → `LicenciaUpdate` → `ControlMedicoRead`.
- `ControlMedicoRead`: id, ingreso_id, fecha_control, **semana_control** (int), medico_tratante, region_derivacion, proximo_control?, proximo_agendado, tiene_licencia, resumen_termino_lm?, total_dias_lm?, tipo_licencia?, tipo_reposo?, gaf?, estado_reca?, observaciones?.
- Enums: `EstadoReca = "pendiente"|"aprobado"|"rechazado"|"en_proceso"|"no_aplica"`; `app__domain__enums_controles__TipoLicencia = "1"|"5"|"6"|"3"|"4"|"extra_sistema"`; `app__domain__enums_controles__TipoReposo = "total"|"parcial"`.
- **Reglas de `LicenciaUpdate` (RN CEPA-062, mirror en zod):** si `tiene_licencia=true` ⇒ **obligatorios**: `resumen_termino_lm`, `total_dias_lm` (entero ≥1), `tipo_licencia`, `tipo_reposo`. `gaf` opcional pero si está presente debe estar **entre 0 y 100**. `estado_reca` y `observaciones` opcionales. Si `tiene_licencia=false` ⇒ los campos de licencia van vacíos/null.

**RBAC:** writer = `Administrativo`/`Coordinacion` (alta, próximo control, licencia). reader = +`Auditor`. Usar `puedeEscribir(rol as Rol)` de `@/lib/rbac` (mismo patrón que Fármacos/Licencias).

**Gaps conocidos (documentar, no inventar):**
- No hay listado global de controles → la lista y los filtros operan en **scope del paciente/ingreso** (igual que Fármacos). Nota en código.
- `ControlMedicoRead` NO tiene fecha de RECA (solo `estado_reca`). El spec menciona "RECA estado/fecha" pero el contrato solo expone el estado → mostrar **estado RECA**; no inventar fecha.

**Convención:** comandos desde `frontend/`. Commits locales, **no pushear**. Gate por cierre: `npm run typecheck && npm run lint && npm run test && npm run build`.

---

### Task 1: Controles — capa API + hooks

**Files:** Create `frontend/src/features/controles/api.ts`, `hooks.ts`, `hooks.test.tsx`.

- [ ] **Step 1: Verificar contratos** en `frontend/src/types/api.ts`: `ControlMedicoCreate`, `ControlMedicoRead`, `ProximoControlUpdate`, `LicenciaUpdate`, enums `EstadoReca` + `app__domain__enums_controles__TipoLicencia`/`TipoReposo`. Anotar nombres/campos reales. Sin `any`.
- [ ] **Step 2: api.ts** — funciones tipadas sobre `api` (`@/lib/apiClient`), exportar tipos:
  - `crearControl(body: ControlMedicoCreate): Promise<ControlMedicoRead>` → `POST /api/v1/controles-medicos` (mapear 409/422 a Error claro).
  - `controlesPorIngreso(ingresoId: number): Promise<ControlMedicoRead[]>` → `GET .../por-ingreso/{ingreso_id}`.
  - `obtenerControl(controlId: number): Promise<ControlMedicoRead>` → `GET .../{control_id}`.
  - `actualizarProximoControl(controlId: number, body: ProximoControlUpdate): Promise<ControlMedicoRead>` → `PATCH .../{control_id}/proximo-control`.
  - `actualizarLicencia(controlId: number, body: LicenciaUpdate): Promise<ControlMedicoRead>` → `PATCH .../{control_id}/licencia`.
  Exportar `ControlMedicoRead`, `ControlMedicoCreate`, `ProximoControlUpdate`, `LicenciaUpdate`, y los tres enum types.
- [ ] **Step 3: Test que falla (MSW global `server.use`, patrón de `features/farmacos/hooks.test.tsx`):** handler de `GET /api/v1/controles-medicos/por-ingreso/:ingreso_id` devolviendo 1 control → render `useControlesPorIngreso(1)` y esperar `isSuccess` + `data.length===1`. Run → FAIL.
- [ ] **Step 4: hooks.ts** — `useControlesPorIngreso(ingresoId)` (useQuery, `enabled: !!ingresoId`, queryKey `["controles", ingresoId]`), `useControl(controlId)`; mutations `useCrearControl()`, `useActualizarProximoControl()`, `useActualizarLicencia()` con invalidación de `["controles", ingresoId]`. Implementar → PASS.
- [ ] **Step 5: Gate + commit.** `npm run test -- src/features/controles && npx tsc -b`.
```bash
git add frontend/src/features/controles
git commit -m "feat(controles): capa API tipada + hooks (alta/por-ingreso/próximo-control/licencia)"
```

---

### Task 2: Controles — página (paciente-driven + tabla Variante 1 + filtros + KPIs)

**Files:** Create `frontend/src/features/controles/ControlesPage.tsx`, `ControlesPage.test.tsx`. Modify `frontend/src/app/router.tsx` (reemplazar placeholder `/controles`).

- [ ] **Step 1: Página** — patrón paciente-driven idéntico a `features/farmacos/FarmacosPage.tsx` (leerlo y reusar el flujo: buscador con debounce 300ms + placeholder "Buscar por RUT, folio o nombre" → seleccionar paciente → `useVista360` → `ingreso_id` primario → `useControlesPorIngreso(ingresoId)`):
  - `PageHeader`: "Controles médicos" + subtítulo (nº de controles, nº con licencia, nº con próximo control agendado) + botón "Nuevo control" (Task 3; oculto para Auditor vía `puedeEscribir`).
  - **Tabla en filas (estilo Variante 1)**: columnas **Fecha control** (`fmtDate`), **Próximo control** (`proximo_control` + badge "Agendado" si `proximo_agendado`), **Semana** (`semana_control`), **Días LM** (`total_dias_lm` ?? "—"), **Reposo** (`tipo_reposo` badge total/parcial, o "—"), **GAF** (mini-bar 0-100 si `gaf!=null`, si no "—"), **RECA** (`estado_reca` badge, o "—"), **Médico** (`medico_tratante`). Acciones por fila → Tasks 4 y 5 (por ahora placeholders no-op si hace falta).
  - Filtros preset (scope del paciente): por `estado_reca`, por `tipo_reposo`, y con/sin licencia (`tiene_licencia`). Nota en código del scope-ingreso (gap backend).
  - Estados carga/empty/error.
- [ ] **Step 2: Test** (`ControlesPage.test.tsx`, MSW global, harness de auth/role de `features/farmacos/*.test.tsx`): busca+selecciona paciente → muestra ≥1 fila de control con semana/días/reposo/GAF/RECA; estados cubiertos; RBAC: Auditor no ve "Nuevo control".
- [ ] **Step 3: Router.** Reemplazar `<ProximamentePage titulo="Controles médicos" />` por `<ControlesPage />`.
- [ ] **Step 4: Gate + commit.** `npm run test -- src/features/controles && npx tsc -b`.
```bash
git add frontend/src/features/controles frontend/src/app/router.tsx
git commit -m "feat(controles): página paciente-driven (tabla Variante 1: semana/días LM/reposo/GAF/RECA)"
```

---

### Task 3: Controles — alta de control

**Files:** Create `frontend/src/features/controles/NuevoControlDialog.tsx`, `controlSchema.ts`. Modify `ControlesPage.tsx`.

- [ ] **Step 1:** `controlSchema.ts` (zod): `fecha_control` (req, fecha), `medico_tratante` (req non-empty), `region_derivacion` (req non-empty). **NO** incluir `semana_control` (autocalc backend) ni `ingreso_id` (se inyecta del paciente seleccionado). Exportar tipo inferido.
- [ ] **Step 2:** `NuevoControlDialog` (Dialog + RHF + zodResolver; mirror `features/farmacos/NuevaRecetaDialog.tsx`): inputs fecha_control (`type="date"`), medico_tratante, region_derivacion. Submit → `useCrearControl()` con `{ ingreso_id, ...values }`. Cierra al éxito, errores via toast. Requiere `ingresoId` (paciente seleccionado) + writer.
- [ ] **Step 3:** Wire el botón "Nuevo control" del header para abrir el dialog (writers, con paciente seleccionado).
- [ ] **Step 4: Test.** Alta válida → `POST /api/v1/controles-medicos` con `ingreso_id` correcto, refetch muestra el control; validación: medico_tratante vacío bloquea submit (mutation no llamada, spy). RBAC Auditor no ve el botón.
- [ ] **Step 5: Gate + commit.** `npm run test -- src/features/controles && npx tsc -b`.
```bash
git add frontend/src/features/controles
git commit -m "feat(controles): alta de control (zod, semana autocalculada en backend)"
```

---

### Task 4: Controles — próximo control

**Files:** Create `frontend/src/features/controles/ProximoControlDialog.tsx`, `proximoControlSchema.ts`. Modify `ControlesPage.tsx`.

- [ ] **Step 1:** `proximoControlSchema.ts` (zod): `proximo_control` (req, fecha), `proximo_agendado` (bool, default false).
- [ ] **Step 2:** `ProximoControlDialog` (Dialog + RHF + zodResolver): input fecha + checkbox agendado. Submit → `useActualizarProximoControl(controlId)`. Acción por fila ("Próximo control") en la tabla (writers). Prefill con el `proximo_control`/`proximo_agendado` actuales si existen.
- [ ] **Step 3: Test.** PATCH `.../{id}/proximo-control` con fecha+flag; refetch refleja el cambio. Validación fecha requerida. RBAC.
- [ ] **Step 4: Gate + commit.** `npm run test -- src/features/controles && npx tsc -b`.
```bash
git add frontend/src/features/controles
git commit -m "feat(controles): acción próximo control (fecha + agendado)"
```

---

### Task 5: Controles — subform licencia + GAF + RECA

**Files:** Create `frontend/src/features/controles/LicenciaControlDialog.tsx`, `licenciaControlSchema.ts`. Modify `ControlesPage.tsx`.

- [ ] **Step 1:** `licenciaControlSchema.ts` (zod, validación condicional RN CEPA-062): `tiene_licencia` (bool). Si true ⇒ **obligatorios** `resumen_termino_lm` (non-empty), `total_dias_lm` (entero ≥1), `tipo_licencia` (enum TipoLicencia), `tipo_reposo` (enum TipoReposo). `gaf` opcional pero **0..100** si presente. `estado_reca` (enum EstadoReca) opcional. `observaciones` opcional. Usar `.superRefine` (mirror `features/farmacos/seguimientoSchema.ts`). Coerción a null de opcionales vacíos y de los campos de licencia cuando `tiene_licencia=false` (mismo criterio que el fix de seguimiento: no enviar datos inconsistentes).
- [ ] **Step 2:** `LicenciaControlDialog` (Dialog + RHF + zodResolver): checkbox tiene_licencia + campos condicionales (inputs/selects nativos con labels amigables para los enums; `total_dias_lm` `type="number"` min 1; `gaf` `type="number"` 0-100). Submit → `useActualizarLicencia(controlId)`. Acción por fila ("Licencia/RECA") en la tabla (writers). Prefill con los valores actuales del control.
- [ ] **Step 3: Test.** tiene_licencia=true con `total_dias_lm` vacío (o tipo_licencia/tipo_reposo faltantes) ⇒ bloqueado (mutation no llamada, spy). gaf=150 ⇒ bloqueado. Caso válido (tiene_licencia=true con los 4 campos) ⇒ PATCH `.../licencia` y refetch refleja reposo/GAF/RECA. Caso tiene_licencia=false ⇒ envía campos de licencia null. RBAC.
- [ ] **Step 4: Gate + commit.** `npm run test -- src/features/controles && npx tsc -b`.
```bash
git add frontend/src/features/controles
git commit -m "feat(controles): subform licencia + GAF + RECA (validación condicional CEPA-062)"
```

---

### Task 6: Verificación de cierre del ciclo

- [ ] **Step 1:** Gate completo desde `frontend/`: `npm run typecheck && npm run lint && npm run test && npm run build`. Cero errores lint/tsc, build OK, tests verdes.
- [ ] **Step 2:** Revisar que `/controles` ya no es placeholder; nav + quick-actions coherentes con RBAC.
- [ ] **Step 3:** Actualizar memoria `sige-ui-base-v2.md` (marcar Ciclo 3 COMPLETO + notas contrato/gaps).
