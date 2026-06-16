/**
 * Tests for LicenciaControlDialog (wired via ControlesPage)
 *
 * Covers:
 *  1. Validation: tiene_licencia checked but required fields missing ⇒ submit BLOCKED.
 *  2. Validation: gaf = 150 ⇒ BLOCKED (range error), PATCH NOT called.
 *  3. Valid case: tiene_licencia true + all required fields ⇒ PATCH fires with correct body;
 *     refetched row reflects the reposo badge.
 *  4. tiene_licencia false ⇒ licencia fields sent as null.
 *  5. RBAC: Auditor does NOT see the "Licencia/RECA" action.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
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

/** Open the LicenciaControlDialog for the mock control. */
async function openLicenciaDialog(
  user: ReturnType<typeof userEvent.setup>,
  controlId = MOCK_CONTROL.id,
) {
  await waitFor(
    () => expect(screen.getByText("Dra. Ana Ruiz")).toBeInTheDocument(),
    { timeout: 3000 },
  );

  const btn = await screen.findByTestId(`btn-licencia-reca-${controlId}`);
  await user.click(btn);

  // Dialog should be open
  await screen.findByRole("dialog");
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("LicenciaControlDialog — validación: tiene_licencia true sin campos requeridos", () => {
  it("submit BLOQUEADO: muestra errores de validación y PATCH NO se llama", async () => {
    const patchSpy = vi.fn();

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json([MOCK_CONTROL]),
      ),
      http.patch(
        `${BASE}/api/v1/controles-medicos/:controlId/licencia`,
        () => {
          patchSpy();
          return HttpResponse.json(MOCK_CONTROL);
        },
      ),
    ]);

    await openLicenciaDialog(user);

    // Check tiene_licencia checkbox — required fields become mandatory
    const checkbox = screen.getByRole("checkbox", {
      name: /Tiene licencia médica/i,
    });
    await user.click(checkbox);

    // Submit without filling required fields
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Validation errors should appear
    await waitFor(() => {
      expect(
        screen.getByText(/El resumen del término de licencia médica es requerido/i),
      ).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(
        screen.getByText(/El total de días de licencia médica es requerido/i),
      ).toBeInTheDocument();
    });

    // PATCH must NOT have been called
    expect(patchSpy).not.toHaveBeenCalled();
  });
});

describe("LicenciaControlDialog — validación: GAF fuera de rango", () => {
  it("gaf=150 BLOQUEADO: error de rango visible y PATCH NO se llama", async () => {
    const patchSpy = vi.fn();

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json([MOCK_CONTROL]),
      ),
      http.patch(
        `${BASE}/api/v1/controles-medicos/:controlId/licencia`,
        () => {
          patchSpy();
          return HttpResponse.json(MOCK_CONTROL);
        },
      ),
    ]);

    await openLicenciaDialog(user);

    // Scope to dialog to avoid ambiguity
    const dialog = screen.getByRole("dialog");
    const d = within(dialog);

    // Fill gaf with an out-of-range value (150)
    const gafInput = d.getByLabelText(/GAF/i);
    await user.clear(gafInput);
    await user.type(gafInput, "150");

    // Submit
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Range error must appear
    await waitFor(() => {
      expect(
        screen.getByText(/GAF debe estar entre 0 y 100/i),
      ).toBeInTheDocument();
    });

    // PATCH must NOT have been called
    expect(patchSpy).not.toHaveBeenCalled();
  });
});

describe("LicenciaControlDialog — alta válida: tiene_licencia true con todos los campos", () => {
  it("PATCH /api/v1/controles-medicos/{control_id}/licencia se dispara con el body correcto y la fila muestra reposo", async () => {
    const patchSpy = vi.fn();

    const MOCK_CONTROL_UPDATED: ControlMedicoRead = {
      ...MOCK_CONTROL,
      tiene_licencia: true,
      resumen_termino_lm: "Término por enfermedad respiratoria",
      total_dias_lm: 15,
      tipo_licencia: "1",
      tipo_reposo: "total",
      gaf: 65,
      estado_reca: "aprobado",
    };

    const state = { controles: [MOCK_CONTROL] as ControlMedicoRead[] };

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json(state.controles),
      ),
      http.patch(
        `${BASE}/api/v1/controles-medicos/:controlId/licencia`,
        async ({ request }) => {
          const body = await request.json();
          patchSpy(body);
          state.controles = [MOCK_CONTROL_UPDATED];
          return HttpResponse.json(MOCK_CONTROL_UPDATED);
        },
      ),
    ]);

    await openLicenciaDialog(user);

    // Scope all queries to the open dialog to avoid ambiguity with page filters
    const dialog = screen.getByRole("dialog");
    const d = within(dialog);

    // Check tiene_licencia
    const checkbox = d.getByRole("checkbox", {
      name: /Tiene licencia médica/i,
    });
    await user.click(checkbox);

    // Fill resumen_termino_lm
    const resumenInput = d.getByLabelText(/Resumen término licencia médica/i);
    await user.type(resumenInput, "Término por enfermedad respiratoria");

    // Fill total_dias_lm
    const diasInput = d.getByLabelText(/Total días licencia médica/i);
    await user.clear(diasInput);
    await user.type(diasInput, "15");

    // Select tipo_licencia
    const tipoLicenciaSelect = d.getByLabelText(/Tipo de licencia/i);
    await user.selectOptions(tipoLicenciaSelect, "1");

    // Select tipo_reposo
    const tipoReposoSelect = d.getByLabelText(/Tipo de reposo/i);
    await user.selectOptions(tipoReposoSelect, "total");

    // Fill gaf
    const gafInput = d.getByLabelText(/GAF/i);
    await user.clear(gafInput);
    await user.type(gafInput, "65");

    // Select estado_reca
    const estadoRecaSelect = d.getByLabelText(/Estado RECA/i);
    await user.selectOptions(estadoRecaSelect, "aprobado");

    // Submit
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // PATCH fired once with correct body
    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledOnce();
    });

    const sentBody = patchSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.tiene_licencia).toBe(true);
    expect(sentBody.resumen_termino_lm).toBe(
      "Término por enfermedad respiratoria",
    );
    expect(sentBody.total_dias_lm).toBe(15);
    expect(sentBody.tipo_licencia).toBe("1");
    expect(sentBody.tipo_reposo).toBe("total");
    expect(sentBody.gaf).toBe(65);
    expect(sentBody.estado_reca).toBe("aprobado");

    // After success, toast confirms the update
    await waitFor(
      () =>
        expect(
          screen.getByText(/Licencia y RECA actualizados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // After invalidation + refetch, the table row reflects the updated data.
    // We check that the refetched reposo badge ("Total") appears in the table.
    // The filter selects also contain "Total" as an <option>, so we look for
    // the Badge div (rendered as <div class="...badge...">Total</div>) specifically.
    await waitFor(
      () => {
        const allDivs = document.querySelectorAll("div");
        const totalBadge = Array.from(allDivs).find(
          (el) =>
            el.textContent?.trim() === "Total" &&
            el.className.includes("inline-flex"),
        );
        expect(totalBadge).toBeDefined();
      },
      { timeout: 3000 },
    );
  });
});

describe("LicenciaControlDialog — tiene_licencia false: licencia fields enviados como null", () => {
  it("body contiene total_dias_lm=null, tipo_licencia=null, etc.", async () => {
    const patchSpy = vi.fn();

    const MOCK_CONTROL_UPDATED: ControlMedicoRead = {
      ...MOCK_CONTROL,
      tiene_licencia: false,
      resumen_termino_lm: null,
      total_dias_lm: null,
      tipo_licencia: null,
      tipo_reposo: null,
      gaf: null,
    };

    const state = { controles: [MOCK_CONTROL] as ControlMedicoRead[] };

    const user = await setupPageWithPaciente(WRITER_TOKEN, [
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`,
        () => HttpResponse.json(state.controles),
      ),
      http.patch(
        `${BASE}/api/v1/controles-medicos/:controlId/licencia`,
        async ({ request }) => {
          const body = await request.json();
          patchSpy(body);
          state.controles = [MOCK_CONTROL_UPDATED];
          return HttpResponse.json(MOCK_CONTROL_UPDATED);
        },
      ),
    ]);

    await openLicenciaDialog(user);

    // tiene_licencia stays unchecked (false by default), just submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = (dialog as HTMLElement).querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // PATCH should fire
    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledOnce();
    });

    const sentBody = patchSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.tiene_licencia).toBe(false);
    expect(sentBody.total_dias_lm).toBeNull();
    expect(sentBody.tipo_licencia).toBeNull();
    expect(sentBody.tipo_reposo).toBeNull();
    expect(sentBody.resumen_termino_lm).toBeNull();
  });
});

describe("LicenciaControlDialog — RBAC", () => {
  it("Auditor NO ve el botón de acción 'Licencia/RECA' en las filas", async () => {
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
      screen.queryByTestId(`btn-licencia-reca-${MOCK_CONTROL.id}`),
    ).not.toBeInTheDocument();
  });
});
