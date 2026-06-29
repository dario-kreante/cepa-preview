/**
 * Tests for NuevoControlDialog (wired via ControlesPage)
 *
 * Covers:
 *  1. Valid alta → POST /api/v1/controles-medicos fires with correct ingreso_id,
 *     and the refetched list shows the new control.
 *  2. Validation: empty medico_tratante blocks submit (error shown, POST NOT called).
 *  3. RBAC: Auditor does NOT see "Nuevo control".
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
import { ControlesPage } from "./ControlesPage";
import type { ControlMedicoRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

// ── JWT tokens ───────────────────────────────────────────────────────────────

const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_PACIENTE = {
  id: 7,
  rut: "15.123.456-7",
  nombre: "María González",
  sexo: "F",
  edad: 45,
  region: "Metropolitana",
  comuna: "Santiago",
  telefono: "+56912345678",
  correo: "mgonzalez@example.com",
};

const MOCK_VISTA_360 = {
  paciente: MOCK_PACIENTE,
  ingresos: [
    {
      id: 10,
      paciente_id: 7,
      fecha_ingreso: "2026-01-15",
      diagnostico_ingreso: "Hipertensión",
      estado: "activo",
    },
  ],
};

const MOCK_CONTROL: ControlMedicoRead = {
  id: 300,
  ingreso_id: 10,
  fecha_control: "2026-06-10",
  semana_control: 21,
  medico_tratante: "Dra. Ana Ruiz",
  region_derivacion: "Valparaíso",
  proximo_control: null,
  proximo_agendado: false,
  tiene_licencia: false,
  resumen_termino_lm: null,
  total_dias_lm: null,
  tipo_licencia: null,
  tipo_reposo: null,
  gaf: null,
  estado_reca: null,
  observaciones: null,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderPage(token = WRITER_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <ControlesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Wire MSW base routes, render page, search and select the paciente. */
async function setupPageWithPaciente(
  token = WRITER_TOKEN,
  extraHandlers: Parameters<typeof server.use>[0][] = [],
) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
      HttpResponse.json([MOCK_PACIENTE]),
    ),
    http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
      HttpResponse.json(MOCK_VISTA_360),
    ),
    ...extraHandlers,
  );

  renderPage(token);
  const user = userEvent.setup();

  const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
  await user.type(input, "María");

  await waitFor(
    () => expect(screen.getByText("María González")).toBeInTheDocument(),
    { timeout: 3000 },
  );

  await user.click(screen.getByText("María González"));
  return user;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("NuevoControlDialog — alta válida", () => {
  it("POST /api/v1/controles-medicos se dispara con el ingreso_id correcto y la lista muestra el nuevo control", async () => {
    const postSpy = vi.fn();
    const state = { controles: [] as ControlMedicoRead[] };

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json(state.controles),
      ),
      http.post(
        `${BASE}/api/v1/controles-medicos`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.controles = [MOCK_CONTROL];
          return HttpResponse.json(MOCK_CONTROL, { status: 201 });
        },
      ),
    ]);

    // Wait for the button to be enabled (ingresoId resolved)
    const btnNuevoControl = await screen.findByRole("button", {
      name: /Nuevo control/i,
    });
    await waitFor(() => expect(btnNuevoControl).not.toBeDisabled(), {
      timeout: 3000,
    });

    // Open the dialog
    await user.click(btnNuevoControl);
    await screen.findByRole("dialog");

    // Fill the form
    await user.type(screen.getByLabelText(/Fecha del control/i), "2026-06-10");
    await user.type(screen.getByLabelText(/Médico tratante/i), "Dra. Ana Ruiz");
    await user.type(
      screen.getByLabelText(/Región de derivación/i),
      "Valparaíso",
    );

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // POST fired once
    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    // Body contains the correct ingreso_id (NOT a form field — injected by dialog)
    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.ingreso_id).toBe(10);
    expect(sentBody.fecha_control).toBe("2026-06-10");
    expect(sentBody.medico_tratante).toBe("Dra. Ana Ruiz");
    expect(sentBody.region_derivacion).toBe("Valparaíso");
    // semana_control must NOT be in the body
    expect(sentBody).not.toHaveProperty("semana_control");

    // After invalidation + refetch, the new control appears in the table
    await waitFor(
      () => expect(screen.getByText("Dra. Ana Ruiz")).toBeInTheDocument(),
      { timeout: 3000 },
    );
  });
});

describe("NuevoControlDialog — validación", () => {
  it("medico_tratante vacío bloquea el submit: error visible y POST NO se llama", async () => {
    const postSpy = vi.fn();

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json([]),
      ),
      http.post(`${BASE}/api/v1/controles-medicos`, () => {
        postSpy();
        return HttpResponse.json(MOCK_CONTROL, { status: 201 });
      }),
    ]);

    // Wait for button to be enabled
    const btnNuevoControl = await screen.findByRole("button", {
      name: /Nuevo control/i,
    });
    await waitFor(() => expect(btnNuevoControl).not.toBeDisabled(), {
      timeout: 3000,
    });

    await user.click(btnNuevoControl);
    await screen.findByRole("dialog");

    // Fill fecha_control and region_derivacion but leave medico_tratante empty
    await user.type(screen.getByLabelText(/Fecha del control/i), "2026-06-10");
    // medico_tratante intentionally left blank
    await user.type(
      screen.getByLabelText(/Región de derivación/i),
      "Metropolitana",
    );

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Validation error visible
    await waitFor(() => {
      expect(
        screen.getByText(/El médico tratante es requerido/i),
      ).toBeInTheDocument();
    });

    // POST must NOT have been called
    expect(postSpy).not.toHaveBeenCalled();
  });
});

describe("NuevoControlDialog — RBAC", () => {
  it("Auditor NO ve el botón 'Nuevo control'", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json([]),
      ),
    );

    renderPage(AUDITOR_TOKEN);

    // Page renders
    await screen.findByText(
      /Escribe un RUT, folio o nombre para buscar pacientes/i,
    );

    // The button should not be present at all
    expect(
      screen.queryByTestId("btn-nuevo-control"),
    ).not.toBeInTheDocument();
  });
});
