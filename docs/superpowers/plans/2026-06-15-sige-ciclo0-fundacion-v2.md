# SIGE — Ciclo 0: Fundación v2 (design system + shell + branding + Ingresos) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development para implementar este plan task-por-task. Los pasos usan checkbox (`- [ ]`).

**Goal:** Portar el design system, el shell y el módulo Ingresos del prototipo **v2** (`cepa-preview-v2`) al `frontend/` real, conectados al backend, rebranded **SIGE**, reemplazando el diseño/Ingresos de la Fundación.

**Architecture:** El prototipo v2 ya está en el stack del `frontend/` (Vite 8 + React 19 + TS 6 + Tailwind v4 + shadcn + recharts + lucide). Se **vendoriza** la fuente de v2 dentro del repo como referencia estable, se portan tokens + componentes + charts + shell, se cablea a hooks tipados (TanStack Query sobre el apiClient existente), y se refactoriza Ingresos al patrón lista + **PatientSheet** (drawer con 5 tabs). Auth/router/RBAC de la Fundación se conservan.

**Tech Stack:** Vite 8, React 19, TS 6, Tailwind v4, shadcn/ui, **recharts 3**, lucide-react, @radix-ui (avatar/checkbox/dropdown-menu/popover/scroll-area/select/switch/tabs/tooltip/separator/dialog/label/slot), react-router-dom 7, @tanstack/react-query 5, react-hook-form + zod, MSW 2, Vitest 2.

**Referencia de diseño:** `docs/superpowers/specs/2026-06-15-sige-frontend-programa-design.md`. Fuente del prototipo v2 clonada en `/tmp/cepa-v2-src` (repo privado `dario-kreante/cepa-preview-v2`, branch `main`) — se vendoriza en Task 1.

**Convención:** comandos desde `frontend/` con `npm …`. No pushear (commits locales). Gate por cierre: `npm run typecheck && npm run lint && npm run test && npm run build`.

---

### Task 1: Vendorizar la fuente del prototipo v2 (referencia estable en repo)

**Files:** Create `frontend/ui-base-v2/**` (copia de la fuente v2, solo referencia — excluida de build/lint/tsc). Modify `frontend/tsconfig.app.json`, `frontend/eslint.config.js`, `frontend/.gitignore` si aplica.

- [ ] **Step 1: Copiar la fuente v2.** Si `/tmp/cepa-v2-src` no existe, re-clonar: `gh auth switch --user dario-kreante >/dev/null 2>&1; T=$(gh auth token); git clone "https://dario-kreante:$T@github.com/dario-kreante/cepa-preview-v2.git" /tmp/cepa-v2-src`. Luego copiar SOLO la fuente relevante:
```bash
mkdir -p "frontend/ui-base-v2"
cp -R /tmp/cepa-v2-src/src "frontend/ui-base-v2/src"
cp /tmp/cepa-v2-src/index.html "frontend/ui-base-v2/index.html"
cp /tmp/cepa-v2-src/package.json "frontend/ui-base-v2/package.json"
```
Expected: `frontend/ui-base-v2/src/{pages,components,data,lib,index.css,App.tsx}` presentes.

- [ ] **Step 2: Excluir de tsc.** En `frontend/tsconfig.app.json`, añadir `"ui-base-v2"` al array `exclude` (crear `"exclude": ["ui-base-v2"]` si no existe). Esto evita que el código de referencia (con imports `@/...` que no resuelven aquí) rompa el typecheck.

- [ ] **Step 3: Excluir de eslint.** En `frontend/eslint.config.js`, añadir `"ui-base-v2"` a `globalIgnores([...])` (o al `ignores` del config). Confirmar que `npm run lint` no recorre `ui-base-v2`.

- [ ] **Step 4: Verificar gate intacto.** Run: `npm run typecheck && npm run lint && npm run build` → todo verde (la referencia no afecta el build real).

- [ ] **Step 5: Commit.**
```bash
git add frontend/ui-base-v2 frontend/tsconfig.app.json frontend/eslint.config.js
git commit -m "chore(sige): vendorizar fuente del prototipo v2 como referencia de UI"
```

---

### Task 2: Portar tokens de diseño v2 (OKLCH teal) a index.css

**Files:** Modify `frontend/src/index.css`.

- [ ] **Step 1: Leer la fuente.** Leer `frontend/ui-base-v2/src/index.css` (tokens v2: `@theme`/`:root` con `--primary` teal OKLCH, `--background/foreground/card/muted/border`, `--success/--warning/--info/--destructive`, `--brand-50..900`, `--chart-1..5`, `--sidebar-*`, `--radius`, fuentes Inter + JetBrains Mono, `.mono`, `.dark`). Leer también el `index.css` actual de `frontend/src/` para ver el esquema Tailwind v4 + shadcn (`@import "tailwindcss"`, `@theme inline` mapeando `--color-* : var(--*)`).

- [ ] **Step 2: Fusionar.** Reescribir `frontend/src/index.css` para usar los **tokens v2** (paleta teal + brand + chart + sidebar + radius + tipografías) MANTENIENDO el patrón Tailwind v4 (`@import "tailwindcss"`) y el bloque `@theme inline` que mapea las variables shadcn (`--color-background`, `--color-primary`, `--color-border`, `--color-sidebar*`, `--color-chart-1..5`, etc.) para que las utilidades (`bg-primary`, `text-foreground`, `bg-sidebar`, `fill-chart-1`) resuelvan. Incluir las fuentes (Inter, JetBrains Mono) y la clase `.mono`. Portar `.dark` aunque no se active (paridad con v2).

- [ ] **Step 3: Fuentes en index.html.** Asegurar en `frontend/index.html` los `<link>` de Google Fonts para Inter **y JetBrains Mono** (la Fundación ya tiene Inter; añadir JetBrains Mono). Título queda para Task 5.

- [ ] **Step 4: Verificar.** Run: `npm run build` → ok. (Validación visual en Task 11.)

- [ ] **Step 5: Commit.**
```bash
git add frontend/src/index.css frontend/index.html
git commit -m "feat(sige): portar tokens de diseño v2 (paleta teal OKLCH, brand/chart/sidebar)"
```

---

### Task 3: Dependencias + componentes shadcn/charts de v2

**Files:** Modify `frontend/package.json` (+ lock). Create/replace `frontend/src/components/ui/*`, `frontend/src/components/charts/*`. Modify `frontend/src/lib/utils.ts` si v2 añade helpers.

- [ ] **Step 1: Instalar deps que usa v2 y faltan.** Desde `frontend/` (con `.npmrc legacy-peer-deps` ya presente):
```bash
npm install recharts@^3 tw-animate-css@^1 \
  @radix-ui/react-avatar @radix-ui/react-checkbox @radix-ui/react-dropdown-menu \
  @radix-ui/react-popover @radix-ui/react-scroll-area @radix-ui/react-separator \
  @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-tooltip
```
(react-router, query, radix dialog/select/label/slot, lucide, cva, clsx, tailwind-merge ya están de la Fundación.)

- [ ] **Step 2: Copiar componentes ui de v2.** Copiar desde `frontend/ui-base-v2/src/components/ui/` a `frontend/src/components/ui/` los que faltan o difieren: `badge.tsx` (con variants success/warning/info/purple/neutral/outline), `button-group.tsx`, `donut.tsx`, `tabs.tsx`, `avatar.tsx`, `separator.tsx`. Para componentes ya existentes en la Fundación (`button`, `card`, `input`, `dialog`, `label`, `select`, `sonner`, `form`, `table`), comparar: si v2 difiere de forma relevante (p.ej. `card` con `rounded-xl shadow-xs`, `dialog` con `Sheet side=right`), **adoptar la versión v2** (la UI debe ser idéntica a v2). Añadir `switch.tsx`, `checkbox.tsx`, `dropdown-menu.tsx`, `popover.tsx`, `scroll-area.tsx`, `tooltip.tsx` de v2. Mantener imports a `@/lib/utils`.

- [ ] **Step 3: Sheet (drawer derecho).** Confirmar que el `dialog.tsx` resultante exporta el patrón `Sheet`/`SheetContent side="right"` que usa `PatientSheet` de v2 (revisar `frontend/ui-base-v2/src/components/ui/dialog.tsx` y `pages/PatientSheet.tsx`). Si v2 implementa Sheet dentro de `dialog.tsx`, portarlo tal cual.

- [ ] **Step 4: Charts wrappers.** Crear `frontend/src/components/charts/` con wrappers recharts tematizados (Area, Bar, Pie/donut) replicando los usados por `Dashboard.tsx`/`Reportes.tsx` de v2 (colores `var(--chart-1..5)`, `ResponsiveContainer`, ejes con CSS vars). Puede portarse el `donut.tsx` SVG custom tal cual a `components/ui/donut.tsx` (Step 2). Mantener los charts recharts encapsulados aquí para reuso en Dashboard/Reportería (ciclos futuros).

- [ ] **Step 5: Verificar.** Run: `npx tsc -b` y `npm run build` → sin errores. Si algún componente v2 usa una util/format que no existe (`fmtDate`, `formatRut` en `ui-base-v2/src/lib/utils.ts`), portar esas funciones a `frontend/src/lib/utils.ts` con implementación real (fecha DD-MM-YYYY ↔ ISO; formateo de RUT con puntos y guion).

- [ ] **Step 6: Commit.**
```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components frontend/src/lib/utils.ts
git commit -m "feat(sige): componentes shadcn v2 + charts recharts + utils de formato"
```

---

### Task 4: Alertas y Tareas — capa API + hooks (para el shell)

**Files:** Create `frontend/src/features/alertas/api.ts`, `frontend/src/features/alertas/hooks.ts`, `frontend/src/features/alertas/hooks.test.tsx`.

- [ ] **Step 1: api.ts tipado.** Funciones sobre el `api` client: `listarAlertas()` → `GET /api/v1/alertas` (tipo `components["schemas"]["AlertaRead"]`); `actualizarAlerta(id, estado)` → `PATCH /api/v1/alertas/{alerta_id}`; `listarTareas()` → `GET /api/v1/tareas` (`TareaItemRead`). Verificar los nombres exactos de schema/paths en `frontend/src/types/api.ts` y adaptar (sin `any`).

- [ ] **Step 2: Test que falla (MSW).** `hooks.test.tsx`: con `server.use(http.get(\`${BASE}/api/v1/alertas\`, () => HttpResponse.json([...])))`, renderizar `useAlertas()` y esperar `isSuccess` + data. Run: `npx vitest run src/features/alertas/hooks.test.tsx` → FAIL.

- [ ] **Step 3: hooks.ts.** `useAlertas()`, `useTareas()` (useQuery), `useActualizarAlerta()` (useMutation con invalidación de `["alertas"]`). Implementar. Run de nuevo → PASS.

- [ ] **Step 4: Full suite + tsc.** `npm run test && npx tsc -b` → verde.

- [ ] **Step 5: Commit.**
```bash
git add frontend/src/features/alertas
git commit -m "feat(sige): alertas+tareas API/hooks (consumo del shell)"
```

---

### Task 5: Branding SIGE

**Files:** Modify `frontend/index.html` (title), y se aplica en los componentes del shell/login al construirlos (Tasks 6, 9). Create `frontend/src/lib/brand.ts`.

- [ ] **Step 1: brand.ts.** Crear constantes: `export const APP_NAME = "SIGE";` `export const APP_INITIAL = "S";` `export const APP_SUBTITLE = "Universidad de Talca";`. Estas se usan en Sidebar/Login en vez de hardcodear "CEPA".

- [ ] **Step 2: title.** En `frontend/index.html` cambiar `<title>` a `SIGE · Universidad de Talca`.

- [ ] **Step 3: Commit.**
```bash
git add frontend/index.html frontend/src/lib/brand.ts
git commit -m "feat(sige): branding SIGE (constantes de marca + title)"
```

---

### Task 6: Shell v2 (Sidebar + Topbar + AlertsPanel + AppShell)

**Files:** Create `frontend/src/components/shell/{Sidebar,Topbar,AlertsPanel}.tsx`. Modify/replace `frontend/src/app/shell/AppShell.tsx`. Modify `frontend/src/app/shell/nav.ts`.

- [ ] **Step 1: nav.ts.** Definir la estructura de v2: secciones General/Clínico/Operación con items {to, label, icon (lucide), navKey, badgeKey?}. Rutas: `/`(dashboard), `/ingresos`, `/licencias`, `/farmacos`, `/controles`, `/ept`, `/reintegro`, `/auditoria`, `/agenda`, `/reportes`. Marcar `activo` los que existirán (Ingresos en este ciclo; los demás muestran placeholder "Próximamente" hasta su ciclo).

- [ ] **Step 2: Sidebar.tsx.** Portar `frontend/ui-base-v2/src/components/shell/Sidebar.tsx`: reemplazar la marca por `APP_NAME/APP_INITIAL/APP_SUBTITLE` (brand.ts); nav con `NavLink` de react-router (activo por `isActive`), secciones/badges; footer con `useAuth()` (nombre/email del JWT + logout real); colapsable. Badges de Licencias/EPT desde conteo de alertas (placeholder 0 o derivado de `useAlertas()` por módulo).

- [ ] **Step 3: Topbar.tsx.** Portar el de v2: título+breadcrumb por ruta (mapa por pathname); pills "N activos"/"N críticas" (placeholder hasta el módulo Dashboard — usar 0/length de alertas críticas de `useAlertas()`); campana toggle del AlertsPanel (estado en AppShell).

- [ ] **Step 4: AlertsPanel.tsx.** Portar el de v2: tabs Todas/Críticas/Próximas/Info; render de `useAlertas()` + `useTareas()`; item → `navigate(\`/ingresos?folio=...\`)` o abrir Ficha (definir: navega a Ingresos con query folio que abre el PatientSheet); quick actions (Nuevo ingreso→`/ingresos/nuevo`; Registrar licencia/Nueva receta → deshabilitados hasta su ciclo). Fecha dinámica (`new Date`).

- [ ] **Step 5: AppShell.tsx.** Componer `grid` Sidebar | (Topbar + `<Outlet/>`) | AlertsPanel (toggle). Estado `alertsHidden`, `sidebarCollapsed`. RBAC: quick-actions de escritura ocultas para Auditor (`puedeEscribir`).

- [ ] **Step 6: Verificar.** `npx tsc -b && npm run build` → ok.

- [ ] **Step 7: Commit.**
```bash
git add frontend/src/components/shell frontend/src/app/shell
git commit -m "feat(sige): shell v2 (sidebar 3 secciones + topbar + panel alertas/tareas)"
```

---

### Task 7: Router por NavKey + placeholders de módulos

**Files:** Modify `frontend/src/app/router.tsx`. Create `frontend/src/features/_placeholder/ProximamentePage.tsx`.

- [ ] **Step 1: ProximamentePage.tsx.** Componente simple: PageHeader con el nombre del módulo + texto "Módulo en construcción". Acepta `titulo` por prop.

- [ ] **Step 2: Rutas.** Reescribir `AppRoutes`: dentro de `ProtectedRoute`+`AppShell`, rutas: `/`→DashboardPlaceholder, `/ingresos`→Ingresos (Task 10), `/ingresos/nuevo`→Alta (protegida escritura), `/licencias`/`/farmacos`/`/controles`/`/ept`/`/reintegro`/`/auditoria`/`/agenda`/`/reportes`→`<ProximamentePage titulo=…/>`. `*`→redirect `/`. Mantener `/login` fuera del shell. Conservar guards RBAC.

- [ ] **Step 3: Verificar guard test.** El test existente `router.test.tsx` (redirige a /login sin sesión) debe seguir verde. Run: `npm run test`.

- [ ] **Step 4: Commit.**
```bash
git add frontend/src/app/router.tsx frontend/src/features/_placeholder
git commit -m "feat(sige): rutas por módulo + placeholders 'Próximamente'"
```

---

### Task 8: Restyle Login a v2 (SIGE)

**Files:** Modify `frontend/src/features/auth/LoginPage.tsx`.

- [ ] **Step 1: Restyle.** Mantener la lógica existente (useAuth.login, error, enviando). Aplicar estética v2: fondo teal/gradiente, card shadcn v2, logo "S" + `APP_NAME` (brand.ts), inputs/labels shadcn v2, botón primary teal. Sin cambiar IDs (`#u`, `#p`) ni accesibilidad (labels Usuario/Contraseña, `role="alert"`).

- [ ] **Step 2: Verificar.** `npx tsc -b && npm run build` → ok. (Visual en Task 11.)

- [ ] **Step 3: Commit.**
```bash
git add frontend/src/features/auth/LoginPage.tsx
git commit -m "feat(sige): login con estética v2 + branding SIGE"
```

---

### Task 9: Ingresos — lista v2 (reemplaza BuscarPage)

**Files:** Create `frontend/src/features/ingresos/IngresosListaPage.tsx`. Modify `frontend/src/features/ingresos/hooks.ts` (si hace falta filtro), router. Delete/replace `BuscarPage.tsx`. Modify/extend tests.

- [ ] **Step 1: Página lista.** Portar la estructura de `frontend/ui-base-v2/src/pages/Ingresos.tsx` (header con conteo + "Nuevo ingreso"; filtros: búsqueda con placeholder **"Buscar por RUT, folio o nombre"**, Estado, Región, Derivación; tabla con columnas Folio/Paciente[avatar+edad·género·email]/Estado[StateDot]/Diagnóstico[+ICD]/RUT/Región/Derivación/Ingreso/acciones; paginación). Cablear a `useBuscarPacientes(q)` (debounce de la búsqueda). Campos que el backend no provea (edad/género/email/diagnóstico si difieren de `PacienteRead`) → mostrar lo disponible; verificar `PacienteRead` en `types/api.ts` y mapear (sin inventar). Fila → abre PatientSheet (Task 10) vía estado/route `?folio=` o `/ingresos/:id`.

- [ ] **Step 2: RBAC.** "Nuevo ingreso" oculto para Auditor (`puedeEscribir`).

- [ ] **Step 3: Test.** Test de componente: con MSW devolviendo pacientes, la tabla los lista y filtra; placeholder correcto. Run hasta verde.

- [ ] **Step 4: Router.** Apuntar `/ingresos` a `IngresosListaPage`. Quitar la antigua `BuscarPage` de las rutas.

- [ ] **Step 5: Verificar + Commit.** `npm run test && npx tsc -b`.
```bash
git add frontend/src/features/ingresos frontend/src/app/router.tsx
git commit -m "feat(sige): Ingresos lista estilo v2 (filtros + tabla + placeholder de búsqueda)"
```

---

### Task 10: Ficha 360 = PatientSheet (drawer 5 tabs)

**Files:** Create `frontend/src/features/ingresos/PatientSheet.tsx`. Modify `IngresosListaPage.tsx` (apertura), `hooks.ts` (vista360 + dimensiones), router. Delete/replace `Vista360Page.tsx`. Tests.

- [ ] **Step 1: Hooks de dimensiones.** Asegurar/añadir hooks: `useVista360(id)` (existe), y para los tabs: licencias por ingreso (`GET /api/v1/ingresos/{id}/licencias`), recetas/esquema (`/registro-farmacologico/{ingreso_id}/...`), controles (`/controles-medicos/por-ingreso/{ingreso_id}`), observaciones (audit-log). Crear funciones api + hooks mínimos (solo lectura) verificando paths/schemas en `types/api.ts`.

- [ ] **Step 2: PatientSheet.tsx.** Portar `frontend/ui-base-v2/src/pages/PatientSheet.tsx`: Sheet derecho, header gradiente (avatar+nombre+folio+RUT+región+badges), 5 tabs **Resumen/Licencias/Fármacos/Controles/Observaciones** con el detalle completo (estilo Variante 1, mejora del doc). Reemplazar la data mock por los hooks reales; dimensiones vacías del backend → estado "pendiente". Acciones del header (Editar/Nueva licencia/Agendar control) → deshabilitadas o enrutadas donde aplique; ocultas a Auditor.

- [ ] **Step 3: Apertura desde la lista.** En `IngresosListaPage`, clic en fila abre el PatientSheet (estado local con el `id`/`folio`, o sincronizado a `?folio=` para deep-link desde el AlertsPanel).

- [ ] **Step 4: Reemplazar Vista360Page.** Quitar `Vista360Page` de rutas; el detalle ahora es el drawer. Mantener `/pacientes/:id` solo si se quiere deep-link (opcional: que abra la lista con el sheet abierto). 

- [ ] **Step 5: Tests.** Test: abrir el sheet muestra el nombre del paciente y los tabs; tab Licencias lista las del backend (MSW). Ajustar/мigrar el test de `Vista360Page` al nuevo patrón. Run hasta verde.

- [ ] **Step 6: Verificar + Commit.** `npm run test && npx tsc -b && npm run build`.
```bash
git add frontend/src/features/ingresos frontend/src/app/router.tsx
git commit -m "feat(sige): Ficha 360 PatientSheet (drawer 5 tabs) reemplaza Vista360"
```

---

### Task 11: Verificación integral del Ciclo 0 + QA preview

**Files:** ninguno nuevo.

- [ ] **Step 1: Gate.** Desde `frontend/`: `npm run typecheck && npm run lint && npm run test && npm run build` → todo verde.

- [ ] **Step 2: QA preview.** Levantar el dev server (preview tools, config `frontend`), validar visualmente: Login SIGE (teal), shell v2 (sidebar 3 secciones + topbar + panel alertas), navegación a placeholders, Ingresos lista (filtros + tabla v2), apertura del PatientSheet con tabs. Capturar evidencia (screenshots). Nota: login real requiere backend con CORS desplegado; validar render + interacción (la búsqueda usa MSW solo en tests, en preview pega a staging — puede requerir CORS).

- [ ] **Step 3: Commit final si queda algo.**
```bash
git add -A && git commit -m "chore(sige): Ciclo 0 (fundación v2) verificado" || echo "nada que commitear"
```

---

## Cobertura (spec ↔ Tasks)

| Requisito del programa (Ciclo 0) | Task(s) |
|---|---|
| Vendorizar fuente v2 (referencia estable) | 1 |
| Tokens de diseño v2 (teal OKLCH, brand/chart/sidebar) | 2 |
| Componentes shadcn v2 + charts recharts + utils formato | 3 |
| Alertas/Tareas para el shell | 4 |
| Branding SIGE | 5, 6, 8 |
| Shell v2 (sidebar/topbar/panel alertas) | 6 |
| Rutas por NavKey + placeholders | 7 |
| Login restyle v2 | 8 |
| Ingresos lista v2 + placeholder búsqueda (mejora doc) | 9 |
| Ficha 360 PatientSheet drawer (detalle completo, mejora doc) | 10 |
| Gate verde + QA preview | 11 |

## Notas

- **Porte fiel:** cuando un componente/página de v2 exista en `frontend/ui-base-v2/`, **copiar y adaptar** (no re-autorear) — la UI debe quedar idéntica a v2. Adaptaciones permitidas: imports, reemplazo de `seed.ts` por hooks reales, branding SIGE, RBAC, react-router.
- **Contratos reales:** los campos de v2 (mock) pueden no coincidir con los schemas del backend (`PacienteRead`, etc.). Verificar siempre en `frontend/src/types/api.ts` y mapear lo disponible; los gaps conocidos del backend se muestran como "pendiente/—" (no inventar campos).
- **Convenciones de testing** de la Fundación (server MSW único, wrapper de fetch centralizado): ver memoria `frontend-testing-conventions`.
- Módulos restantes (Licencias, Fármacos, Controles, EPT, Reintegro, Auditoría, Dashboard, Reportería, Agenda) = ciclos siguientes, cada uno spec breve → plan → impl, reusando esta Fundación v2.
```
