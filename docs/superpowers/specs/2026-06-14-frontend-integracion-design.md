# Diseño — Frontend real e integración con el backend (Fundación)

> **Estado:** aprobado en brainstorming (2026-06-14). Próximo paso: plan de implementación
> (superpowers:writing-plans). Esta spec cubre la **Fundación del frontend + el primer módulo
> (Ingresos/360°)**. Los demás módulos se especifican en ciclos siguientes (spec → plan → impl).

## Contexto y problema

El backend del Sistema CEPA está completo (13 épicas, 774 tests, desplegado en Render:
`https://cepa-backend-staging.onrender.com`) y expone un OpenAPI exhaustivo. Sin embargo, el
"frontend" actual es un **prototipo mock** (`index.html` + `src/*.jsx`, React por CDN, sin
build, sin TypeScript, datos falsos en `data.js`, sin auth ni llamadas HTTP). El README de
specs (`docs/issues/README.md`) define el stack frontend como **React (Vite) + TypeScript +
Tailwind + shadcn/ui**, que nunca se construyó.

**Objetivo de esta Fundación:** crear el frontend real en el stack de la spec, conectado al
backend, con autenticación, RBAC y el primer módulo (Ingresos/Búsqueda 360°) funcionando
end-to-end. Deja la base (build, auth, cliente API tipado, design system, testing, CI/deploy)
para construir los módulos restantes encima.

## Decisiones tomadas (brainstorming)

| Decisión | Elección |
|----------|----------|
| Stack | Vite + React 18 + TypeScript + Tailwind v4 + shadcn/ui (rehacer; el prototipo es referencia visual) |
| Descomposición | Fundación + primer módulo (Ingresos/360°); demás módulos en specs siguientes |
| Tipos ↔ contrato | **Generar tipos TS desde el OpenAPI del backend** (`openapi-typescript`) |
| Estado de servidor | TanStack Query |
| Rutas | React Router con guards por rol |
| Testing | Vitest + Testing Library + **MSW** (unit/componente) + **Playwright** (E2E) + QA preview |
| Diseño | Portar `tokens.css` del prototipo al tema Tailwind; componentes shadcn tematizados |
| Deploy | Build a Vercel (proyecto `cepa-preview` existente); `VITE_API_BASE_URL` → Render |

## Arquitectura

Monorepo: el frontend vive en `frontend/` junto a `backend/`.

```
frontend/
  index.html
  package.json
  vite.config.ts            # incluye config de Vitest
  playwright.config.ts
  tsconfig*.json
  tailwind.config / CSS @theme (tokens portados del prototipo)
  src/
    main.tsx                # bootstrap React + QueryClient + Router + AuthProvider
    app/
      router.tsx            # rutas + guards por rol
      shell/                # layout (sidebar, header) portado del prototipo
    lib/
      apiClient.ts          # fetch tipado + interceptor de refresh (401)
      auth/                 # AuthContext, useAuth, almacenamiento de tokens, jwt-decode
      queryClient.ts        # TanStack Query
      rbac.ts               # helpers de permisos por rol
    types/
      api.ts                # GENERADO desde /openapi.json (no editar a mano)
    features/
      ingresos/             # primer módulo: api/ hooks/ components/ (alta, búsqueda, 360)
    components/ui/          # shadcn
    test/
      setup.ts              # setup Vitest + Testing Library
      msw/                  # handlers tipados desde types/api.ts
  e2e/                      # specs Playwright
```

**Principio de aislamiento:** cada `feature/<modulo>` encapsula su API, hooks y componentes,
y se comunica con el resto solo vía rutas y el cliente API compartido. La capa `lib/` no conoce
módulos concretos. Esto permite añadir módulos sin tocar la Fundación.

## Autenticación, sesión y RBAC

- **Login:** `POST /api/v1/auth/login` → `{access_token, refresh_token, token_type}`. Errores:
  401 genérico ("credenciales inválidas", sin filtrar usuario), 429 (bloqueo por intentos).
- **Almacenamiento:** access token **en memoria** (AuthContext); refresh token en `localStorage`.
  Al montar la app, si hay refresh token → `POST /api/v1/auth/refresh` (login silencioso).
- **Interceptor:** ante `401` de la API, intenta refresh **una vez**; si falla, limpia sesión
  y redirige a login.
- **Rol para UI:** se decodifica del JWT (claim `role` ∈ `Coordinacion`/`Administrativo`/`Auditor`)
  con `jwt-decode`. El servidor es la autoridad real (ya enforcea 401/403); el rol en cliente
  solo dirige la UI (guards de ruta + render condicional; Auditor sin acciones de escritura).
- **Logout:** limpia tokens (memoria + localStorage) y estado de Query.

> **Nota de seguridad (dominio clínico):** access token en memoria reduce exposición a XSS; el
> refresh en `localStorage` es el trade-off pragmático porque el backend entrega tokens en JSON,
> no en cookies httpOnly. Migrar a cookie httpOnly es una mejora futura que requiere cambio de
> backend (fuera del alcance de esta Fundación).

## Primer módulo: Ingresos / Búsqueda 360° (CEPA-010/011/012)

- **Búsqueda 360°:** input → `GET /api/v1/pacientes/buscar?q=` → lista de pacientes; clic abre
  la vista 360. Sin resultados = lista vacía (no error).
- **Vista 360°:** `GET /api/v1/pacientes/{id}/vista-360` → ingresos del paciente; las dimensiones
  aún vacías en el backend (fármacos/licencias/controles/reintegro) se muestran como "pendiente"
  (gap conocido del backend, a poblar en sus módulos).
- **Alta de ingreso:** formulario (react-hook-form + zod) → `POST /api/v1/ingresos`. Campos según
  `IngresoCreate`: rut, nombre, sexo, edad, region, diagnostico, tipo_derivacion, tipo_ingreso,
  modelo_tratamiento, fecha_ingreso (+ opcionales: comuna, teléfono, correo, fecha_diep_diat,
  razón social, nº siniestro, folio manual, es_reingreso). Dropdowns desde los enums de dominio.
  Validación de RUT en cliente (espejo del módulo 11) y del servidor (422 → errores por campo;
  409 → folio en conflicto).
- **RBAC:** Administrativo/Coordinación pueden dar de alta; Auditor solo lectura (sin botón de alta).
- **Flujo de datos:** hooks TanStack Query (`useBuscarPacientes`, `useVista360`, `useCrearIngreso`)
  con tipos generados; invalidación de queries tras el alta.

Los demás sub-features de EPIC-01 (seguimiento, cierre, ODAS, consentimiento) se especifican en
el ciclo del módulo EPIC-01, no en esta Fundación.

## Manejo de errores

- **Global:** error boundary de React + toasts para errores inesperados.
- **API → mensajes claros:** 401 → re-login; 403 → "no tienes permiso"; 409 → mensaje de
  conflicto (p. ej. folio); 422 → errores mapeados por campo en el formulario; 5xx/red → toast
  con reintento.
- **Formularios:** validación cliente con zod antes de enviar; el servidor sigue siendo la
  autoridad.

## Testing

- **Unit/componente:** Vitest + Testing Library. **MSW** con handlers tipados desde `types/api.ts`
  cubriendo login, refresh, buscar, vista-360, alta y casos de error (401/403/409/422). Cada
  pantalla y hook con sus tests.
- **E2E (Playwright):** flujo login → alta de ingreso → búsqueda → vista 360. En CI corre contra
  un **backend local desechable** (docker-compose del backend, BD efímera) para determinismo y
  no contaminar staging; staging se usa para humo manual.
- **QA preview:** validación visual con las preview tools antes de cerrar cada entrega.

## Cambios en el backend (parte de "conectar de verdad")

- **CORS:** añadir `fastapi.middleware.cors.CORSMiddleware` permitiendo los orígenes del frontend
  (Vercel: `https://cepa-preview.vercel.app` y previews; `http://localhost:5173` en dev),
  parametrizable por env (`CORS_ORIGINS`). Único cambio de backend de esta Fundación.

## Deploy y CI

- **CI (`frontend-ci`):** lint (eslint) + typecheck (tsc) + unit (vitest) + build (vite) + E2E
  (Playwright contra backend docker-compose).
- **Deploy:** build de Vite al proyecto Vercel `cepa-preview` (reemplaza el mock). Variable
  `VITE_API_BASE_URL` → `https://cepa-backend-staging.onrender.com`. Tras desplegar, actualizar
  `CORS_ORIGINS` del backend en Render con el dominio de Vercel.
- **Generación de tipos:** script `npm run gen:api` que corre `openapi-typescript` contra el
  `/openapi.json` del backend (commit del resultado en `src/types/api.ts`).

## Fuera de alcance (esta Fundación)

- Módulos distintos de Ingresos/360° (fármacos, EPT, reintegro, controles, licencias,
  agendamiento, dashboard/reportes, alertas, auditoría, config de formularios) — specs siguientes.
- Sub-features avanzados de EPIC-01 (seguimiento, cierre, ODAS, consentimiento).
- Gaps de backend ya documentados (export CSV/PDF, CEPA-095 CA-3, CEPA-111 captura, CEPA-096,
  scoping por profesional, poblar ranuras vista-360) — backlog separado.
- Cookies httpOnly para tokens (mejora de seguridad futura, requiere cambio backend).

## Criterios de éxito (Fundación)

1. Proyecto `frontend/` en el stack spec compila, lint y typecheck limpios.
2. Login real contra el backend; sesión persistente con refresh silencioso; logout.
3. RBAC en UI por los 3 roles (Auditor solo lectura).
4. Módulo Ingresos/360° end-to-end: alta, búsqueda y vista 360 contra el backend real.
5. Suite verde: unit/componente (MSW) + E2E (Playwright) + QA preview.
6. Backend con CORS; frontend desplegado en Vercel apuntando a Render.
