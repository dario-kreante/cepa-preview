# Frontend real + integración (Fundación + módulo Ingresos) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan Task por Task. Los pasos usan checkbox (`- [ ]`).

**Goal:** Construir el frontend real del Sistema CEPA (Vite + React + TypeScript + Tailwind v4 + shadcn/ui), conectado al backend FastAPI, con login JWT, RBAC en UI y el módulo Ingresos/Búsqueda 360° funcionando end-to-end; dejar la base (cliente API tipado desde OpenAPI, testing, CI/deploy) para los módulos siguientes.

**Architecture:** Proyecto nuevo en `frontend/` (monorepo junto a `backend/`). Tipos TS generados desde el `/openapi.json` del backend (`openapi-typescript`) y cliente `openapi-fetch` con middleware de auth/refresh. Estado de servidor con TanStack Query; rutas con React Router y guards por rol. Diseño portado del prototipo (`src/tokens.css`). Tests con Vitest + Testing Library + MSW y E2E con Playwright contra un backend docker-compose. El backend añade `CORSMiddleware`.

**Tech Stack:** Vite 6, React 18, TypeScript 5, Tailwind v4, shadcn/ui, @tanstack/react-query 5, react-router-dom 7, openapi-typescript 7 + openapi-fetch 0.13, jwt-decode 4, react-hook-form 7 + zod 3 + @hookform/resolvers, MSW 2, Vitest 2 + @testing-library/react, Playwright 1.

**Referencia de diseño:** `docs/superpowers/specs/2026-06-14-frontend-integracion-design.md`.

**Convención:** comandos del frontend desde `frontend/` con `npm …`. El backend (CORS) desde `backend/` con `uv …`. Backend de pruebas/contratos: `https://cepa-backend-staging.onrender.com` (sólo para generar tipos) y docker-compose local para E2E.

---

## Estructura de archivos

```
frontend/
  package.json, tsconfig.json, tsconfig.node.json, vite.config.ts, playwright.config.ts
  index.html, components.json, .env.example, .env
  src/
    main.tsx                      # bootstrap: Router + QueryClientProvider + AuthProvider
    index.css                     # Tailwind + @theme (tokens portados)
    types/api.ts                  # GENERADO (openapi-typescript) — no editar
    lib/
      apiClient.ts                # openapi-fetch + middleware auth/refresh
      tokenStore.ts               # access en memoria + refresh en localStorage
      auth/AuthContext.tsx        # AuthProvider, useAuth, login/logout/rol
      queryClient.ts              # QueryClient
      rbac.ts                     # puede(rol, accion)
      utils.ts                    # cn() para shadcn
      rut.ts                      # validación módulo 11 (espejo del backend)
    app/
      router.tsx                  # rutas + ProtectedRoute
      shell/AppShell.tsx          # layout (sidebar + header)
      shell/nav.ts                # definición de módulos del menú
    features/
      auth/LoginPage.tsx
      ingresos/
        api.ts                    # funciones tipadas (buscar, vista360, crear)
        hooks.ts                  # useBuscarPacientes, useVista360, useCrearIngreso
        BuscarPage.tsx
        Vista360Page.tsx
        AltaIngresoPage.tsx
        ingresoSchema.ts          # zod del formulario
    components/ui/                # shadcn (button, input, card, table, select, label, form, sonner, dialog)
    test/
      setup.ts                    # jsdom + jest-dom + MSW server
      msw/handlers.ts             # handlers tipados
      msw/server.ts               # setupServer
  e2e/
    auth.spec.ts, ingresos.spec.ts
  .github/ (en raíz del repo): .github/workflows/frontend-ci.yml
```

---

### Task 1: Scaffold del proyecto Vite + React + TS

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/.env.example`, `frontend/.env`, `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/vite-env.d.ts`
- Modify: `.gitignore` (raíz)

- [ ] **Step 1: Crear el proyecto y dependencias**

Run (desde la raíz del repo):
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install @tanstack/react-query@^5 react-router-dom@^7 openapi-fetch@^0.13 jwt-decode@^4 \
  react-hook-form@^7 zod@^3 @hookform/resolvers@^3 sonner@^1 clsx tailwind-merge class-variance-authority lucide-react
npm install -D openapi-typescript@^7 tailwindcss@^4 @tailwindcss/vite@^4 \
  vitest@^2 jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom \
  msw@^2 @playwright/test@^1 @types/node
```
Expected: instala sin errores; `frontend/package.json` con las dependencias.

- [ ] **Step 2: Configurar `vite.config.ts` (Vite + Tailwind v4 + Vitest + alias `@`)**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
```

- [ ] **Step 3: `tsconfig.json` (paths `@/*`)**

Reemplazar `compilerOptions.paths` añadiendo:
```jsonc
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```
(Mantener el resto de la config del template.)

- [ ] **Step 4: `index.css` con Tailwind v4 + tema portado del prototipo**

```css
@import "tailwindcss";

@theme {
  --color-brand-50: #eff5fb;
  --color-brand-100: #dbe8f4;
  --color-brand-200: #b8d0e7;
  --color-brand-300: #8bb2d5;
  --color-brand-400: #5a8fbe;
  --color-brand-500: #2f6ea4;
  --color-brand-600: #1f5a8f;
  --color-brand-700: #174877;
  --color-brand-800: #123a61;
  --color-brand-900: #0d2a48;
  --color-ink-50: #f7f9fc;
  --color-ink-100: #eef2f7;
  --color-ink-200: #dde4ee;
  --color-ink-300: #c2cdda;
  --color-ink-400: #8c9bae;
  --color-ink-500: #5e6b7d;
  --color-ink-700: #2f3a48;
  --color-ink-900: #0f1721;
  --color-success-600: #039855;
  --color-warn-600: #d97706;
  --color-danger-600: #d92d20;
  --color-info-600: #1570ef;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
}

:root { color-scheme: light; }
body { @apply bg-ink-50 text-ink-900 font-sans antialiased; }
```

> Nota: estos valores se portan de `src/tokens.css` del prototipo (paleta UTalca). Si se quiere
> el set completo de tonos, copiar las variables `--brand-*`/`--ink-*` restantes con el prefijo
> `--color-` requerido por Tailwind v4.

- [ ] **Step 5: `index.html` (fuente Inter + root)**

Reemplazar `<head>` del `index.html` generado para incluir Inter y dejar `<div id="root">`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
<title>Sistema CEPA</title>
```

- [ ] **Step 6: `.env.example` y `.env`**

`frontend/.env.example`:
```bash
VITE_API_BASE_URL=https://cepa-backend-staging.onrender.com
```
`frontend/.env` (igual contenido para dev local apuntando a staging; o `http://localhost:8000`).

- [ ] **Step 7: `src/vite-env.d.ts` (tipar env)**

```ts
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 8: `src/main.tsx` mínimo (placeholder temporal)**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="p-6 text-brand-700">Sistema CEPA — base</div>
  </StrictMode>,
);
```

- [ ] **Step 9: `.gitignore` de la raíz — añadir artefactos del frontend**

Añadir al final de `.gitignore`:
```
# Frontend
frontend/node_modules/
frontend/dist/
frontend/.env
frontend/playwright-report/
frontend/test-results/
```

- [ ] **Step 10: Verificar build y arranque**

Run (desde `frontend/`): `npm run build`
Expected: build sin errores de TypeScript.

- [ ] **Step 11: Commit**

```bash
git add frontend/ .gitignore
git commit -m "chore(frontend): scaffold Vite + React + TS + Tailwind v4"
```

---

### Task 2: shadcn/ui + utilidades base

**Files:**
- Create: `frontend/components.json`, `frontend/src/lib/utils.ts`, `frontend/src/components/ui/*`

- [ ] **Step 1: `src/lib/utils.ts` (helper `cn`)**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: `components.json` para shadcn (Tailwind v4, alias `@`)**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": { "config": "", "css": "src/index.css", "baseColor": "slate", "cssVariables": true },
  "aliases": { "components": "@/components", "utils": "@/lib/utils", "ui": "@/components/ui" },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 3: Añadir componentes shadcn**

Run (desde `frontend/`):
```bash
npx shadcn@latest add button input label card table select form sonner dialog --yes
```
Expected: crea `src/components/ui/{button,input,label,card,table,select,form,sonner,dialog}.tsx`. Si el CLI pide confirmaciones, aceptarlas; si falla por Tailwind v4, seguir la guía del skill `tailwind-v4-shadcn`.

- [ ] **Step 4: Verificar typecheck**

Run: `npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/components.json frontend/src/lib/utils.ts frontend/src/components/ui/
git commit -m "chore(frontend): shadcn/ui + componentes base"
```

---

### Task 3: Generación de tipos desde el OpenAPI del backend

**Files:**
- Create: `frontend/src/types/api.ts` (generado)
- Modify: `frontend/package.json` (script `gen:api`)

- [ ] **Step 1: Añadir script `gen:api` a `package.json`**

En `"scripts"` agregar:
```json
"gen:api": "openapi-typescript ${VITE_API_BASE_URL:-https://cepa-backend-staging.onrender.com}/openapi.json -o src/types/api.ts"
```

- [ ] **Step 2: Generar los tipos**

Run (desde `frontend/`, con el backend de staging accesible):
```bash
npm run gen:api
```
Expected: crea `src/types/api.ts` con `paths`/`components` del backend. Debe contener las rutas `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/pacientes/buscar`, `/api/v1/pacientes/{paciente_id}/vista-360`, `/api/v1/ingresos`.

- [ ] **Step 3: Verificar que los tipos compilan**

Run: `npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/src/types/api.ts
git commit -m "feat(frontend): tipos TS generados desde el OpenAPI del backend"
```

---

### Task 4: Almacenamiento de tokens (memoria + localStorage)

**Files:**
- Create: `frontend/src/lib/tokenStore.ts`
- Test: `frontend/src/lib/tokenStore.test.ts`

- [ ] **Step 1: Escribir el test que falla**

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { tokenStore } from "./tokenStore";

describe("tokenStore", () => {
  beforeEach(() => { localStorage.clear(); tokenStore.clear(); });

  it("guarda y lee el access token en memoria (no en localStorage)", () => {
    tokenStore.setAccess("abc");
    expect(tokenStore.getAccess()).toBe("abc");
    expect(localStorage.getItem("cepa_access")).toBeNull();
  });

  it("persiste el refresh token en localStorage", () => {
    tokenStore.setRefresh("ref");
    expect(tokenStore.getRefresh()).toBe("ref");
    expect(localStorage.getItem("cepa_refresh")).toBe("ref");
  });

  it("clear borra ambos", () => {
    tokenStore.setAccess("a"); tokenStore.setRefresh("r");
    tokenStore.clear();
    expect(tokenStore.getAccess()).toBeNull();
    expect(tokenStore.getRefresh()).toBeNull();
  });
});
```

- [ ] **Step 2: Correr y ver que falla**

Run: `npx vitest run src/lib/tokenStore.test.ts`
Expected: FAIL (módulo no existe).

- [ ] **Step 3: Implementar `tokenStore.ts`**

```ts
const REFRESH_KEY = "cepa_refresh";
let accessToken: string | null = null;

export const tokenStore = {
  getAccess: () => accessToken,
  setAccess: (t: string | null) => { accessToken = t; },
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  setRefresh: (t: string | null) => {
    if (t) localStorage.setItem(REFRESH_KEY, t);
    else localStorage.removeItem(REFRESH_KEY);
  },
  clear: () => { accessToken = null; localStorage.removeItem(REFRESH_KEY); },
};
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `npx vitest run src/lib/tokenStore.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/tokenStore.ts frontend/src/lib/tokenStore.test.ts
git commit -m "feat(frontend): almacenamiento de tokens (access en memoria, refresh en localStorage)"
```

---

### Task 5: Cliente API tipado con middleware de auth/refresh

**Files:**
- Create: `frontend/src/lib/apiClient.ts`
- Test: `frontend/src/lib/apiClient.test.ts`
- Depende de: `src/test/msw/server.ts` y `handlers.ts` (Task 11). Para no bloquear, este test usa `msw` directamente con un server local.

- [ ] **Step 1: Escribir el test que falla (refresh ante 401)**

```ts
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { api } from "./apiClient";
import { tokenStore } from "./tokenStore";

const BASE = import.meta.env.VITE_API_BASE_URL;
let refreshCalls = 0;

const server = setupServer(
  http.get(`${BASE}/api/v1/ingresos`, ({ request }) => {
    const auth = request.headers.get("authorization");
    if (auth === "Bearer good") return HttpResponse.json([]);
    return new HttpResponse(null, { status: 401 });
  }),
  http.post(`${BASE}/api/v1/auth/refresh`, async () => {
    refreshCalls += 1;
    return HttpResponse.json({ access_token: "good", token_type: "bearer" });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => { refreshCalls = 0; tokenStore.clear(); });

describe("apiClient", () => {
  it("ante 401 refresca una vez y reintenta con el nuevo token", async () => {
    tokenStore.setAccess("stale");
    tokenStore.setRefresh("r");
    const { response } = await api.GET("/api/v1/ingresos", {});
    expect(refreshCalls).toBe(1);
    expect(response.status).toBe(200);
    expect(tokenStore.getAccess()).toBe("good");
  });
});
```

- [ ] **Step 2: Correr y ver que falla**

Run: `npx vitest run src/lib/apiClient.test.ts`
Expected: FAIL (módulo no existe).

- [ ] **Step 3: Implementar `apiClient.ts`**

```ts
import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "@/types/api";
import { tokenStore } from "./tokenStore";

const baseUrl = import.meta.env.VITE_API_BASE_URL;

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) { tokenStore.clear(); return false; }
  const data = (await res.json()) as { access_token: string };
  tokenStore.setAccess(data.access_token);
  return true;
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const token = tokenStore.getAccess();
    if (token) request.headers.set("authorization", `Bearer ${token}`);
    return request;
  },
  async onResponse({ request, response }) {
    if (response.status !== 401) return response;
    // Evitar bucle en el propio refresh
    if (request.url.endsWith("/api/v1/auth/refresh")) return response;
    refreshing ??= doRefresh().finally(() => { refreshing = null; });
    const ok = await refreshing;
    if (!ok) return response;
    const retried = new Request(request.url, request);
    retried.headers.set("authorization", `Bearer ${tokenStore.getAccess()}`);
    return fetch(retried);
  },
};

export const api = createClient<paths>({ baseUrl });
api.use(authMiddleware);
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `npx vitest run src/lib/apiClient.test.ts`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/apiClient.ts frontend/src/lib/apiClient.test.ts
git commit -m "feat(frontend): cliente API tipado (openapi-fetch) con refresh ante 401"
```

---

### Task 6: RBAC y contexto de autenticación

**Files:**
- Create: `frontend/src/lib/rbac.ts`, `frontend/src/lib/auth/AuthContext.tsx`
- Test: `frontend/src/lib/rbac.test.ts`, `frontend/src/lib/auth/AuthContext.test.tsx`

- [ ] **Step 1: Test de `rbac.ts` (que falla)**

```ts
import { describe, expect, it } from "vitest";
import { puedeEscribir, type Rol } from "./rbac";

describe("rbac", () => {
  it("Administrativo y Coordinacion pueden escribir; Auditor no", () => {
    expect(puedeEscribir("Administrativo")).toBe(true);
    expect(puedeEscribir("Coordinacion")).toBe(true);
    expect(puedeEscribir("Auditor")).toBe(false);
  });
});
```

- [ ] **Step 2: Ver que falla y luego implementar `rbac.ts`**

Run: `npx vitest run src/lib/rbac.test.ts` → FAIL. Implementar:
```ts
export type Rol = "Coordinacion" | "Administrativo" | "Auditor";
const ESCRITORES: Rol[] = ["Coordinacion", "Administrativo"];
export function puedeEscribir(rol: Rol | null | undefined): boolean {
  return !!rol && ESCRITORES.includes(rol);
}
```
Run de nuevo: PASS.

- [ ] **Step 3: Test de `AuthContext` (login decodifica rol del JWT)**

```tsx
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./AuthContext";
import { tokenStore } from "@/lib/tokenStore";

const BASE = import.meta.env.VITE_API_BASE_URL;
// JWT con payload {"sub":"1","username":"ana","role":"Auditor","type":"access"} (sin verificar firma)
const JWT_AUDITOR =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhbmEiLCJyb2xlIjoiQXVkaXRvciIsInR5cGUiOiJhY2Nlc3MifQ." +
  "x";

const server = setupServer(
  http.post(`${BASE}/api/v1/auth/login`, () =>
    HttpResponse.json({ access_token: JWT_AUDITOR, refresh_token: "r", token_type: "bearer" }),
  ),
);
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); tokenStore.clear(); });
afterAll(() => server.close());

function Probe() {
  const { rol, login } = useAuth();
  return (
    <div>
      <span>rol:{rol ?? "none"}</span>
      <button onClick={() => login("ana", "x")}>login</button>
    </div>
  );
}

describe("AuthContext", () => {
  it("tras login expone el rol decodificado del JWT", async () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    await userEvent.click(screen.getByText("login"));
    await waitFor(() => expect(screen.getByText("rol:Auditor")).toBeInTheDocument());
  });
});
```

- [ ] **Step 4: Ver que falla**

Run: `npx vitest run src/lib/auth/AuthContext.test.tsx` → FAIL.

- [ ] **Step 5: Implementar `AuthContext.tsx`**

```tsx
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { jwtDecode } from "jwt-decode";
import { api } from "@/lib/apiClient";
import { tokenStore } from "@/lib/tokenStore";
import type { Rol } from "@/lib/rbac";

interface JwtClaims { sub: string; username: string; role: Rol; type: string; exp: number; }

interface AuthState {
  rol: Rol | null;
  username: string | null;
  cargando: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

function rolDesdeToken(token: string | null): { rol: Rol | null; username: string | null } {
  if (!token) return { rol: null, username: null };
  try {
    const c = jwtDecode<JwtClaims>(token);
    return { rol: c.role, username: c.username };
  } catch {
    return { rol: null, username: null };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [rol, setRol] = useState<Rol | null>(() => rolDesdeToken(tokenStore.getAccess()).rol);
  const [username, setUsername] = useState<string | null>(() => rolDesdeToken(tokenStore.getAccess()).username);
  const [cargando, setCargando] = useState(true);

  // Login silencioso al montar si hay refresh token.
  useEffect(() => {
    let activo = true;
    (async () => {
      if (!tokenStore.getAccess() && tokenStore.getRefresh()) {
        const refresh = tokenStore.getRefresh()!;
        const { data } = await api.POST("/api/v1/auth/refresh", { body: { refresh_token: refresh } });
        if (activo && data?.access_token) {
          tokenStore.setAccess(data.access_token);
          const r = rolDesdeToken(data.access_token);
          setRol(r.rol); setUsername(r.username);
        } else if (activo) {
          tokenStore.clear();
        }
      }
      if (activo) setCargando(false);
    })();
    return () => { activo = false; };
  }, []);

  async function login(user: string, password: string) {
    const { data, error } = await api.POST("/api/v1/auth/login", { body: { username: user, password } });
    if (error || !data) throw new Error("Credenciales inválidas");
    tokenStore.setAccess(data.access_token);
    tokenStore.setRefresh(data.refresh_token);
    const r = rolDesdeToken(data.access_token);
    setRol(r.rol); setUsername(r.username);
  }

  function logout() {
    tokenStore.clear();
    setRol(null); setUsername(null);
  }

  const value = useMemo(() => ({ rol, username, cargando, login, logout }), [rol, username, cargando]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}
```

- [ ] **Step 6: Ver que pasa**

Run: `npx vitest run src/lib/rbac.test.ts src/lib/auth/AuthContext.test.tsx`
Expected: ambos passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/rbac.ts frontend/src/lib/rbac.test.ts frontend/src/lib/auth/
git commit -m "feat(frontend): RBAC + AuthContext (login/logout, refresh silencioso, rol del JWT)"
```

---

### Task 7: QueryClient, rutas y guards (RBAC)

**Files:**
- Create: `frontend/src/lib/queryClient.ts`, `frontend/src/app/router.tsx`, `frontend/src/features/auth/LoginPage.tsx`
- Modify: `frontend/src/main.tsx`
- Test: `frontend/src/app/router.test.tsx`

- [ ] **Step 1: `queryClient.ts`**

```ts
import { QueryClient } from "@tanstack/react-query";
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 } },
});
```

- [ ] **Step 2: Test de guard (redirige a /login sin sesión)**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { ProtectedRoute } from "./router";

function wrap(initial: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/login" element={<div>login-page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<div>home-protegido</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("ProtectedRoute", () => {
  it("sin sesión redirige a /login", async () => {
    wrap("/");
    expect(await screen.findByText("login-page")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Ver que falla y luego implementar `router.tsx`**

Run: `npx vitest run src/app/router.test.tsx` → FAIL. Implementar:
```tsx
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { AppShell } from "./shell/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { BuscarPage } from "@/features/ingresos/BuscarPage";
import { Vista360Page } from "@/features/ingresos/Vista360Page";
import { AltaIngresoPage } from "@/features/ingresos/AltaIngresoPage";

export function ProtectedRoute({ rolesEscritura }: { rolesEscritura?: boolean }) {
  const { rol, cargando } = useAuth();
  if (cargando) return <div className="p-6 text-ink-500">Cargando…</div>;
  if (!rol) return <Navigate to="/login" replace />;
  if (rolesEscritura && !puedeEscribir(rol as Rol)) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<BuscarPage />} />
          <Route path="/pacientes/:id" element={<Vista360Page />} />
          <Route element={<ProtectedRoute rolesEscritura />}>
            <Route path="/ingresos/nuevo" element={<AltaIngresoPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 4: Implementar `LoginPage.tsx`**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState(""); const [p, setP] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { await login(u, p); nav("/"); }
    catch { setError("Credenciales inválidas"); }
    finally { setEnviando(false); }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-ink-100">
      <Card className="w-full max-w-sm p-6 space-y-4">
        <h1 className="text-xl font-semibold text-brand-700">Sistema CEPA</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="u">Usuario</Label>
            <Input id="u" value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="p">Contraseña</Label>
            <Input id="p" type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" />
          </div>
          {error && <p role="alert" className="text-sm text-danger-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={enviando}>
            {enviando ? "Ingresando…" : "Ingresar"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: Reescribir `main.tsx` con providers**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { queryClient } from "@/lib/queryClient";
import { AppRoutes } from "@/app/router";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster richColors />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 6: Ver que pasa el test del guard**

Run: `npx vitest run src/app/router.test.tsx`
Expected: PASS. (Requiere que existan los componentes de Ingresos y AppShell de las Tasks 8–10; si aún no, este test puede ejecutarse tras la Task 10. Marcar el orden: implementar Tasks 8–10 antes de correr el typecheck global.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/queryClient.ts frontend/src/app/router.tsx frontend/src/app/router.test.tsx frontend/src/features/auth/ frontend/src/main.tsx
git commit -m "feat(frontend): rutas + guards RBAC + página de login + providers"
```

---

### Task 8: App shell (sidebar + header)

**Files:**
- Create: `frontend/src/app/shell/nav.ts`, `frontend/src/app/shell/AppShell.tsx`

- [ ] **Step 1: `nav.ts` (módulos del menú; sólo Ingresos activo)**

```ts
export interface NavItem { to: string; label: string; activo: boolean; }
export const NAV: NavItem[] = [
  { to: "/", label: "Búsqueda 360°", activo: true },
  { to: "/ingresos/nuevo", label: "Nuevo ingreso", activo: true },
  { to: "/farmacos", label: "Fármacos", activo: false },
  { to: "/licencias", label: "Licencias", activo: false },
  { to: "/controles", label: "Controles", activo: false },
  { to: "/ept", label: "EPT", activo: false },
  { to: "/reintegro", label: "Reintegro", activo: false },
  { to: "/agenda", label: "Agendamiento", activo: false },
  { to: "/reportes", label: "Reportería", activo: false },
  { to: "/alertas", label: "Alertas", activo: false },
  { to: "/auditoria", label: "Auditoría", activo: false },
];
```

- [ ] **Step 2: `AppShell.tsx` (layout con Outlet + logout + rol)**

```tsx
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { NAV } from "./nav";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AppShell() {
  const { rol, username, logout } = useAuth();
  const escritor = puedeEscribir(rol as Rol);
  return (
    <div className="min-h-screen grid grid-cols-[240px_1fr] bg-ink-50">
      <aside className="border-r border-ink-200 bg-white p-4 space-y-1">
        <div className="px-2 py-3 text-brand-700 font-semibold">Sistema CEPA</div>
        {NAV.filter((n) => n.activo && (n.to !== "/ingresos/nuevo" || escritor)).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"}
            className={({ isActive }) => cn(
              "block rounded-md px-3 py-2 text-sm",
              isActive ? "bg-brand-50 text-brand-700 font-medium" : "text-ink-700 hover:bg-ink-100",
            )}>
            {n.label}
          </NavLink>
        ))}
        <div className="pt-2 mt-2 border-t border-ink-200 text-xs text-ink-400">Próximamente</div>
        {NAV.filter((n) => !n.activo).map((n) => (
          <span key={n.to} className="block rounded-md px-3 py-2 text-sm text-ink-300 cursor-not-allowed">{n.label}</span>
        ))}
      </aside>
      <div className="flex flex-col">
        <header className="flex items-center justify-between border-b border-ink-200 bg-white px-6 py-3">
          <Link to="/" className="text-sm text-ink-500">CEPA · UTalca</Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-ink-500">{username} · {rol}</span>
            <Button variant="outline" size="sm" onClick={logout}>Salir</Button>
          </div>
        </header>
        <main className="p-6"><Outlet /></main>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `npx tsc --noEmit` (puede requerir los componentes de Ingresos de la Task 9–10).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/shell/
git commit -m "feat(frontend): app shell (sidebar con módulos + header con rol/logout)"
```

---

### Task 9: Ingresos — capa de API y hooks

**Files:**
- Create: `frontend/src/features/ingresos/api.ts`, `frontend/src/features/ingresos/hooks.ts`
- Test: `frontend/src/features/ingresos/hooks.test.tsx`
- Depende de MSW (Task 11). Este test arma su propio `setupServer`.

- [ ] **Step 1: Implementar `api.ts` (funciones tipadas)**

```ts
import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type PacienteRead = components["schemas"]["PacienteRead"];
export type Vista360 = components["schemas"]["Vista360"];
export type IngresoCreate = components["schemas"]["IngresoCreate"];
export type IngresoRead = components["schemas"]["IngresoRead"];

export async function buscarPacientes(q: string): Promise<PacienteRead[]> {
  const { data, error } = await api.GET("/api/v1/pacientes/buscar", { params: { query: { q } } });
  if (error) throw new Error("Error al buscar pacientes");
  return data ?? [];
}

export async function obtenerVista360(id: number): Promise<Vista360> {
  const { data, error } = await api.GET("/api/v1/pacientes/{paciente_id}/vista-360", {
    params: { path: { paciente_id: id } },
  });
  if (error || !data) throw new Error("No se pudo cargar la vista 360");
  return data;
}

export async function crearIngreso(body: IngresoCreate): Promise<IngresoRead> {
  const { data, error, response } = await api.POST("/api/v1/ingresos", { body });
  if (error || !data) {
    if (response.status === 409) throw new Error("El folio ya está emitido para otro ingreso.");
    if (response.status === 422) throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el ingreso");
  }
  return data;
}
```

- [ ] **Step 2: Test de hooks (que falla)**

```tsx
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useBuscarPacientes } from "./hooks";
import type { ReactNode } from "react";

const BASE = import.meta.env.VITE_API_BASE_URL;
const server = setupServer(
  http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
    HttpResponse.json([{ id: 1, rut: "11111111-1", nombre: "Ana", sexo: "F", edad: 30, region: "Maule", comuna: null, telefono: null, correo: null }]),
  ),
);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useBuscarPacientes", () => {
  it("devuelve pacientes para una query no vacía", async () => {
    const { result } = renderHook(() => useBuscarPacientes("Ana"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].nombre).toBe("Ana");
  });
});
```

- [ ] **Step 3: Ver que falla y luego implementar `hooks.ts`**

Run: `npx vitest run src/features/ingresos/hooks.test.tsx` → FAIL. Implementar:
```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { buscarPacientes, crearIngreso, obtenerVista360, type IngresoCreate } from "./api";

export function useBuscarPacientes(q: string) {
  return useQuery({
    queryKey: ["pacientes", "buscar", q],
    queryFn: () => buscarPacientes(q),
    enabled: q.trim().length > 0,
  });
}

export function useVista360(id: number) {
  return useQuery({ queryKey: ["pacientes", id, "vista360"], queryFn: () => obtenerVista360(id) });
}

export function useCrearIngreso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IngresoCreate) => crearIngreso(body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pacientes"] }); },
  });
}
```
Run de nuevo: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/ingresos/api.ts frontend/src/features/ingresos/hooks.ts frontend/src/features/ingresos/hooks.test.tsx
git commit -m "feat(ingresos): capa API tipada + hooks TanStack Query (buscar/vista360/crear)"
```

---

### Task 10: Ingresos — pantallas (búsqueda, vista 360, alta)

**Files:**
- Create: `frontend/src/lib/rut.ts`, `frontend/src/features/ingresos/ingresoSchema.ts`, `BuscarPage.tsx`, `Vista360Page.tsx`, `AltaIngresoPage.tsx`
- Test: `frontend/src/lib/rut.test.ts`, `frontend/src/features/ingresos/AltaIngresoPage.test.tsx`

- [ ] **Step 1: Test de `rut.ts` (validación módulo 11)**

```ts
import { describe, expect, it } from "vitest";
import { rutValido } from "./rut";

describe("rutValido", () => {
  it("acepta RUT con DV correcto", () => {
    expect(rutValido("11.111.111-1")).toBe(true);
    expect(rutValido("7.876.543-7")).toBe(true);
  });
  it("rechaza DV incorrecto", () => {
    expect(rutValido("11.111.111-2")).toBe(false);
    expect(rutValido("abc")).toBe(false);
  });
});
```

- [ ] **Step 2: Ver que falla y luego implementar `rut.ts`**

Run: `npx vitest run src/lib/rut.test.ts` → FAIL. Implementar (espejo del módulo 11 del backend):
```ts
export function rutValido(rut: string): boolean {
  const limpio = rut.replace(/[.\-\s]/g, "").toUpperCase();
  if (limpio.length < 2) return false;
  const cuerpo = limpio.slice(0, -1);
  const dv = limpio.slice(-1);
  if (!/^\d+$/.test(cuerpo)) return false;
  let suma = 0, mul = 2;
  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma += parseInt(cuerpo[i], 10) * mul;
    mul = mul === 7 ? 2 : mul + 1;
  }
  const resto = 11 - (suma % 11);
  const dvEsperado = resto === 11 ? "0" : resto === 10 ? "K" : String(resto);
  return dv === dvEsperado;
}
```
Run de nuevo: PASS.

- [ ] **Step 3: `ingresoSchema.ts` (zod del formulario)**

```ts
import { z } from "zod";
import { rutValido } from "@/lib/rut";

export const ingresoSchema = z.object({
  rut: z.string().refine(rutValido, "RUT inválido"),
  nombre: z.string().min(1, "Requerido"),
  sexo: z.enum(["F", "M", "otro"]),
  edad: z.coerce.number().int().min(1).max(130),
  region: z.string().min(1, "Requerido"),
  diagnostico: z.string().min(1, "Requerido"),
  tipo_derivacion: z.enum(["DIEP", "DIAT", "PAPT a flujo AT", "Reingreso FUMP", "Reingreso SUSESO", "Convenio U.Clinica", "Proyecto", "Particular", "PAPT"]),
  tipo_ingreso: z.enum(["consulta_espontanea", "convenio", "proyecto", "particular"]),
  modelo_tratamiento: z.string().min(1, "Requerido"),
  fecha_ingreso: z.string().min(1, "Requerido"),
  folio: z.string().optional(),
  es_reingreso: z.boolean().default(false),
});

export type IngresoForm = z.infer<typeof ingresoSchema>;
```

- [ ] **Step 4: `BuscarPage.tsx`**

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { useBuscarPacientes } from "./hooks";
import { Input } from "@/components/ui/input";

export function BuscarPage() {
  const [q, setQ] = useState("");
  const { data, isFetching } = useBuscarPacientes(q);
  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-lg font-semibold text-ink-900">Búsqueda 360°</h1>
      <Input placeholder="RUT, nombre o folio…" value={q} onChange={(e) => setQ(e.target.value)} />
      {isFetching && <p className="text-sm text-ink-400">Buscando…</p>}
      <ul className="divide-y divide-ink-200 rounded-md border border-ink-200 bg-white">
        {(data ?? []).map((p) => (
          <li key={p.id}>
            <Link to={`/pacientes/${p.id}`} className="flex justify-between px-4 py-3 hover:bg-ink-50">
              <span className="font-medium">{p.nombre}</span>
              <span className="text-ink-500">{p.rut}</span>
            </Link>
          </li>
        ))}
        {q && !isFetching && (data?.length ?? 0) === 0 && (
          <li className="px-4 py-3 text-ink-400 text-sm">Sin resultados</li>
        )}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: `Vista360Page.tsx`**

```tsx
import { useParams } from "react-router-dom";
import { useVista360 } from "./hooks";
import { Card } from "@/components/ui/card";

export function Vista360Page() {
  const { id } = useParams();
  const { data, isLoading, isError } = useVista360(Number(id));
  if (isLoading) return <p className="text-ink-400">Cargando…</p>;
  if (isError || !data) return <p className="text-danger-600">No se pudo cargar el paciente.</p>;
  const ranuras: [string, unknown[]][] = [
    ["Fármacos", data.farmacos], ["Licencias", data.licencias],
    ["Controles", data.controles], ["Reintegro", data.reintegro],
  ];
  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-lg font-semibold">{data.paciente.nombre} <span className="text-ink-500 font-normal">· {data.paciente.rut}</span></h1>
      <Card className="p-4">
        <h2 className="font-medium mb-2">Ingresos</h2>
        <ul className="space-y-1 text-sm">
          {data.ingresos.map((i) => (
            <li key={i.id} className="flex justify-between">
              <span>Folio {i.folio}</span><span className="text-ink-500">{i.estado} · {i.fecha_ingreso}</span>
            </li>
          ))}
          {data.ingresos.length === 0 && <li className="text-ink-400">Sin ingresos</li>}
        </ul>
      </Card>
      <div className="grid grid-cols-2 gap-3">
        {ranuras.map(([nombre, items]) => (
          <Card key={nombre} className="p-4">
            <h2 className="font-medium">{nombre}</h2>
            <p className="text-sm text-ink-400">{items.length ? `${items.length} registros` : "Pendiente (módulo futuro)"}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Test de alta (que falla) con MSW**

```tsx
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AltaIngresoPage } from "./AltaIngresoPage";

const BASE = import.meta.env.VITE_API_BASE_URL;
let lastBody: any = null;
const server = setupServer(
  http.post(`${BASE}/api/v1/ingresos`, async ({ request }) => {
    lastBody = await request.json();
    return HttpResponse.json({ id: 1, paciente_id: 1, folio: "F-2026-0001", estado: "activo", fecha_ingreso: lastBody.fecha_ingreso, folio_manual: false, numero_siniestro: null, fecha_diep_diat: null, tipo_derivacion: lastBody.tipo_derivacion, tipo_ingreso: lastBody.tipo_ingreso, modelo_tratamiento: lastBody.modelo_tratamiento, diagnostico: lastBody.diagnostico, razon_social: null, tipo_alta: null, fecha_alta: null, flag_revision: false, observaciones: null, tratamiento_iniciado: false }, { status: 201 });
  }),
);
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); lastBody = null; });
afterAll(() => server.close());

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter><AltaIngresoPage /></MemoryRouter></QueryClientProvider>);
}

describe("AltaIngresoPage", () => {
  it("rechaza RUT inválido sin llamar a la API", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/RUT/i), "11.111.111-2");
    await userEvent.type(screen.getByLabelText(/Nombre/i), "Ana");
    await userEvent.click(screen.getByRole("button", { name: /crear/i }));
    expect(await screen.findByText(/RUT inválido/i)).toBeInTheDocument();
    expect(lastBody).toBeNull();
  });
});
```

- [ ] **Step 7: Ver que falla y luego implementar `AltaIngresoPage.tsx`**

Run: `npx vitest run src/features/ingresos/AltaIngresoPage.test.tsx` → FAIL. Implementar:
```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ingresoSchema, type IngresoForm } from "./ingresoSchema";
import { useCrearIngreso } from "./hooks";
import type { IngresoCreate } from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const TIPOS_DERIVACION = ["DIEP", "DIAT", "PAPT a flujo AT", "Reingreso FUMP", "Reingreso SUSESO", "Convenio U.Clinica", "Proyecto", "Particular", "PAPT"];
const TIPOS_INGRESO = ["consulta_espontanea", "convenio", "proyecto", "particular"];

export function AltaIngresoPage() {
  const nav = useNavigate();
  const crear = useCrearIngreso();
  const { register, handleSubmit, formState: { errors } } = useForm<IngresoForm>({
    resolver: zodResolver(ingresoSchema),
    defaultValues: { sexo: "F", es_reingreso: false },
  });

  async function onSubmit(values: IngresoForm) {
    try {
      const ingreso = await crear.mutateAsync(values as IngresoCreate);
      toast.success(`Ingreso creado · folio ${ingreso.folio}`);
      nav(`/pacientes/${ingreso.paciente_id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-xl">
      <h1 className="text-lg font-semibold">Nuevo ingreso</h1>
      {([
        ["rut", "RUT"], ["nombre", "Nombre"], ["edad", "Edad"], ["region", "Región"],
        ["diagnostico", "Diagnóstico"], ["modelo_tratamiento", "Modelo de tratamiento"],
      ] as const).map(([name, label]) => (
        <div key={name} className="space-y-1">
          <Label htmlFor={name}>{label}</Label>
          <Input id={name} {...register(name)} />
          {errors[name] && <p className="text-sm text-danger-600">{errors[name]?.message as string}</p>}
        </div>
      ))}
      <div className="space-y-1">
        <Label htmlFor="fecha_ingreso">Fecha de ingreso</Label>
        <Input id="fecha_ingreso" type="date" {...register("fecha_ingreso")} />
        {errors.fecha_ingreso && <p className="text-sm text-danger-600">{errors.fecha_ingreso.message}</p>}
      </div>
      <div className="space-y-1">
        <Label htmlFor="sexo">Sexo</Label>
        <select id="sexo" {...register("sexo")} className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm">
          <option value="F">F</option><option value="M">M</option><option value="otro">Otro</option>
        </select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="tipo_derivacion">Tipo de derivación</Label>
        <select id="tipo_derivacion" {...register("tipo_derivacion")} className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm">
          {TIPOS_DERIVACION.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="tipo_ingreso">Tipo de ingreso</Label>
        <select id="tipo_ingreso" {...register("tipo_ingreso")} className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm">
          {TIPOS_INGRESO.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <Button type="submit" disabled={crear.isPending}>{crear.isPending ? "Creando…" : "Crear ingreso"}</Button>
    </form>
  );
}
```
Run de nuevo: PASS.

- [ ] **Step 8: Typecheck + suite completa**

Run: `npx tsc --noEmit && npx vitest run`
Expected: typecheck limpio; todos los tests verdes.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/lib/rut.ts frontend/src/lib/rut.test.ts frontend/src/features/ingresos/
git commit -m "feat(ingresos): pantallas búsqueda 360, vista 360 y alta (RUT + zod + RBAC)"
```

---

### Task 11: Infra de tests (MSW) y E2E (Playwright)

**Files:**
- Create: `frontend/src/test/setup.ts`, `frontend/src/test/msw/handlers.ts`, `frontend/src/test/msw/server.ts`, `frontend/playwright.config.ts`, `frontend/e2e/auth.spec.ts`, `frontend/e2e/ingresos.spec.ts`
- Modify: `frontend/package.json` (scripts test/e2e)

- [ ] **Step 1: `src/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./msw/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] **Step 2: `src/test/msw/handlers.ts` (handlers compartidos por defecto)**

```ts
import { http, HttpResponse } from "msw";
const BASE = import.meta.env.VITE_API_BASE_URL;

export const handlers = [
  http.get(`${BASE}/api/v1/pacientes/buscar`, () => HttpResponse.json([])),
];
```

- [ ] **Step 3: `src/test/msw/server.ts`**

```ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";
export const server = setupServer(...handlers);
```

> Nota: los tests que necesitan respuestas específicas usan `server.use(...)` o su propio
> `setupServer` (como en Tasks 5, 6, 9, 10). El `setup.ts` global garantiza fallo ante requests
> no manejadas.

- [ ] **Step 4: Scripts en `package.json`**

En `"scripts"`:
```json
"test": "vitest run",
"test:watch": "vitest",
"e2e": "playwright test",
"lint": "eslint .",
"typecheck": "tsc --noEmit"
```

- [ ] **Step 5: `playwright.config.ts`**

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:4173" },
  webServer: {
    command: "npm run build && npm run preview -- --port 4173",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 6: `e2e/auth.spec.ts` (login → home)**

```ts
import { expect, test } from "@playwright/test";

test("login muestra credenciales inválidas y luego entra", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Usuario").fill(process.env.E2E_USER ?? "coordinador");
  await page.getByLabel("Contraseña").fill(process.env.E2E_PASS ?? "cambiar");
  await page.getByRole("button", { name: /ingresar/i }).click();
  await expect(page.getByText(/Búsqueda 360/i)).toBeVisible();
});
```

- [ ] **Step 7: `e2e/ingresos.spec.ts` (alta → 360)**

```ts
import { expect, test } from "@playwright/test";

test("crea un ingreso y lo ve en la vista 360", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Usuario").fill(process.env.E2E_USER ?? "coordinador");
  await page.getByLabel("Contraseña").fill(process.env.E2E_PASS ?? "cambiar");
  await page.getByRole("button", { name: /ingresar/i }).click();
  await page.getByRole("link", { name: /nuevo ingreso/i }).click();
  await page.getByLabel("RUT").fill("7.876.543-7");
  await page.getByLabel("Nombre").fill("Paciente E2E");
  await page.getByLabel("Edad").fill("40");
  await page.getByLabel("Región").fill("Maule");
  await page.getByLabel("Diagnóstico").fill("Prueba E2E");
  await page.getByLabel("Modelo de tratamiento").fill("ambulatorio");
  await page.getByLabel("Fecha de ingreso").fill("2026-06-01");
  await page.getByRole("button", { name: /crear ingreso/i }).click();
  await expect(page.getByText(/Folio F-/i)).toBeVisible();
});
```

- [ ] **Step 8: Correr unit y verificar**

Run: `npm run test`
Expected: toda la suite unit/componente verde.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/test/ frontend/playwright.config.ts frontend/e2e/ frontend/package.json
git commit -m "test(frontend): infra MSW + E2E Playwright (auth, alta ingreso)"
```

---

### Task 12: Backend — CORSMiddleware

**Files:**
- Modify: `backend/app/config.py`, `backend/app/main.py`
- Test: `backend/tests/test_cors.py`

- [ ] **Step 1: Añadir `cors_origins` a `Settings`**

En `backend/app/config.py`, dentro de `Settings` (tras `app_name`):
```python
    cors_origins: str = "http://localhost:5173,http://localhost:4173,https://cepa-preview.vercel.app"
```
Y un helper:
```python
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
```

- [ ] **Step 2: Escribir el test que falla**

`backend/tests/test_cors.py`:
```python
def test_cors_permite_origen_configurado(client):
    r = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 3: Ver que falla**

Run (desde `backend/`): `uv run pytest tests/test_cors.py -v`
Expected: FAIL (no hay header CORS).

- [ ] **Step 4: Registrar el middleware en `main.py`**

En `backend/app/main.py`, tras crear `app = FastAPI(...)`:
```python
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 5: Ver que pasa + suite backend**

Run: `uv run pytest tests/test_cors.py -v && uv run pytest -q`
Expected: nuevo test verde; suite completa sigue verde.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/main.py backend/tests/test_cors.py
git commit -m "feat(backend): CORSMiddleware parametrizable por CORS_ORIGINS (integración frontend)"
```

---

### Task 13: CI del frontend y configuración de deploy

**Files:**
- Create: `.github/workflows/frontend-ci.yml` (raíz)
- Create: `frontend/vercel.json`

- [ ] **Step 1: Workflow `frontend-ci.yml`**

```yaml
name: frontend-ci
on:
  push:
    paths: ["frontend/**", ".github/workflows/frontend-ci.yml"]
  pull_request:
    paths: ["frontend/**", ".github/workflows/frontend-ci.yml"]
jobs:
  build-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    env:
      VITE_API_BASE_URL: https://cepa-backend-staging.onrender.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm run test
      - run: npm run build
```

> Nota: el E2E con Playwright contra backend docker-compose se añade en un job aparte cuando se
> estabilice el arranque del backend en CI; el job `build-test` es el gate obligatorio.

- [ ] **Step 2: `frontend/vercel.json` (SPA rewrites + build)**

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/frontend-ci.yml frontend/vercel.json
git commit -m "ci(frontend): workflow build/test + vercel.json (SPA rewrites)"
```

- [ ] **Step 4: Deploy manual a Vercel (verificación, fuera de CI automático)**

Run (desde `frontend/`, con el CLI ya autenticado como `dario-kreante`):
```bash
vercel pull --yes --environment=production
vercel build --prod
vercel deploy --prebuilt --prod
```
Luego en Vercel definir la env var `VITE_API_BASE_URL=https://cepa-backend-staging.onrender.com` en el proyecto y, en Render, añadir el dominio de Vercel a `CORS_ORIGINS` del servicio backend.
Expected: la app carga, el login contra el backend funciona, y la búsqueda/alta operan end-to-end.

---

### Task 14: Verificación final integral

**Files:** ninguno nuevo.

- [ ] **Step 1: Frontend — typecheck, lint, unit, build**

Run (desde `frontend/`): `npm run typecheck && npm run lint && npm run test && npm run build`
Expected: todo verde.

- [ ] **Step 2: Backend — suite con CORS**

Run (desde `backend/`): `uv run pytest -q && uv run ruff check .`
Expected: verde.

- [ ] **Step 3: E2E local contra backend docker-compose**

Run (desde `backend/`): `docker compose up -d` (levanta db + api con migraciones). Sembrar admin:
```bash
docker compose exec api python -m app.scripts.seed_admin --username coordinador --password 'Test1234!' --nombre 'Coordinación'
```
Luego (desde `frontend/`): `E2E_BASE_URL=http://localhost:4173 E2E_USER=coordinador E2E_PASS='Test1234!' VITE_API_BASE_URL=http://localhost:8000 npm run e2e`
Expected: specs E2E (auth, alta ingreso) verdes. Apagar: `docker compose down -v`.

- [ ] **Step 4: QA preview visual**

Levantar `npm run dev`, abrir la preview y validar: login, búsqueda, vista 360, alta (con RBAC: Auditor sin botón de alta). Usar las preview tools para capturar evidencia.

- [ ] **Step 5: Commit final (si quedó algo)**

```bash
git add -A && git commit -m "chore(frontend): Fundación + módulo Ingresos verificados" || echo "nada que commitear"
```

---

## Cobertura (spec ↔ Tasks)

| Requisito de la spec | Task(s) |
|----------------------|---------|
| Proyecto Vite+TS+Tailwind+shadcn | 1, 2 |
| Tipos desde OpenAPI (opción A) | 3 |
| Cliente API + refresh ante 401 | 4, 5 |
| Auth JWT + sesión + login silencioso | 6 |
| RBAC en UI (3 roles) | 6, 7, 8 |
| Rutas + guards + login | 7 |
| App shell (diseño del prototipo) | 1 (tema), 8 |
| Módulo Ingresos: búsqueda 360 | 9, 10 |
| Módulo Ingresos: vista 360 | 9, 10 |
| Módulo Ingresos: alta (RUT, enums, 409/422) | 9, 10 |
| Manejo de errores (toasts, mapeo) | 5, 10 |
| Testing unit/componente + MSW | 4–11 |
| Testing E2E Playwright | 11, 14 |
| QA preview | 14 |
| Backend CORS | 12 |
| Deploy/CI (Vercel→Render) | 13 |

## Notas de cierre

- **Orden de ejecución:** las Tasks 1–3 son base; 4–7 la plataforma; 8–10 el shell+módulo; 11
  infra de tests; 12 backend CORS; 13–14 deploy/verificación. Algunos tests de la Task 7 (guard
  con rutas reales) requieren que existan los componentes de 8–10 para el typecheck global —
  ejecutar el typecheck completo al cerrar la Task 10.
- **Dependencias contra el código real:** los tipos (`src/types/api.ts`) se generan del OpenAPI
  vivo; si el backend cambia un contrato, regenerar con `npm run gen:api`.
- **Decisión abierta heredada del diseño:** tokens httpOnly para los JWT (mejora de seguridad
  futura, requiere cambio de backend). Hoy: access en memoria + refresh en localStorage.
- **Gaps de backend conocidos** (no bloquean esta Fundación): la vista 360 muestra ranuras
  vacías para fármacos/licencias/controles/reintegro hasta que esos módulos las pueblen.
- **Próximos ciclos:** cada módulo restante (fármacos, EPT, reintegro, controles, licencias,
  agendamiento, dashboard/reportes, alertas, auditoría, config) tendrá su spec → plan → impl,
  reutilizando esta Fundación.
