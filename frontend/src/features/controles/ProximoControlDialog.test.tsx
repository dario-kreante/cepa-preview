/**
 * Tests for ProximoControlDialog (wired via ControlesPage)
 *
 * Covers:
 *  1. Valid update → PATCH /api/v1/controles-medicos/{control_id}/proximo-control fires
 *     with the right body, and the refetched row shows the "Agendado" badge.
 *  2. Validation: empty proximo_control blocks submit (error visible, PATCH NOT called).
 *  3. RBAC: Auditor does NOT see the "Próximo control" action button.
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

const MOCK_CONTROL_UPDATED: ControlMedicoRead = {
  ...MOCK_CONTROL,
  proximo_control: "2026-07-15",
  proximo_agendado: true,
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

describe("ProximoControlDialog — alta válida", () => {
  it("PATCH /api/v1/controles-medicos/{control_id}/proximo-control se dispara con el body correcto y la fila muestra el badge Agendado", async () => {
    const patchSpy = vi.fn();
    const state = { controles: [MOCK_CONTROL] as ControlMedicoRead[] };

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json(state.controles),
      ),
      http.patch(
        `${BASE}/api/v1/controles-medicos/:controlId/proximo-control`,
        async ({ request }) => {
          const body = await request.json();
          patchSpy(body);
          state.controles = [MOCK_CONTROL_UPDATED];
          return HttpResponse.json(MOCK_CONTROL_UPDATED);
        },
      ),
    ]);

    // Wait for the control row to appear
    await waitFor(
      () => expect(screen.getByText("Dra. Ana Ruiz")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Click the "Próximo control" row action button
    const actionBtn = await screen.findByTestId(`btn-proximo-control-${MOCK_CONTROL.id}`);
    await user.click(actionBtn);

    // Dialog opens
    await screen.findByRole("dialog");

    // Fill the date
    const dateInput = screen.getByLabelText(/Fecha del próximo control/i);
    await user.type(dateInput, "2026-07-15");

    // Check the agendado checkbox
    const checkbox = screen.getByRole("checkbox", {
      name: /Próximo control agendado/i,
    });
    await user.click(checkbox);

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // PATCH fired once with correct body
    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledOnce();
    });

    const sentBody = patchSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.proximo_control).toBe("2026-07-15");
    expect(sentBody.proximo_agendado).toBe(true);

    // After invalidation + refetch, the Agendado badge appears
    await waitFor(
      () => expect(screen.getByText("Agendado")).toBeInTheDocument(),
      { timeout: 3000 },
    );
  });
});

describe("ProximoControlDialog — validación", () => {
  it("proximo_control vacío bloquea el submit: error visible y PATCH NO se llama", async () => {
    const patchSpy = vi.fn();

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json([MOCK_CONTROL]),
      ),
      http.patch(
        `${BASE}/api/v1/controles-medicos/:controlId/proximo-control`,
        () => {
          patchSpy();
          return HttpResponse.json(MOCK_CONTROL_UPDATED);
        },
      ),
    ]);

    // Wait for the control row to appear
    await waitFor(
      () => expect(screen.getByText("Dra. Ana Ruiz")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Click the row action button
    const actionBtn = await screen.findByTestId(`btn-proximo-control-${MOCK_CONTROL.id}`);
    await user.click(actionBtn);

    // Dialog opens
    await screen.findByRole("dialog");

    // Leave proximo_control empty and submit directly
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Validation error visible
    await waitFor(() => {
      expect(
        screen.getByText(/La fecha del próximo control es requerida/i),
      ).toBeInTheDocument();
    });

    // PATCH must NOT have been called
    expect(patchSpy).not.toHaveBeenCalled();
  });
});

describe("ProximoControlDialog — RBAC", () => {
  it("Auditor NO ve el botón de acción 'Próximo control' en las filas", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json([MOCK_CONTROL]),
      ),
    );

    renderPage(AUDITOR_TOKEN);

    const user = userEvent.setup();
    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await user.type(input, "María");

    await waitFor(
      () => expect(screen.getByText("María González")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await user.click(screen.getByText("María González"));

    // Wait for controles to load
    await waitFor(
      () => expect(screen.getByText("Dra. Ana Ruiz")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // The action button must not be present
    expect(
      screen.queryByTestId(`btn-proximo-control-${MOCK_CONTROL.id}`),
    ).not.toBeInTheDocument();
  });
});
