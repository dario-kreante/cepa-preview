# SIGE — Ciclo 1: Licencias médicas (EPIC-07) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Pasos con checkbox (`- [ ]`).

**Goal:** Portar el módulo **Licencias médicas** del prototipo v2 al `frontend/`, conectado al backend, con las mejoras del documento (GAF/EEAG, filtro reposo Parcial/Total, badge "Vence en", envío masivo ISL / por paciente), reemplazando el placeholder.

**Architecture:** Reusa la Fundación v2 (shell, design system, apiClient tipado, TanStack Query, MSW). El backend de licencias es **folio-driven** (no hay endpoint "listar todas"): la página busca por folio (o RUT→folio) y muestra el historial del folio (`GET /api/v1/licencias/folio/{folio}` → `LicenciasResponse {folio, historial: LicenciaRead[], dias_acumulados}`) con estilo de tabla v2 + filtros + acciones. Estilo de referencia: `frontend/ui-base-v2/src/pages/SimplePages.tsx` (componente Licencias).

**Tech Stack:** igual que Ciclo 0. Contratos (verificar nombres/campos exactos en `frontend/src/types/api.ts`):
- `POST /api/v1/licencias` → `LicenciaCreate` / `app__schemas__licencia__LicenciaRead`.
- `GET /api/v1/licencias/folio/{folio}` → `LicenciasResponse`.
- `GET /api/v1/ingresos/{ingreso_id}/licencias` → `LicenciaRead[]`; `.../licencias/acumulado` → `AcumuladoRead`.
- `PATCH /api/v1/licencias/{licencia_id}/anular` → `LicenciaAnularUpdate {observaciones}`.
- `PATCH /api/v1/licencias/{licencia_id}/isl` → `LicenciaISLUpdate {envio_isl: EstadoEnvioISL, fecha_envio_isl?, eeag_gaf?(1-100), observaciones?}`.
- `POST /api/v1/licencias/alertas/generar` → `AlertaLicenciaRead[]`.

**Gap conocido (documentar, no inventar):** no existe listado global ni filtro por región a nivel API de licencias. El "envío por región" del documento NO es soportable cross-paciente sin un endpoint de listado; se implementa **envío masivo sobre las licencias mostradas (scope del folio) con selección** ("envío por paciente"). Se deja nota para una mejora futura de backend.

**Convención:** comandos desde `frontend/`. Commits locales, no pushear. Gate por cierre: `npm run typecheck && npm run lint && npm run test && npm run build`.

---

### Task 1: Licencias — capa API + hooks

**Files:** Create `frontend/src/features/licencias/api.ts`, `frontend/src/features/licencias/hooks.ts`, `frontend/src/features/licencias/hooks.test.tsx`.

- [ ] **Step 1: Verificar contratos.** Leer en `frontend/src/types/api.ts` los campos exactos de `LicenciaCreate`, `app__schemas__licencia__LicenciaRead`, `LicenciasResponse`, `LicenciaISLUpdate`, `LicenciaAnularUpdate`, `AcumuladoRead`, `AlertaLicenciaRead`, y el enum `EstadoEnvioISL`. Anotar nombres reales (p.ej. `folio_lm`, `tipo_lm`, `tipo_reposo`, `fecha_inicio`, `fecha_termino`, `cantidad_dias`, `origen`, `eeag_gaf?`, `anulada`, `envio_isl`). Adaptar el código sin `any`.

- [ ] **Step 2: api.ts** — funciones tipadas sobre `api` (`@/lib/apiClient`):
  - `buscarLicenciasPorFolio(folio: string): Promise<LicenciasResponse>` → `GET /api/v1/licencias/folio/{folio}` (error 404 → devolver `{folio, historial: [], dias_acumulados: 0}` o lanzar y que el hook lo trate como "sin resultados").
  - `crearLicencia(body: LicenciaCreate)` → `POST /api/v1/licencias` (mapear 409/422 a Error con mensaje claro).
  - `anularLicencia(id: number, observaciones: string)` → `PATCH /api/v1/licencias/{licencia_id}/anular`.
  - `actualizarISL(id: number, body: LicenciaISLUpdate)` → `PATCH /api/v1/licencias/{licencia_id}/isl`.
  - `generarAlertasLicencias()` → `POST /api/v1/licencias/alertas/generar`.
  - `acumuladoPorIngreso(ingresoId: number)` → `GET /api/v1/ingresos/{ingreso_id}/licencias/acumulado`.
  Exportar los tipos (`LicenciaRead`, `LicenciaCreate`, `LicenciasResponse`, etc.).

- [ ] **Step 3: Test que falla (MSW global `server.use`).** `hooks.test.tsx`: con handler de `GET /api/v1/licencias/folio/:folio` devolviendo `{folio:"123", historial:[{id:1, folio_lm:"LM-1", tipo_lm:"1", tipo_reposo:"total", cantidad_dias:14, anulada:false}], dias_acumulados:14}`, renderizar `useLicenciasPorFolio("123")` y esperar `isSuccess` + `data.historial.length===1`. Run `npx vitest run src/features/licencias/hooks.test.tsx` → FAIL.

- [ ] **Step 4: hooks.ts** — `useLicenciasPorFolio(folio)` (useQuery, `enabled: folio.trim().length>0`), `useCrearLicencia()`, `useAnularLicencia()`, `useActualizarISL()`, `useGenerarAlertas()` (useMutation con invalidación de `["licencias", folio]`). Implementar. Run → PASS.

- [ ] **Step 5: Gate + commit.** `npm run test && npx tsc -b`.
```bash
git add frontend/src/features/licencias
git commit -m "feat(licencias): capa API tipada + hooks (folio search/alta/anular/ISL/alertas)"
```

---

### Task 2: Licencias — página lista (búsqueda por folio + tabla v2 + filtros + KPIs)

**Files:** Create `frontend/src/features/licencias/LicenciasPage.tsx`, `frontend/src/features/licencias/LicenciasPage.test.tsx`. Modify `frontend/src/app/router.tsx`.

- [ ] **Step 1: Página.** Portar el estilo del componente Licencias de `frontend/ui-base-v2/src/pages/SimplePages.tsx` adaptado a datos reales:
  - `PageHeader`: título "Licencias médicas" + subtítulo (cuenta del historial + total días acumulados del folio buscado) + botón "Nueva licencia" (abre dialog de Task 3; oculto para Auditor vía `puedeEscribir`).
  - `FiltersBar`: input búsqueda placeholder **"Buscar por folio o RUT"** (busca por folio; si parece RUT, intentar resolver a folio — si no hay endpoint RUT→folio, buscar solo por folio y notar el gap). Selects **Tipo LM** y **Reposo (Parcial/Total)** (mejora doc) + ISL estado, filtrando client-side sobre `historial`.
  - Estados: prompt cuando folio vacío ("Ingresa un folio para ver sus licencias."), "Buscando…", "Sin licencias para este folio.".
  - Tabla (estilo v2): columnas **Folio LM | Tipo | Reposo | Inicio | Fin | Días | GAF/EEAG | ISL | Estado | (acciones)** — usar campos reales de `LicenciaRead`. **Mejoras doc:** mostrar **GAF/EEAG** (`eeag_gaf`), y badge **"Vence en"** calculado desde `fecha_termino` (rojo <3 días, ámbar <7, verde si vigente, neutro si vencida/anulada). Estado: badge Vigente/Anulada/Finalizada.
  - Strip inferior: **días acumulados** (`dias_acumulados` del response) destacado (ámbar), con nota si `hay_solapamiento`/extra-sistema cuando se disponga del acumulado por ingreso.
  - KPIs (opcional, sobre el historial): total, vigentes, días acumulados, pendientes ISL.
  - Las acciones por fila (anular/ISL) y selección para envío masivo se añaden en Tasks 4–5; por ahora dejar la columna de acciones lista (botones deshabilitados o placeholders) y `onAnular`/`onISL` como props/handlers stub.

- [ ] **Step 2: Router.** Apuntar `/licencias` a `LicenciasPage` (reemplazar el `ProximamentePage` de licencias en `src/app/router.tsx`).

- [ ] **Step 3: Test componente (MSW).** Buscar un folio → MSW devuelve historial con 1 licencia → la tabla la muestra (folio_lm, días) y el badge "Vence en". Filtro Reposo=Total muestra solo totales. Placeholder correcto. Usar server global (`server.use`) + wrapper QueryClient/MemoryRouter/AuthProvider (token Coordinacion en tokenStore, patrón de Ingresos Task 9).

- [ ] **Step 4: Gate + commit.** `npm run test && npx tsc -b && npm run build`.
```bash
git add frontend/src/features/licencias frontend/src/app/router.tsx
git commit -m "feat(licencias): página lista v2 (búsqueda folio + GAF/EEAG + filtro reposo + vence-en)"
```

---

### Task 3: Alta de licencia (formulario)

**Files:** Create `frontend/src/features/licencias/AltaLicenciaDialog.tsx`, `frontend/src/features/licencias/licenciaSchema.ts`, test. Modify `LicenciasPage.tsx` (montar el dialog).

- [ ] **Step 1: licenciaSchema.ts (zod).** Campos de `LicenciaCreate` (verificar): `ingreso_id` (number, requerido — el alta cuelga de un ingreso; obtener del contexto del folio buscado o pedir folio→ingreso), `folio_lm?`, `tipo_lm` (enum real), `tipo_reposo` (enum: total/parcial), `fecha_inicio`, `fecha_termino`, `cantidad_dias` (number), `diagnostico`, `origen` (enum: sistema/extra_sistema). Validaciones: `fecha_termino >= fecha_inicio` (y reposo si aplica). `eeag_gaf?` 1–100 si se incluye en alta (si no, va por el PATCH ISL).

- [ ] **Step 2: Test que falla.** Render del dialog; enviar con `fecha_termino < fecha_inicio` → muestra error de coherencia y NO llama a la API (MSW spy). Run → FAIL.

- [ ] **Step 3: AltaLicenciaDialog.tsx.** `Dialog` shadcn con `react-hook-form + zodResolver`. Selects para enums (tipo_lm, tipo_reposo, origen). On submit → `useCrearLicencia().mutateAsync` → toast éxito + cierra + invalida `["licencias", folio]`; errores 409/422 → toast. Solo para escritura (Auditor no ve "Nueva licencia"). Implementar → test PASS.

- [ ] **Step 4: Montar en LicenciasPage** (botón "Nueva licencia" abre el dialog; precargar `ingreso_id` del folio en contexto si está disponible).

- [ ] **Step 5: Gate + commit.** `npm run test && npx tsc -b`.
```bash
git add frontend/src/features/licencias
git commit -m "feat(licencias): alta de licencia (form zod + coherencia de fechas)"
```

---

### Task 4: Acciones por fila — Anular + actualizar ISL

**Files:** Create `frontend/src/features/licencias/AnularLicenciaDialog.tsx`, `frontend/src/features/licencias/IslLicenciaDialog.tsx`, test. Modify `LicenciasPage.tsx`.

- [ ] **Step 1: AnularLicenciaDialog.** Dialog con textarea `observaciones` (requerido) → `useAnularLicencia(id, observaciones)` → toast + invalida. 
- [ ] **Step 2: IslLicenciaDialog.** Dialog con select `envio_isl` (`EstadoEnvioISL`: pendiente/enviado/rechazado), `fecha_envio_isl?` (date), `eeag_gaf?` (1–100), `observaciones?` → `useActualizarISL(id, body)` → toast + invalida.
- [ ] **Step 3: Wire en la tabla.** Botones por fila (icon-buttons) abren los dialogs con la licencia seleccionada. Ocultos para Auditor.
- [ ] **Step 4: Test.** Anular con observaciones llama al PATCH correcto (MSW captura body); ISL update envía `envio_isl` + `eeag_gaf`. Run hasta verde.
- [ ] **Step 5: Gate + commit.** 
```bash
git add frontend/src/features/licencias
git commit -m "feat(licencias): acciones anular + actualizar ISL (GAF/EEAG)"
```

---

### Task 5: Envío masivo ISL + generar alertas

**Files:** Modify `LicenciasPage.tsx`. Create test.

- [ ] **Step 1: Selección de filas.** Checkboxes por fila (shadcn `checkbox`) + "seleccionar todas" sobre el historial mostrado. Estado de selección en la página.
- [ ] **Step 2: Envío masivo ISL ("envío por paciente").** Botón "Envío masivo ISL" (header) → para cada licencia seleccionada, `useActualizarISL` con `envio_isl="enviado"` + `fecha_envio_isl=hoy` (secuencial o `Promise.all`); toast con resumen; invalida. Nota visible/comentario: el "envío por región" cross-paciente requiere endpoint de listado por región (gap backend) — fuera de alcance.
- [ ] **Step 3: Generar alertas.** Botón "Generar alertas de vencimiento" → `useGenerarAlertas()` → toast con nº de alertas generadas. (Solo escritura.)
- [ ] **Step 4: RBAC.** Todas estas acciones ocultas para Auditor.
- [ ] **Step 5: Test.** Seleccionar 2 filas + envío masivo → 2 PATCH ISL (MSW cuenta). Run hasta verde.
- [ ] **Step 6: Gate + commit.**
```bash
git add frontend/src/features/licencias
git commit -m "feat(licencias): envío masivo ISL (selección) + generar alertas de vencimiento"
```

---

### Task 6: Verificación del Ciclo 1 + QA

**Files:** ninguno.

- [ ] **Step 1: Gate.** `npm run typecheck && npm run lint && npm run test && npm run build` → verde.
- [ ] **Step 2: QA preview.** Levantar dev server; navegar a Licencias (requiere sesión → si backend sin CORS, validar al menos render del placeholder→página, estados vacíos y estilos; la búsqueda real necesita backend con CORS). Capturar evidencia posible.
- [ ] **Step 3: Commit final si queda algo.** `git add -A && git commit -m "chore(licencias): Ciclo 1 verificado" || echo "nada"`.

---

## Cobertura (programa ↔ Tasks)

| Requisito (Licencias) | Task |
|---|---|
| Lista estilo v2 + búsqueda folio | 2 |
| GAF/EEAG visible (mejora doc) | 2, 4 |
| Filtro reposo Parcial/Total (mejora doc) | 2 |
| Badge "Vence en" | 2 |
| Días acumulados | 1, 2 |
| Alta de licencia (coherencia fechas) | 3 |
| Anular | 4 |
| Actualizar ISL | 4 |
| Envío masivo ISL / por paciente (mejora doc) | 5 |
| Generar alertas de vencimiento | 5 |
| RBAC (Auditor solo lectura) | 2–5 |
| Gate + QA | 6 |

## Notas
- **Folio-driven:** la página gira en torno a un folio (no hay listado global). "Envío por región" del doc no es soportable sin endpoint de listado → documentado como gap; se entrega envío masivo por selección (scope del folio).
- Reusar convenciones de testing ([[frontend-testing-conventions]]) y el patrón de wrapper con AuthProvider de Ingresos.
- Componentes UI de v2 ya disponibles (`checkbox`, `dialog`, `select`, `badge`, `tabs`). Estilo de tabla: portar de `ui-base-v2/src/pages/SimplePages.tsx`.
