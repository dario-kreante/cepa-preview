# SIGE — Ciclo 4: Evaluación de Puesto de Trabajo (EPT, EPIC-03) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Pasos con checkbox (`- [ ]`).

**Goal:** Portar el módulo **EPT** (Evaluación de Puesto de Trabajo) al `frontend/`, conectado al backend, reemplazando el placeholder, con el flujo completo: alta de caso, contactos, proceso y plazos (con estados de cumplimiento del backend).

**Architecture — caso-céntrico (NO lista):** A diferencia de Fármacos/Controles, el backend EPT **NO expone listado, ni búsqueda, ni endpoint por-ingreso, y `Vista360` NO incluye casos EPT**. La única forma de acceder a un caso es `GET /api/v1/casos-ept/{caso_id}`. Por lo tanto **no se puede portar la lista v2 con KPIs reales** (esos serían inventados). El módulo se construye **caso-céntrico**:
1. **Alta de caso** paciente-driven (busca paciente → resuelve `ingreso_id` primario vía `useVista360`, igual que Fármacos/Controles → crea el caso con los datos del trabajador). El caso recién creado queda **activo** en pantalla.
2. **Cargar un caso existente por `caso_id`** (campo de input + soporte de query param `?caso=`), única afordancia de la API para recuperar casos (p.ej. el `caso_id` proviene de una alerta `caso_tipo="ept"`).
3. **Workspace del caso activo**: detalle/edición del caso (PATCH), **contactos** (agregar correo), **proceso** (GET/POST/PATCH), **plazos** (GET/POST/PATCH con badges de estado de cumplimiento calculados en backend).
Referencia visual: `frontend/ui-base-v2/src/pages/EPT.tsx` (adaptar header/KPIs al caso activo; la tabla-lista NO es portable). Reusar el patrón de búsqueda paciente→ingreso de `features/farmacos`/`features/controles`.

**RBAC — writer EPT = solo `Administrativo`:** OJO, distinto del resto. `Coordinacion` y `Auditor` solo **leen** EPT; solo `Administrativo` escribe. `puedeEscribir()` (que incluye Coordinacion) NO sirve para gates de escritura EPT. Agregar helper `puedeEscribirEpt(rol) => rol === "Administrativo"` en `@/lib/rbac` y usarlo en todos los gates de escritura de este módulo.

**Tech Stack:** igual que Ciclos 1-3. Contratos (verificar nombres/campos exactos en `frontend/src/types/api.ts`):
- `POST /api/v1/casos-ept` → `CasoEptCreate` (`ingreso_id`, `mes`, `fecha_ingreso_ept`, `nombre_trabajador`, `rut_trabajador`, `region_trabajador`, `eista`, `factor_riesgo: FactorRiesgo`, `corresponde_ept` (def true), `razon_social?`, `unidad_cargo_horario?`) → `CasoEptRead`.
- `GET /api/v1/casos-ept/{caso_id}` → `CasoEptRead`. `PATCH /api/v1/casos-ept/{caso_id}` → `CasoEptUpdate` → `CasoEptRead` (incluye `estado: EstadoEpt`).
- `POST /api/v1/casos-ept/{caso_id}/contactos` → body `ContactoEptPayload` (`correo`) → `ContactoEptRead`. **No hay GET de contactos** (solo POST) → tras agregar, mostrar el correo devuelto/lista en sesión; nota de gap.
- `GET/POST/PATCH /api/v1/casos-ept/{caso_id}/proceso` → `ProcesoEptRead` (POST/PATCH con sus bodies — verificar si el POST usa `ProcesoEptCreate` o un payload sin `caso_ept_id`). Campos: `plazo_evid_denunciante?`, `plazo_insumos_empresa?`, `hay_testigos`, `testigos_cantidad`, `num_entrevistas`, `insumos_eista?`, `doc_incumplimiento?`, `observaciones?`. **GET proceso puede devolver 404** si no se ha creado → tratar como "sin proceso aún".
- `GET/POST/PATCH /api/v1/casos-ept/{caso_id}/plazos` → `PlazoEptRead` (`plazo_informe_ept?`, `plazo_portal_isl?`, `fecha_entrega_isl?`, `fecha_envio?`, **`estado_informe: EstadoCumplimiento`**, **`estado_entrega_isl: EstadoCumplimiento`** — calculados en backend, solo se muestran). **GET plazos puede devolver 404** si no existe.
- Enums: `FactorRiesgo = "carga"|"organizacion_trabajo"|"factores_psicosociales"|"violencia_laboral"|"condiciones_ergonomicas"|"otro"`; `EstadoEpt = "abierto"|"no_corresponde"|"cerrado"`; `EstadoCumplimiento = "en_plazo"|"por_vencer"|"vencido"|"cumplido"`. (Verificar nombres exactos / namespacing en types/api.ts.)

**Gaps conocidos (documentar, no inventar):**
- Sin listado/búsqueda/por-ingreso de casos EPT ni en Vista360 → módulo caso-céntrico; la lista v2 con KPIs no es portable. Navegación a casos existentes solo por `caso_id`.
- Contactos: solo POST (sin GET) → no se pueden re-listar tras recargar; se muestran los agregados en la sesión.

**Convención:** comandos desde `frontend/`. Commits locales, **no pushear**. Gate por cierre: `npm run typecheck && npm run lint && npm run test && npm run build`.

---

### Task 1: EPT — capa API + hooks + helper RBAC

**Files:** Create `frontend/src/features/ept/api.ts`, `hooks.ts`, `hooks.test.tsx`. Modify `frontend/src/lib/rbac.ts` (+ `rbac.test.ts`).

- [ ] **Step 1:** Verificar contratos en `frontend/src/types/api.ts` (CasoEpt*, ContactoEpt*, ProcesoEpt*, PlazoEpt*, enums; en especial los **request bodies** exactos de POST proceso/plazos/contactos). Sin `any`.
- [ ] **Step 2: rbac helper.** Agregar `export function puedeEscribirEpt(rol: Rol | null | undefined): boolean { return rol === "Administrativo"; }` en `rbac.ts`. Test en `rbac.test.ts`: Administrativo→true, Coordinacion→false, Auditor→false, null→false.
- [ ] **Step 3: api.ts** — funciones tipadas, exportar tipos:
  - `crearCaso(body: CasoEptCreate): Promise<CasoEptRead>` → `POST /api/v1/casos-ept`.
  - `obtenerCaso(casoId): Promise<CasoEptRead>` → `GET .../{caso_id}`.
  - `actualizarCaso(casoId, body: CasoEptUpdate): Promise<CasoEptRead>` → `PATCH .../{caso_id}`.
  - `agregarContacto(casoId, body /* ContactoEptPayload */): Promise<ContactoEptRead>` → `POST .../{caso_id}/contactos`.
  - `obtenerProceso(casoId): Promise<ProcesoEptRead | null>` → `GET .../{caso_id}/proceso` (**404 → null**).
  - `crearProceso(casoId, body): Promise<ProcesoEptRead>` / `actualizarProceso(casoId, body): Promise<ProcesoEptRead>`.
  - `obtenerPlazos(casoId): Promise<PlazoEptRead | null>` → `GET .../{caso_id}/plazos` (**404 → null**).
  - `crearPlazos(casoId, body): Promise<PlazoEptRead>` / `actualizarPlazos(casoId, body): Promise<PlazoEptRead>`.
  Mapear 409/422 a Error claro donde aplique.
- [ ] **Step 4: Test que falla (MSW global `server.use`, patrón `features/controles/hooks.test.tsx`):** handler `GET /api/v1/casos-ept/:caso_id` → 1 caso; render `useCaso(1)` → `isSuccess` + `data.id===1`. Caso 404 en `useProceso(1)` → `data===null` sin error. Run → FAIL.
- [ ] **Step 5: hooks.ts** — `useCaso(casoId)`, `useProceso(casoId)`, `usePlazos(casoId)` (useQuery, `enabled: !!casoId`, keys `["ept", casoId, ...]`); mutations `useCrearCaso()`, `useActualizarCaso()`, `useAgregarContacto()`, `useCrearProceso()`, `useActualizarProceso()`, `useCrearPlazos()`, `useActualizarPlazos()` con invalidación de `["ept", casoId, ...]`. Implementar → PASS.
- [ ] **Step 6: Gate + commit.** `npm run test -- src/features/ept src/lib/rbac.test.ts && npx tsc -b`.
```bash
git add frontend/src/features/ept frontend/src/lib/rbac.ts frontend/src/lib/rbac.test.ts
git commit -m "feat(ept): capa API tipada + hooks + helper RBAC puedeEscribirEpt (Administrativo)"
```

---

### Task 2: EPT — página (alta paciente-driven + cargar por caso_id + workspace del caso)

**Files:** Create `frontend/src/features/ept/EptPage.tsx`, `EptPage.test.tsx`, `NuevoCasoEptDialog.tsx`, `casoEptSchema.ts`. Modify `frontend/src/app/router.tsx` (reemplazar placeholder `/ept`).

- [ ] **Step 1:** `casoEptSchema.ts` (zod): `mes` (req), `fecha_ingreso_ept` (req fecha), `nombre_trabajador` (req), `rut_trabajador` (req), `region_trabajador` (req), `eista` (req), `factor_riesgo` (enum FactorRiesgo), `corresponde_ept` (bool, default true), `razon_social?`, `unidad_cargo_horario?`. NO `ingreso_id` (se inyecta del paciente).
- [ ] **Step 2:** `NuevoCasoEptDialog` (Dialog + RHF + zodResolver; mirror `features/controles/NuevoControlDialog.tsx`): campos del schema (selects nativos con labels amigables para `factor_riesgo`). Submit → `useCrearCaso()` con `{ ingreso_id, ...values }`. Al éxito, el `CasoEptRead` devuelto se vuelve el caso activo (callback `onCreated(caso)`).
- [ ] **Step 3:** `EptPage` — header "Seguimiento EPT" (subtítulo del v2) + acción "Nueva EPT" (solo `puedeEscribirEpt`; requiere paciente seleccionado para habilitar). Dos formas de activar un caso: (a) crear uno nuevo (paciente-driven: buscador reusando `useBuscarPacientes` + `useVista360` → `ingreso_id`); (b) **cargar por caso_id** (input numérico "Cargar caso N°" + soporte `?caso=` en la URL) → `useCaso(casoId)`. Mostrar el **detalle del caso activo** (trabajador, RUT, región, eista, factor de riesgo badge, `corresponde_ept`, **`estado: EstadoEpt`** badge, razón social, unidad/cargo) + botón "Editar caso" (PATCH vía dialog reutilizando el form, opcional/simple). Nota en código del gap (sin listado). Estados carga/empty/error/404.
- [ ] **Step 4:** Router: reemplazar `<ProximamentePage titulo="Seguimiento EPT" />` por `<EptPage />`.
- [ ] **Step 5: Test** (`EptPage.test.tsx`, MSW global, harness de `features/controles/*.test.tsx`): (a) crear caso paciente-driven → POST `/casos-ept` con `ingreso_id` correcto, se muestra el detalle del caso devuelto; (b) cargar por caso_id → GET `/casos-ept/{id}` y muestra detalle; RBAC: con rol **Coordinacion** (no Administrativo) NO aparece "Nueva EPT".
- [ ] **Step 6: Gate + commit.** `npm run test -- src/features/ept && npx tsc -b`.
```bash
git add frontend/src/features/ept frontend/src/app/router.tsx
git commit -m "feat(ept): página caso-céntrica (alta paciente-driven + cargar por caso_id + detalle/estado)"
```

---

### Task 3: EPT — proceso (panel + subform GET/POST/PATCH)

**Files:** Create `frontend/src/features/ept/ProcesoEptPanel.tsx`, `ProcesoEptDialog.tsx`, `procesoEptSchema.ts`. Modify `EptPage.tsx`.

- [ ] **Step 1:** `procesoEptSchema.ts` (zod): `plazo_evid_denunciante?` (fecha), `plazo_insumos_empresa?` (fecha), `hay_testigos` (bool, default false), `testigos_cantidad` (int ≥0, default 0), `num_entrevistas` (int ≥0, default 0), `insumos_eista?`, `doc_incumplimiento?`, `observaciones?`. (Si `hay_testigos=false`, `testigos_cantidad` puede ir 0 — no forzar, salvo regla backend; verificar.)
- [ ] **Step 2:** `ProcesoEptPanel` — consume `useProceso(casoId)`. Si `null`: empty state con CTA "Registrar proceso" (writer EPT). Si existe: mostrar plazos evidencia/insumos (fmtDate), testigos (sí/no + cantidad), nº entrevistas, insumos eista, doc incumplimiento, observaciones. Botón "Editar proceso".
- [ ] **Step 3:** `ProcesoEptDialog` (Dialog + RHF + zodResolver): crea (si no existe) vía `useCrearProceso()` o edita vía `useActualizarProceso()`; prefill cuando existe; checkbox `hay_testigos` (watch+setValue) muestra/relevant `testigos_cantidad`; inputs number con `setValueAs` (gotcha number↔string). Gate writer EPT.
- [ ] **Step 4: Test:** sin proceso (404) → empty + CTA; crear proceso → POST refetch muestra datos; editar → PATCH; validación number; RBAC (Coordinacion no ve acciones de escritura).
- [ ] **Step 5: Gate + commit.** `npm run test -- src/features/ept && npx tsc -b`.
```bash
git add frontend/src/features/ept
git commit -m "feat(ept): proceso del caso (testigos/entrevistas/plazos evidencia, GET/POST/PATCH)"
```

---

### Task 4: EPT — plazos (estado cumplimiento) + contactos

**Files:** Create `frontend/src/features/ept/PlazosEptPanel.tsx`, `PlazosEptDialog.tsx`, `plazosEptSchema.ts`, `ContactosEptPanel.tsx`. Modify `EptPage.tsx`.

- [ ] **Step 1:** `plazosEptSchema.ts` (zod): `plazo_informe_ept?` (fecha), `plazo_portal_isl?` (fecha), `fecha_entrega_isl?` (fecha), `fecha_envio?` (fecha). (`estado_informe`/`estado_entrega_isl` NO van en el form — los calcula el backend.)
- [ ] **Step 2:** `PlazosEptPanel` — consume `usePlazos(casoId)`. Si `null`: empty + CTA "Registrar plazos" (writer EPT). Si existe: mostrar las fechas (fmtDate) + **badges de `estado_informe` y `estado_entrega_isl`** (EstadoCumplimiento: en_plazo→info, por_vencer→warning, vencido→destructive, cumplido→success; labels amigables). Botón "Editar plazos".
- [ ] **Step 3:** `PlazosEptDialog` (crear/editar vía `useCrearPlazos()`/`useActualizarPlazos()`; prefill; inputs date). Gate writer EPT.
- [ ] **Step 4:** `ContactosEptPanel` — input correo (zod email) + botón "Agregar contacto" → `useAgregarContacto()`. Como **no hay GET de contactos**, mostrar los agregados en la sesión (lista local desde las respuestas) con nota del gap. Gate writer EPT.
- [ ] **Step 5: Test:** plazos null → empty+CTA; crear plazos → POST refetch muestra fechas + badges de estado; editar → PATCH; agregar contacto válido → POST y aparece en la lista de sesión; email inválido bloquea (spy no llamado); RBAC (Coordinacion no ve acciones de escritura).
- [ ] **Step 6: Gate + commit.** `npm run test -- src/features/ept && npx tsc -b`.
```bash
git add frontend/src/features/ept
git commit -m "feat(ept): plazos con estado de cumplimiento (backend) + contactos (agregar correo)"
```

---

### Task 5: Verificación de cierre del ciclo

- [ ] **Step 1:** Gate completo desde `frontend/`: `npm run typecheck && npm run lint && npm run test && npm run build`. Cero errores lint/tsc, build OK, tests verdes.
- [ ] **Step 2:** Revisar que `/ept` ya no es placeholder; nav + quick-actions coherentes con RBAC (EPT = Administrativo writer).
- [ ] **Step 3:** Actualizar memoria `sige-ui-base-v2.md` (marcar Ciclo 4 COMPLETO + notas contrato/gaps: caso-céntrico, sin listado, writer Administrativo, estados de cumplimiento backend).
