# SIGE — Ciclo 2: Gestión de fármacos (EPIC-02) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Pasos con checkbox (`- [ ]`).

**Goal:** Portar el módulo **Gestión de fármacos** del prototipo v2 al `frontend/`, conectado al backend, con las mejoras del documento (modelo de info estilo Variante 1: **receta completa por paciente con plazos** emisión/revisión/envío, **cambio de esquema**, **estado**; filas **no** cuadritos por medicamento; **sin categoría "socorro"**; filtros preset por estado/médico/marca), reemplazando el placeholder.

**Architecture:** Reusa la Fundación v2 (shell, design system, apiClient tipado, TanStack Query, MSW). El backend de fármacos es **por-ingreso (1:1 registro-farmacológico ↔ ingreso)**, NO hay endpoint "listar todas las recetas" cross-paciente. Igual que Licencias fue folio-driven, **Fármacos es paciente/ingreso-driven**: la página busca paciente (reusa `buscarPacientes` de `features/ingresos/api.ts`) → resuelve su `ingreso_id` → carga registro + esquema (indicaciones) + recetas + seguimientos de ese ingreso y los muestra con estilo v2. Estilo de referencia: `frontend/ui-base-v2/src/pages/SimplePages.tsx` (componente `Farmacos`).

**Tech Stack:** igual que Ciclo 0/1. Contratos (verificar nombres/campos exactos en `frontend/src/types/api.ts`):
- `GET /api/v1/registro-farmacologico/{ingreso_id}` → `RegistroFarmacologicoRead` (404 si no existe registro).
- `POST /api/v1/registro-farmacologico` → `RegistroFarmacologicoCreate` (ingreso_id, medico_tratante, estado_farmacologico, antecedentes_previos?, tratamiento_previo?) → `RegistroFarmacologicoRead`.
- `PATCH /api/v1/registro-farmacologico/{ingreso_id}` → `RegistroFarmacologicoUpdate` → `RegistroFarmacologicoRead`.
- `GET .../{ingreso_id}/esquema` → `EsquemaIndicacionRead[]`; `POST .../{ingreso_id}/esquema` → `EsquemaIndicacionBody` (medicamento, dosis, frecuencia: `FrecuenciaFarmaco`, extra_sistema) → `EsquemaIndicacionRead`.
- `GET .../{ingreso_id}/recetas` → `RecetaRead[]`; `POST .../{ingreso_id}/recetas` → `RecetaBody` (fecha_emision, fecha_revision, fecha_envio?, marca_medicamento) → `RecetaRead`.
- `GET .../{ingreso_id}/seguimientos` → `SeguimTratamientoRead[]`; `POST .../{ingreso_id}/seguimientos` → `SeguimTratamientoBody` (disminucion_farmacos, plan_disminucion?, cambio_esquema, detalle_cambio?, observaciones?) → `SeguimTratamientoRead`.
- `POST /api/v1/registro-farmacologico/recetas/alertas/generar` → `list[AlertaRead]` (revisión próxima ≤5 días).
- Enums: `EstadoFarmacologico = "activo"|"suspendido"|"completado"|"pendiente"`; `FrecuenciaFarmaco = "c/24h"|"c/12h"|"c/8h"|"c/6h"|"semanal"|"bisemanal"|"mensual"|"otro"` (**no hay "socorro"** — el backend ya lo eliminó; el frontend simplemente nunca lo ofrece).

**RBAC:** writer = `Administrativo`/`Coordinacion` (crear/editar registro, esquema, recetas, seguimientos, generar alertas). reader = +`Auditor`. Usar el helper `puedeEscribir` del proyecto (mismo patrón que Licencias).

**Gaps conocidos (documentar, no inventar):**
- No existe listado global de recetas ni búsqueda por marca/médico a nivel API. Los filtros preset (estado/médico/marca) operan **sobre las recetas/indicaciones del paciente cargado** (scope del ingreso), no cross-paciente. Se deja nota para mejora futura de backend.
- "Estado" de la receta no existe como campo en `RecetaRead`; el estado mostrado (Vigente/Por vencer/Vencida) se **deriva en cliente** de `fecha_revision` vs hoy (ventana 5 días = "Por vencer", igual que la regla de alertas del backend). El "estado farmacológico" (activo/suspendido/…) es a nivel **registro**, no receta.

**Convención:** comandos desde `frontend/`. Commits locales, **no pushear**. Gate por cierre: `npm run typecheck && npm run lint && npm run test && npm run build`.

---

### Task 1: Fármacos — capa API + hooks

**Files:** Create `frontend/src/features/farmacos/api.ts`, `hooks.ts`, `hooks.test.tsx`.

- [ ] **Step 1: Verificar contratos.** Leer en `frontend/src/types/api.ts` los campos exactos de `RegistroFarmacologicoRead/Create/Update`, `EsquemaIndicacionRead/Body`, `RecetaRead/Body`, `SeguimTratamientoRead/Body`, `AlertaRead`, y enums `EstadoFarmacologico`, `FrecuenciaFarmaco`. Reusar el tipo `RecetaRead` ya exportado en `features/ingresos/api.ts` solo si conviene; preferible re-exportar desde el feature propio. Sin `any`.

- [ ] **Step 2: api.ts** — funciones tipadas sobre `api` (`@/lib/apiClient`):
  - `obtenerRegistro(ingresoId)` → `GET .../{ingreso_id}` (404 → devolver `null`, NO lanzar: significa "sin registro aún").
  - `crearRegistro(body: RegistroFarmacologicoCreate)` → `POST` (mapear 409/422 a Error claro).
  - `actualizarRegistro(ingresoId, body: RegistroFarmacologicoUpdate)` → `PATCH`.
  - `listarIndicaciones(ingresoId)` / `agregarIndicacion(ingresoId, body: EsquemaIndicacionBody)`.
  - `listarRecetas(ingresoId)` / `crearReceta(ingresoId, body: RecetaBody)`.
  - `listarSeguimientos(ingresoId)` / `crearSeguimiento(ingresoId, body: SeguimTratamientoBody)`.
  - `generarAlertasRevision()` → `POST /api/v1/registro-farmacologico/recetas/alertas/generar`.
  Exportar tipos.

- [ ] **Step 3: Test que falla (MSW global `server.use`).** `hooks.test.tsx`: handler de `GET /api/v1/registro-farmacologico/:ingreso_id/recetas` devolviendo 1 receta; render `useRecetas(1)` y esperar `isSuccess` + `data.length===1`. Añadir un caso para `useRegistro` con 404 → `data === null` sin estado de error. Run → FAIL.

- [ ] **Step 4: hooks.ts** — `useRegistro(ingresoId)`, `useIndicaciones(ingresoId)`, `useRecetas(ingresoId)`, `useSeguimientos(ingresoId)` (useQuery, `enabled: !!ingresoId`); `useCrearRegistro()`, `useActualizarRegistro()`, `useAgregarIndicacion()`, `useCrearReceta()`, `useCrearSeguimiento()`, `useGenerarAlertasRevision()` (useMutation con invalidación de las queries `["farmacos", ingresoId, ...]`). Implementar. Run → PASS.

- [ ] **Step 5: Gate + commit.** `npm run test -- src/features/farmacos && npx tsc -b`.
```bash
git add frontend/src/features/farmacos
git commit -m "feat(farmacos): capa API tipada + hooks (registro/esquema/recetas/seguimiento/alertas)"
```

---

### Task 2: Fármacos — página (paciente-driven + panel registro + recetas en filas + filtros + KPIs)

**Files:** Create `frontend/src/features/farmacos/FarmacosPage.tsx`, `FarmacosPage.test.tsx`. Modify `frontend/src/app/router.tsx` (reemplazar placeholder `/farmacos`).

- [ ] **Step 1: Página.** Portar el estilo del componente `Farmacos` de `ui-base-v2/.../SimplePages.tsx`, adaptado a datos reales paciente-driven:
  - Buscador (reusa `buscarPacientes`, placeholder "Buscar por RUT, folio o nombre") → al elegir paciente, resolver `ingreso_id` (del PacienteRead/vista-360, mismo patrón que `PatientSheet`) y cargar `useRegistro/useRecetas/useIndicaciones` de ese ingreso.
  - `PageHeader`: "Gestión de fármacos" + subtítulo con conteo de recetas y cuántas "por vencer"/"vencidas" (derivado en cliente) + botón "Nueva receta" (abre dialog Task 4; oculto para Auditor).
  - Panel de **registro farmacológico** del paciente: médico tratante, `estado_farmacologico` (Badge), antecedentes/tratamiento previo. Si no hay registro (`null`): empty state con CTA "Crear registro" (writer).
  - **Recetas en filas** (no cuadritos): tabla/cards v2 con marca_medicamento, fecha_emision, fecha_revision, fecha_envio (al paciente), y Badge de estado derivado (Vigente/Por vencer/Vencida). Usar `fmtDate`/tokens del design system.
  - Filtros preset (estado derivado, marca, médico tratante del registro) sobre el scope del paciente. Nota visible/comentario de que es scope-ingreso (gap backend).
- [ ] **Step 2: Test.** `FarmacosPage.test.tsx` con MSW global: busca paciente → muestra registro + ≥1 receta con su badge de estado. Estados de carga/empty/error cubiertos. RBAC: con rol Auditor no aparece "Nueva receta".
- [ ] **Step 3: Router.** Reemplazar `<ProximamentePage titulo="Gestión de fármacos" />` por `<FarmacosPage />`.
- [ ] **Step 4: Gate + commit.** `npm run test -- src/features/farmacos && npx tsc -b`.
```bash
git add frontend/src/features/farmacos frontend/src/app/router.tsx
git commit -m "feat(farmacos): página paciente-driven (registro + recetas en filas + filtros + estado derivado)"
```

---

### Task 3: Fármacos — esquema de indicaciones (listar + agregar)

**Files:** Create `frontend/src/features/farmacos/EsquemaPanel.tsx`, `AgregarIndicacionDialog.tsx`, `indicacionSchema.ts`. Modify `FarmacosPage.tsx`.

- [ ] **Step 1:** `EsquemaPanel` — lista las indicaciones del registro (medicamento, dosis, `frecuencia`, `extra_sistema`/`vigente` como badges). Empty state si no hay.
- [ ] **Step 2:** `AgregarIndicacionDialog` con form zod (`indicacionSchema`): medicamento (req), dosis (req), frecuencia (select del enum `FrecuenciaFarmaco` — **sin "socorro"**), extra_sistema (checkbox). Submit → `useAgregarIndicacion`. Oculto/disabled si no hay registro o no es writer.
- [ ] **Step 3: Test.** Render esquema con 2 indicaciones; abrir dialog, enviar, refetch muestra 3. Validación: medicamento vacío bloquea submit.
- [ ] **Step 4: Gate + commit.** `npm run test -- src/features/farmacos && npx tsc -b`.
```bash
git add frontend/src/features/farmacos frontend/src/app/router.tsx
git commit -m "feat(farmacos): esquema de indicaciones (lista + alta con zod, frecuencias sin socorro)"
```

---

### Task 4: Fármacos — nueva receta + crear registro

**Files:** Create `frontend/src/features/farmacos/NuevaRecetaDialog.tsx`, `recetaSchema.ts`, `CrearRegistroDialog.tsx`, `registroSchema.ts`. Modify `FarmacosPage.tsx`.

- [ ] **Step 1:** `CrearRegistroDialog` (zod): medico_tratante (req), estado_farmacologico (select enum), antecedentes_previos?, tratamiento_previo?. Submit → `useCrearRegistro` con `ingreso_id` resuelto. Solo cuando el paciente no tiene registro.
- [ ] **Step 2:** `NuevaRecetaDialog` (zod `recetaSchema`): fecha_emision (req), fecha_revision (req, **≥ emisión** — RN CEPA-022), fecha_envio? (**≥ emisión** si presente), marca_medicamento (req). Submit → `useCrearReceta`. Requiere registro existente (si no, primero CrearRegistro).
- [ ] **Step 3: Test.** Coherencia de fechas: revisión < emisión bloquea submit con mensaje; alta válida refetcha y muestra la receta. Crear registro cuando no existe habilita "Nueva receta".
- [ ] **Step 4: Gate + commit.** `npm run test -- src/features/farmacos && npx tsc -b`.
```bash
git add frontend/src/features/farmacos
git commit -m "feat(farmacos): alta de receta (zod + coherencia de fechas) + crear registro"
```

---

### Task 5: Fármacos — seguimiento de tratamiento + generar alertas de revisión

**Files:** Create `frontend/src/features/farmacos/SeguimientoPanel.tsx`, `NuevoSeguimientoDialog.tsx`, `seguimientoSchema.ts`. Modify `FarmacosPage.tsx`.

- [ ] **Step 1:** `SeguimientoPanel` — lista seguimientos (disminucion_farmacos, cambio_esquema como badges; plan/detalle/observaciones). Empty state.
- [ ] **Step 2:** `NuevoSeguimientoDialog` (zod): disminucion_farmacos (bool) → `plan_disminucion` requerido si true (RN CEPA-023); cambio_esquema (bool) → `detalle_cambio` requerido si true; observaciones?. Submit → `useCrearSeguimiento`.
- [ ] **Step 3:** Botón "Generar alertas de revisión" (header, writer) → `useGenerarAlertasRevision` → toast con nº de alertas creadas (revisión ≤5 días).
- [ ] **Step 4: Test.** Validación condicional (cambio_esquema=true sin detalle bloquea); alta refetcha. Botón generar alertas dispara la mutation (handler MSW devuelve lista).
- [ ] **Step 5: Gate + commit.** `npm run test -- src/features/farmacos && npx tsc -b`.
```bash
git add frontend/src/features/farmacos
git commit -m "feat(farmacos): seguimiento de tratamiento (cambio esquema/disminución) + generar alertas revisión"
```

---

### Task 6: Verificación de cierre del ciclo

- [ ] **Step 1:** Gate completo desde `frontend/`: `npm run typecheck && npm run lint && npm run test && npm run build`. Cero errores de lint/tsc, build OK, todos los tests verdes.
- [ ] **Step 2:** Revisar que `/farmacos` ya no es placeholder y que el nav y los quick-actions ("Nueva receta") siguen coherentes con RBAC.
- [ ] **Step 3:** Actualizar memoria `sige-ui-base-v2.md` (marcar Ciclo 2 COMPLETO + notas de contrato/gaps). Commit final si aplica:
```bash
git commit -am "chore(farmacos): cierre ciclo 2 (gate verde)"
```
