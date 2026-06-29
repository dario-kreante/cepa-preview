/**
 * EsquemaPanel tests
 *
 * Covers:
 *  1. Renders 2 indicaciones when data exists.
 *  2. Shows empty state when no indicaciones.
 *  3. Opens dialog, fills form, submits → mutation fires → list updates to 3 items.
 *  4. Validation: empty medicamento blocks submission, mutation not called.
 *  5. RBAC: Auditor does not see "Agregar indicación" button.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { EsquemaPanel } from "./EsquemaPanel";
import type { EsquemaIndicacionRead, RegistroFarmacologicoRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

// ── JWT tokens ───────────────────────────────────────────────────────────────

// role "Coordinacion" (writer)
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// role "Auditor" (read-only)
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_REGISTRO: RegistroFarmacologicoRead = {
  id: 1,
  ingreso_id: 10,
  medico_tratante: "Dra. Carmen López",
  estado_farmacologico: "activo",
  antecedentes_previos: null,
  tratamiento_previo: null,
  activo: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const MOCK_INDICACIONES: EsquemaIndicacionRead[] = [
  {
    id: 1,
    registro_id: 1,
    medicamento: "Enalapril",
    dosis: "10 mg",
    frecuencia: "c/24h",
    extra_sistema: false,
    vigente: true,
    created_at: "2026-06-01T00:00:00Z",
  },
  {
    id: 2,
    registro_id: 1,
    medicamento: "Losartán",
    dosis: "50 mg",
    frecuencia: "c/12h",
    extra_sistema: true,
    vigente: true,
    created_at: "2026-06-02T00:00:00Z",
  },
];

const MOCK_INDICACION_3: EsquemaIndicacionRead = {
  id: 3,
  registro_id: 1,
  medicamento: "Metformina",
  dosis: "850 mg",
  frecuencia: "c/8h",
  extra_sistema: false,
  vigente: true,
  created_at: "2026-06-03T00:00:00Z",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

interface RenderOptions {
  token?: string;
  registro?: RegistroFarmacologicoRead | null;
  indicaciones?: EsquemaIndicacionRead[];
}

function renderPanel({
  token = WRITER_TOKEN,
  registro = MOCK_REGISTRO,
  indicaciones = MOCK_INDICACIONES,
}: RenderOptions = {}) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  server.use(
    http.get(
      `${BASE}/api/v1/registro-farmacologico/:ingreso_id/esquema`,
      () => HttpResponse.json(indicaciones),
    ),
  );

  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <EsquemaPanel
            ingresoId={10}
            registro={registro}
            canWrite={
              // Derive from token role to stay in sync with real RBAC
              token === WRITER_TOKEN
            }
          />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return { qc };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("EsquemaPanel", () => {
  it("muestra 2 indicaciones cuando hay datos", async () => {
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Enalapril")).toBeInTheDocument();
      expect(screen.getByText("Losartán")).toBeInTheDocument();
    });

    // Dosis
    expect(screen.getByText("10 mg")).toBeInTheDocument();
    expect(screen.getByText("50 mg")).toBeInTheDocument();

    // Frecuencia (friendly labels)
    expect(screen.getByText("Cada 24 h")).toBeInTheDocument();
    expect(screen.getByText("Cada 12 h")).toBeInTheDocument();

    // Badges
    const vigenteBadges = screen.getAllByText("Vigente");
    expect(vigenteBadges.length).toBeGreaterThanOrEqual(2);

    // extra_sistema badge for Losartán
    expect(screen.getByText("Extra sistema")).toBeInTheDocument();
  });

  it("muestra empty state cuando no hay indicaciones", async () => {
    renderPanel({ indicaciones: [] });

    await waitFor(() => {
      expect(
        screen.getByText(/Sin indicaciones en el esquema/i),
      ).toBeInTheDocument();
    });
  });

  it("abre el dialog, rellena el formulario y llama a la mutación → mutation fires con datos correctos y refetch devuelve 3 items", async () => {
    const postSpy = vi.fn();

    // Mutable reference so the GET handler returns updated data after POST
    const state = { indicaciones: [...MOCK_INDICACIONES] };

    tokenStore.setAccess(WRITER_TOKEN);
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    server.use(
      http.get(
        `${BASE}/api/v1/registro-farmacologico/:ingreso_id/esquema`,
        () => HttpResponse.json(state.indicaciones),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:ingreso_id/esquema`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          // Mutate state so next GET returns 3 items
          state.indicaciones = [...MOCK_INDICACIONES, MOCK_INDICACION_3];
          return HttpResponse.json(MOCK_INDICACION_3, { status: 201 });
        },
      ),
    );

    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <Toaster />
            <EsquemaPanel
              ingresoId={10}
              registro={MOCK_REGISTRO}
              canWrite={true}
            />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const user = userEvent.setup();

    // Wait for the panel to load
    await waitFor(() => {
      expect(screen.getByText("Enalapril")).toBeInTheDocument();
    });

    // Open dialog
    const addBtn = screen.getByRole("button", { name: /Agregar indicación/i });
    await user.click(addBtn);

    // Wait for dialog
    await screen.findByRole("dialog");

    // Fill medicamento
    await user.type(screen.getByLabelText(/medicamento/i), "Metformina");

    // Fill dosis
    await user.type(screen.getByLabelText(/dosis/i), "850 mg");

    // Select frecuencia
    await user.selectOptions(screen.getByLabelText(/frecuencia/i), "c/8h");

    // Click submit button inside dialog (there is also the panel's "Agregar indicación" btn — use dialog context)
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector('button[type="submit"]') as HTMLElement;
    await user.click(submitBtn);

    // Wait for mutation to fire
    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.medicamento).toBe("Metformina");
    expect(sentBody.dosis).toBe("850 mg");
    expect(sentBody.frecuencia).toBe("c/8h");
    expect(sentBody.extra_sistema).toBe(false);

    // After mutation + cache invalidation, the refetch returns 3 items
    await waitFor(() => {
      expect(screen.getByText("Metformina")).toBeInTheDocument();
    });
  });

  it("bloquea el submit con medicamento vacío y NO llama la mutación", async () => {
    const postSpy = vi.fn();

    server.use(
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:ingreso_id/esquema`,
        () => {
          postSpy();
          return HttpResponse.json(MOCK_INDICACION_3, { status: 201 });
        },
      ),
    );

    renderPanel();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Enalapril")).toBeInTheDocument();
    });

    // Open dialog
    await user.click(screen.getByRole("button", { name: /Agregar indicación/i }));
    await screen.findByRole("dialog");

    // Leave medicamento empty; fill the rest
    await user.type(screen.getByLabelText(/dosis/i), "500 mg");
    await user.selectOptions(screen.getByLabelText(/frecuencia/i), "semanal");

    // Try to submit
    await user.click(screen.getByRole("button", { name: /Agregar indicación/i, hidden: false }));

    // Validation error shown
    await waitFor(() => {
      expect(
        screen.getByText(/El medicamento es requerido/i),
      ).toBeInTheDocument();
    });

    // Mutation must NOT have been called
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("Auditor NO ve el botón Agregar indicación", async () => {
    renderPanel({ token: AUDITOR_TOKEN });

    await waitFor(() => {
      expect(screen.getByText("Enalapril")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: /Agregar indicación/i }),
    ).not.toBeInTheDocument();
  });

  it("oculta el botón Agregar indicación cuando no hay registro", async () => {
    renderPanel({ registro: null });

    await waitFor(() => {
      expect(screen.getByText("Enalapril")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: /Agregar indicación/i }),
    ).not.toBeInTheDocument();
  });
});
