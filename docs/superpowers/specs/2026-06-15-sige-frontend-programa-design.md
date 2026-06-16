# Diseño — Programa frontend SIGE (port del prototipo v2, conectado al backend)

> **Estado:** aprobado (2026-06-15) — el usuario instruyó "documenta las nuevas specs al completo y arranca".
> Supersede el roadmap previo. Base UI = prototipo **v2** (`dario-kreante/cepa-preview-v2`, "Variante 2"
> del documento *Revisión variantes prototipo SIGE*). Producto rebranded a **SIGE**. Backend intacto.

## Contexto y decisión

El stakeholder revisó dos variantes de prototipo (doc *Revisión variantes prototipo SIGE.docx*) y **eligió la
Variante 2** (`cepa-preview-v2`) como base UI por su claridad, orden y distribución, con la petición de
incorporar varias fortalezas de la Variante 1. La Fundación frontend ya entregada (login + shell simple +
módulo Ingresos page-based, rama `claude/frontend-integracion`) se **rehace** sobre el diseño v2.

**Hecho habilitante:** el prototipo v2 ya está construido en el **stack exacto** del `frontend/` real
(Vite 8 + React 19 + TS 6 + Tailwind v4 + shadcn/ui + **recharts** + lucide). Por tanto el trabajo NO es
rediseñar, sino **portar** los componentes/páginas de v2 al `frontend/` y **cablearlos al backend real**
(apiClient tipado + TanStack Query), conservando router + auth JWT + RBAC, con rebrand a SIGE y las mejoras
del documento.

**Objetivo del programa:** entregar las **10 pantallas de v2** completamente funcionales contra el backend,
con UI idéntica a v2 + mejoras del doc, rebranded SIGE, reusando la Fundación (auth, cliente API, testing, CI).

## Arquitectura

Se mantiene `frontend/` (monorepo junto a `backend/`). Se **incorpora el design system de v2** y se reescriben
shell y páginas:

```
frontend/src/
  main.tsx                      # providers (QueryClient + AuthProvider + Router) — existente
  index.css                     # TOKENS v2 (OKLCH teal, brand-50..900, chart-1..5, sidebar-*) — REEMPLAZA tokens actuales
  components/
    ui/                         # shadcn — alinear/añadir a v2: button, badge(+variants success/warning/info/purple/neutral),
                                #   card, dialog(+Sheet side=right), tabs, avatar, input, separator, button-group, switch, checkbox,
                                #   dropdown-menu, popover, scroll-area, tooltip, select, label, donut(custom), sonner, form
    charts/                     # wrappers recharts (Area, Bar, Pie/donut) tematizados con chart-1..5
    shell/
      AppShell.tsx              # layout: Sidebar | main(Topbar + Outlet) | AlertsPanel
      Sidebar.tsx               # 3 secciones (General/Clínico/Operación) + badges + colapsable + footer usuario (de auth)
      Topbar.tsx                # título+breadcrumb por ruta, pills KPI (dashboard), campana→AlertsPanel
      AlertsPanel.tsx           # tabs Todas/Críticas/Próximas/Info; alertas+tareas reales; quick actions
  lib/                          # apiClient, auth, rbac, queryClient, rut, utils, fmt(date/rut) — existente + fmt reales
  features/
    <modulo>/                   # api.ts (tipado) + hooks.ts + páginas + esquemas zod + componentes
  app/router.tsx                # rutas por NavKey + guards RBAC; PatientSheet como ruta/estado
```

**Branding SIGE:** nombre de producto "SIGE" (logo letra "S", marca teal v2), subtítulo institución
("Universidad de Talca"), `<title>` y textos. Email/nombre de usuario del JWT (no hardcode). `Sistema CEPA`→`SIGE`.

**Principio de aislamiento:** cada `features/<modulo>` encapsula API+hooks+UI; `lib/` y `components/` son
compartidos y no conocen módulos. El shell consume auth + alertas/tareas; las páginas consumen sus hooks.

## Design system (de v2)

- **Tokens** (`index.css`): paleta OKLCH teal — `--primary: oklch(0.56 0.10 185)`, `--background/foreground/card/
  muted/border`, semánticos `--success/--warning/--info/--destructive`, escala `--brand-50..900`, `--chart-1..5`,
  tokens `--sidebar-*`, `--radius: 0.625rem`. Tipografía **Inter** (UI) + **JetBrains Mono** (`.mono`: RUT, folios,
  fechas, números). Reemplaza la paleta brand/ink actual de la Fundación.
- **Componentes shadcn** alineados a v2 (variants de `Badge`: success/warning/info/purple/neutral; `Sheet`
  side=right; `ButtonGroup`; `Donut` SVG custom). Charts vía **recharts** (Area/Bar/Pie-donut) tematizados.
- Densidad/acento opcionales de v2 quedan como mejora futura (no MVP).

## Shell (de v2)

- **Sidebar** (260px / 64px colapsado): secciones **General** (Dashboard), **Módulos clínicos** (Ingresos,
  Licencias [badge n], Fármacos, Controles, EPT [badge n], Reintegro, Auditoría), **Operación** (Agendamiento,
  Reportería). Badges = conteos reales de alertas por módulo. Footer = usuario del JWT + logout. Buscador lateral.
- **Topbar** (h-14): título + breadcrumb por ruta; pills "N activos"/"N críticas" desde dashboard real; campana
  toggle del panel.
- **AlertsPanel** (320px): tabs Todas/Críticas/Próximas/Info; lista de **alertas** (`GET /api/v1/alertas`) +
  **tareas** (`GET /api/v1/tareas`); item → navega al caso (Ficha 360 por folio); quick actions (Nuevo ingreso,
  Registrar licencia, Nueva receta). Fecha dinámica.

## Mapa de pantallas v2 ↔ backend ↔ mejoras del doc

Cada módulo: lista con filtros + (KPIs) + formularios alta/edición + acciones, **idéntico a v2** salvo mejoras.

### Ingresos y pacientes (EPIC-01) — rehace la Fundación
- **Lista** (`Ingresos.tsx`): tabla v2 (Folio, Paciente [avatar+edad/género/email], Estado [StateDot], Diagnóstico
  [+ICD], RUT, Región, Derivación, Ingreso, acciones). Filtros: búsqueda placeholder **"Buscar por RUT, folio o
  nombre"** (mejora doc), Estado, Región, Derivación. Paginación. Datos: `GET /api/v1/pacientes/buscar`.
- **Alta** (existente, restyle v2): `POST /api/v1/ingresos` (rhf+zod, RUT módulo-11, enums backend).
- **Ficha 360 = PatientSheet** (drawer derecho, gradiente, 5 tabs Resumen/Licencias/Fármacos/Controles/
  Observaciones) — **detalle completo estilo Variante 1** (mejora doc). Datos: `GET /api/v1/pacientes/{id}/vista-360`
  + `GET .../licencias`, recetas/esquema, controles por ingreso, audit-log (Observaciones). Slots vacíos del
  backend → "pendiente".

### Licencias médicas (EPIC-07)
- Lista v2 (SimplePages): Folio, Paciente, N° LM, Tipo, Inicio, Fin, Días, Médico, Estado + **GAF/EEAG** y badge
  **"Vence en"** (mejora doc). Filtros preset: tipo LM, **reposo Parcial/Total**, ISL, región (mejoras doc).
- Acciones: alta (`POST /api/v1/licencias`), anular (`PATCH .../anular`), ISL (`PATCH .../isl`), **envío masivo
  ISL + envío por región + por paciente** (mejoras doc; usa el endpoint ISL por lote desde la UI), acumulado
  (`GET /api/v1/ingresos/{id}/licencias/acumulado`), alertas vencimiento (`POST /api/v1/licencias/alertas/generar`).

### Gestión de fármacos (EPIC-02)
- **Modelo de info estilo Variante 1** (mejora doc): por paciente, **receta completa con plazos** (fecha emisión,
  fecha revisión, fecha envío [al paciente, no "farmacia"], cambio de esquema, estado) en filas, **no** cuadritos
  por medicamento; **eliminar la categoría "socorro"**. Filtros preset (estado, médico, marca).
- Endpoints: registro (`/registro-farmacologico`), esquema, recetas, seguimiento, alertas de revisión (≤5 días).

### Controles médicos (EPIC-06)
- Lista estilo Variante 1 (mejora doc): Fecha ingreso, Próximo control, **Semana control**, **Días LM**, **Reposo
  (total/parcial)**, **GAF** (mini-bar), **RECA (estado/fecha)**, médico. Filtros preset.
- Acciones: alta (`POST /api/v1/controles-medicos`, semana autocalculada), próximo control (`PATCH .../proximo-control`),
  subform licencia+GAF+RECA (`PATCH .../licencia`).

### Seguimiento EPT (EPIC-03)
- Lista v2 (Nº EPT, Paciente, Empresa, Tipo, EPTista, Factor riesgo, Entrevistas, Plazos ISL/Informe, Envío ISL,
  Estado). Formularios: caso (`POST /casos-ept`), contactos (≤2 correos), proceso, plazos ISL. Estados de cumplimiento.

### Seguimiento reintegro (EPIC-04)
- Lista v2 (Paciente, Derivación, RECA, Tipo, Riesgos, Medidas, Verificación, Estado, F. reintegro, Alta).
  Formularios: caso (`POST /reintegros`), RECA + medidas (validación temporal verif≥medida≥RECA), cierre.

### Auditoría (EPIC-05)
- Tabla consolidada v2 (header de 2 filas agrupado: Ingreso/Evaluaciones/Informe ISL/RECA/Cierre).
  `GET /api/v1/auditoria/casos` + `/casos/{id}`. Reportes filtrables + **descarga CSV** (`/reportes`, `/reportes/descargar`).
  **Mejoras doc:** **ODAS vencidas por paciente** (`GET /api/v1/odas/alertas` + por ingreso) y **Nº de sesión**.
  Gaps backend (sesiones null) → "—".

### Agendamiento (EPIC-08)
- Grilla multi-profesional v2 (slots 08:30–17:30 × profesionales, colores). Disponibilidad
  (`/disponibilidad-profesional`), propuestas (`/propuestas-agenda` generar/listar/citas/confirmar), estado de cita
  (`PATCH /citas/{id}/estado`). Vista semanal/selector de fecha (v2 hoy es fija).

### Reportería (EPIC-09)
- Charts recharts v2 (ingresos mensuales bar, distribución diagnósticos donut, tipo derivación barras, KPIs
  operativos). Reportes: operativo, convenio, carga laboral, licencias, adherencia, ODAS vencidas
  (`/api/v1/reportes/*`) + ventanas de proceso (`/ventanas-proceso`). Exportar.

### Dashboard (EPIC-09 CEPA-090)
- KPIs primarios (donut) + secundarios + charts (AreaChart atenciones/inasistencias, BarChart carga por profesional
  [+ **horas por profesional**, mejora doc], PieChart diagnósticos) + tareas del día + alertas urgentes.
  Datos: `GET /api/v1/dashboard` (+ reportes para series). Pills del Topbar desde aquí.

## Orden de ejecución (ciclos)

Cada ciclo = spec breve (deriva de este doc) → plan (writing-plans) → impl (subagent-driven) → gate verde → commit/PR.

- **Ciclo 0 — Fundación v2:** portar tokens+componentes+charts de v2; shell (Sidebar/Topbar/AlertsPanel) con datos
  reales (alertas/tareas/dashboard pills); rebrand **SIGE**; restyle Login; **refactor Ingresos** (lista v2 +
  **PatientSheet drawer** 5 tabs) reemplazando las páginas Buscar/Vista360 actuales; rutas por NavKey.
- **Ciclo 1 — Licencias (07)** · **Ciclo 2 — Fármacos (02)** · **Ciclo 3 — Controles (06)** ·
  **Ciclo 4 — EPT (03)** · **Ciclo 5 — Reintegro (04)** · **Ciclo 6 — Auditoría (05)** ·
  **Ciclo 7 — Dashboard (09/090) + cableado final del AlertsPanel/Tareas (10)** ·
  **Ciclo 8 — Reportería (09)** · **Ciclo 9 — Agendamiento (08)**.

## Mejoras del documento (checklist transversal)

- [ ] Búsqueda con placeholder "Buscar por RUT, folio o nombre" (Ingresos y global).
- [ ] Ficha de paciente (drawer derecho) con detalle completo estilo Variante 1.
- [ ] Fármacos: receta completa por paciente con plazos (emisión/revisión/envío), cambio de esquema, estado; sin "socorro".
- [ ] Licencias: GAF/EEAG visible; filtro reposo Parcial/Total; envío por región y por paciente; envío masivo ISL.
- [ ] Controles: semana control, días LM, reposo, GAF, RECA estado/fecha; filtros preset.
- [ ] Dashboard: horas de trabajo por profesional en "Carga por profesional".
- [ ] Auditoría: ODAS vencidas por paciente; N° de sesión.

## Testing / CI / Deploy

- Por módulo: tests unit/componente Vitest + MSW (convenciones de la Fundación: server MSW único, wrapper de fetch
  centralizado), QA preview con preview tools; E2E Playwright creciente. Gate por ciclo: typecheck+lint+test+build.
- CI `frontend-ci` existente; recharts añade peso de bundle (aceptable; code-splitting futuro).
- Deploy a Vercel + CORS en Render: pasos operacionales del usuario (CORS ya implementado en backend).

## Fuera de alcance (esta etapa)

- Pantallas administrativas **no diseñadas en v2**: Usuarios CRUD (CEPA-002), visor de Audit log (CEPA-003), Config de
  formularios (CEPA-110/111), PDF (CEPA-112), Consentimientos CRUD, IMED (CEPA-122, backend 503). El backend las
  soporta; se planifican en una fase posterior con su propio diseño UI. (El módulo "Auditoría" de v2 ≠ visor de
  audit-log técnico.)
- Modo oscuro, switch de densidad/acento (v2 los define pero no son MVP).
- Cookies httpOnly para tokens (mejora futura, requiere backend).

## Criterios de éxito (programa)

1. `frontend/` compila/lint/typecheck limpios con el design system v2 y branding SIGE.
2. Shell v2 (sidebar 3 secciones, topbar con KPIs reales, panel de alertas/tareas real) funcionando.
3. Las 10 pantallas de v2 conectadas al backend real, con las mejoras del documento aplicadas.
4. RBAC en UI (Auditor solo lectura) en todos los módulos.
5. Suite verde por ciclo (Vitest+MSW) + QA preview; E2E del flujo principal.
6. Ingresos rehecho al patrón v2 (lista + Ficha 360 drawer) reemplazando la UX page-based.
