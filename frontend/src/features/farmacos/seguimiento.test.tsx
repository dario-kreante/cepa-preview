/**
 * Tests for SeguimientoPanel + NuevoSeguimientoDialog + "Generar alertas de revisión"
 *
 * Covers:
 *  1. Conditional validation: cambio_esquema checked + detalle_cambio empty → blocked, spy NOT called.
 *  2. Conditional validation: disminucion_farmacos checked + plan_disminucion empty → blocked, spy NOT called.
 *  3. Valid submit (both flags false) → POST fires, refetch shows new seguimiento.
 *  4. Valid submit (flags true with detail filled) → POST fires.
 *  5. "Generar alertas de revisión": fires POST and toast shows correct count.
 *  6. RBAC: Auditor sees neither "Agregar seguimiento" nor "Generar alertas de revisión".
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
import { FarmacosPage } from "./FarmacosPage";
import type { RegistroFarmacologicoRead, SeguimTratamientoRead } from "./api";

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
  nombre: "Juan Pérez",
  sexo: "M",
  edad: 52,
  region: "Metropolitana",
  comuna: "Providencia",
  telefono: "+56911223344",
  correo: "jperez@example.com",
};

const MOCK_VISTA_360 = {
  paciente: MOCK_PACIENTE,
  ingresos: [
    {
      id: 10,
      paciente_id: 7,
      fecha_ingreso: "2026-01-15",
      diagnostico_ingreso: "Fractura de cadera",
      estado: "activo",
    },
  ],
};

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

const MOCK_SEGUIMIENTO: SeguimTratamientoRead = {
  id: 1,
  registro_id: 1,
  disminucion_farmacos: false,
  plan_disminucion: null,
  cambio_esquema: false,
  detalle_cambio: null,
  observaciones: "Primera revisión sin cambios",
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
};

const MOCK_SEGUIMIENTO_CON_FLAGS: SeguimTratamientoRead = {
  id: 2,
  registro_id: 1,
  disminucion_farmacos: true,
  plan_disminucion: "Reducir dosis gradualmente",
  cambio_esquema: true,
  detalle_cambio: "Cambiar a monoterapia",
  observaciones: null,
  created_at: "2026-06-10T00:00:00Z",
  updated_at: "2026-06-10T00:00:00Z",
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
          <FarmacosPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Wire base MSW handlers, render page, search for Juan Pérez, and select him. */
async function setupPageWithPaciente(
  token = WRITER_TOKEN,
  extraHandlers: Parameters<typeof server.use>[0][] = [],
) {
  renderPage(token);
  const user = userEvent.setup();

  const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
  await user.type(input, "Juan");

  await waitFor(
    () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
    { timeout: 3000 },
  );

  // Register any extra handlers before interacting further
  if (extraHandlers.length > 0) {
    server.use(...extraHandlers);
  }

  await user.click(screen.getByText("Juan Pérez"));
  return user;
}

/** Wire the standard handlers needed by most tests. */
function wireBaseHandlers(seguimientos: SeguimTratamientoRead[] = []) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
      HttpResponse.json([MOCK_PACIENTE]),
    ),
    http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
      HttpResponse.json(MOCK_VISTA_360),
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
      HttpResponse.json(MOCK_REGISTRO),
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
      HttpResponse.json(seguimientos),
    ),
  );
}

// ── 1. Conditional validation: cambio_esquema + empty detalle_cambio ─────────

describe("NuevoSeguimientoDialog — validación condicional", () => {
  it("bloquea submit con cambio_esquema marcado y detalle_cambio vacío → mutation NO llamada", async () => {
    const postSpy = vi.fn();

    wireBaseHandlers();
    server.use(
      http.post(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () => {
        postSpy();
        return HttpResponse.json(MOCK_SEGUIMIENTO, { status: 201 });
      }),
    );

    const user = await setupPageWithPaciente();

    // Wait for panel to load
    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Wait for "Sin seguimientos registrados" empty state
    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Open dialog
    const addBtn = screen.getByRole("button", { name: /Agregar seguimiento/i });
    await user.click(addBtn);
    await screen.findByRole("dialog");

    // Check "Cambio de esquema" checkbox — detalle_cambio stays empty
    const cambioCheckbox = screen.getByRole("checkbox", {
      name: /Cambio de esquema/i,
    });
    await user.click(cambioCheckbox);

    // Submit without filling detalle_cambio
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Validation error shown
    await waitFor(() => {
      expect(
        screen.getByText(
          /El detalle del cambio es requerido cuando se indica cambio de esquema/i,
        ),
      ).toBeInTheDocument();
    });

    // Mutation must NOT have been called
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("bloquea submit con disminucion_farmacos marcado y plan_disminucion vacío → mutation NO llamada", async () => {
    const postSpy = vi.fn();

    wireBaseHandlers();
    server.use(
      http.post(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () => {
        postSpy();
        return HttpResponse.json(MOCK_SEGUIMIENTO, { status: 201 });
      }),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Open dialog
    await user.click(screen.getByRole("button", { name: /Agregar seguimiento/i }));
    await screen.findByRole("dialog");

    // Check "Disminución de fármacos" — plan_disminucion stays empty
    const disminucionCheckbox = screen.getByRole("checkbox", {
      name: /Disminución de fármacos/i,
    });
    await user.click(disminucionCheckbox);

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Validation error shown
    await waitFor(() => {
      expect(
        screen.getByText(
          /El plan de disminución es requerido cuando se indica disminución de fármacos/i,
        ),
      ).toBeInTheDocument();
    });

    expect(postSpy).not.toHaveBeenCalled();
  });

  // ── 3. Valid submit (both flags false) ──────────────────────────────────────

  it("submit válido (flags false) → POST dispara y el panel muestra el nuevo seguimiento", async () => {
    const postSpy = vi.fn();
    const state = { seguimientos: [] as SeguimTratamientoRead[] };

    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(MOCK_REGISTRO),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json(state.seguimientos),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:id/seguimiento`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.seguimientos = [MOCK_SEGUIMIENTO];
          return HttpResponse.json(MOCK_SEGUIMIENTO, { status: 201 });
        },
      ),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Open dialog
    await user.click(screen.getByRole("button", { name: /Agregar seguimiento/i }));
    await screen.findByRole("dialog");

    // Fill observaciones — flags remain unchecked
    await user.type(
      screen.getByLabelText(/Observaciones/i),
      "Primera revisión sin cambios",
    );

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.disminucion_farmacos).toBe(false);
    expect(sentBody.cambio_esquema).toBe(false);
    expect(sentBody.observaciones).toBe("Primera revisión sin cambios");

    // After mutation + cache invalidation, the panel should show the seguimiento data
    await waitFor(
      () =>
        expect(
          screen.getByText("Primera revisión sin cambios"),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );
  });

  // ── 4. Valid submit (flags true with detail filled) ─────────────────────────

  it("submit válido con flags true y detalles → POST dispara con datos correctos", async () => {
    const postSpy = vi.fn();
    const state = { seguimientos: [] as SeguimTratamientoRead[] };

    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(MOCK_REGISTRO),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json(state.seguimientos),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:id/seguimiento`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.seguimientos = [MOCK_SEGUIMIENTO_CON_FLAGS];
          return HttpResponse.json(MOCK_SEGUIMIENTO_CON_FLAGS, { status: 201 });
        },
      ),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await user.click(screen.getByRole("button", { name: /Agregar seguimiento/i }));
    await screen.findByRole("dialog");

    // Check disminucion_farmacos and fill plan
    await user.click(
      screen.getByRole("checkbox", { name: /Disminución de fármacos/i }),
    );
    await user.type(
      screen.getByLabelText(/Plan de disminución/i),
      "Reducir dosis gradualmente",
    );

    // Check cambio_esquema and fill detalle
    await user.click(
      screen.getByRole("checkbox", { name: /Cambio de esquema/i }),
    );
    await user.type(
      screen.getByLabelText(/Detalle del cambio/i),
      "Cambiar a monoterapia",
    );

    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.disminucion_farmacos).toBe(true);
    expect(sentBody.plan_disminucion).toBe("Reducir dosis gradualmente");
    expect(sentBody.cambio_esquema).toBe(true);
    expect(sentBody.detalle_cambio).toBe("Cambiar a monoterapia");
  });
});

// ── 5. Generar alertas de revisión ───────────────────────────────────────────

describe("Generar alertas de revisión", () => {
  it("click en 'Generar alertas de revisión' dispara POST y toast con el número correcto", async () => {
    const MOCK_ALERTAS = [
      { id: 1, receta_id: 1, tipo: "revision", mensaje: "Revisar receta" },
      { id: 2, receta_id: 2, tipo: "revision", mensaje: "Revisar receta" },
      { id: 3, receta_id: 3, tipo: "revision", mensaje: "Revisar receta" },
    ];

    const alertasSpy = vi.fn();

    wireBaseHandlers();
    server.use(
      http.post(
        `${BASE}/api/v1/registro-farmacologico/recetas/alertas/generar`,
        () => {
          alertasSpy();
          return HttpResponse.json(MOCK_ALERTAS, { status: 201 });
        },
      ),
    );

    renderPage(WRITER_TOKEN);
    const user = userEvent.setup();

    // The button should be available right away (global action, no ingreso needed)
    const alertasBtn = await screen.findByRole("button", {
      name: /Generar alertas de revisión/i,
    });
    expect(alertasBtn).toBeInTheDocument();
    await user.click(alertasBtn);

    await waitFor(() => {
      expect(alertasSpy).toHaveBeenCalledOnce();
    });

    // Toast should reflect the count
    await waitFor(
      () =>
        expect(
          screen.getByText(/3 alertas de revisión generadas/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );
  });
});

// ── 7. Flag-detail coercion: detail nulled when flag is unchecked ─────────────

describe("NuevoSeguimientoDialog — coerción de detalle cuando flag desmarcado", () => {
  it("cambio_esquema desmarcado → detalle_cambio enviado como null aunque se haya escrito texto", async () => {
    const postSpy = vi.fn();
    const state = { seguimientos: [] as SeguimTratamientoRead[] };

    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(MOCK_REGISTRO),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json(state.seguimientos),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:id/seguimiento`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.seguimientos = [MOCK_SEGUIMIENTO];
          return HttpResponse.json(MOCK_SEGUIMIENTO, { status: 201 });
        },
      ),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Open dialog
    await user.click(screen.getByRole("button", { name: /Agregar seguimiento/i }));
    await screen.findByRole("dialog");

    // Check "Cambio de esquema" and type text in detalle_cambio
    await user.click(
      screen.getByRole("checkbox", { name: /Cambio de esquema/i }),
    );
    await user.type(
      screen.getByLabelText(/Detalle del cambio/i),
      "texto que debería ser descartado",
    );

    // Now UNCHECK "Cambio de esquema" — detail text remains in the field
    await user.click(
      screen.getByRole("checkbox", { name: /Cambio de esquema/i }),
    );

    // Fill observaciones so the form is otherwise valid
    await user.type(
      screen.getByLabelText(/Observaciones/i),
      "Sin cambios al final",
    );

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.cambio_esquema).toBe(false);
    expect(sentBody.detalle_cambio).toBeNull();
  });

  it("disminucion_farmacos desmarcado → plan_disminucion enviado como null aunque se haya escrito texto", async () => {
    const postSpy = vi.fn();
    const state = { seguimientos: [] as SeguimTratamientoRead[] };

    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(MOCK_REGISTRO),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json(state.seguimientos),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:id/seguimiento`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.seguimientos = [MOCK_SEGUIMIENTO];
          return HttpResponse.json(MOCK_SEGUIMIENTO, { status: 201 });
        },
      ),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Open dialog
    await user.click(screen.getByRole("button", { name: /Agregar seguimiento/i }));
    await screen.findByRole("dialog");

    // Check "Disminución de fármacos" and type text in plan_disminucion
    await user.click(
      screen.getByRole("checkbox", { name: /Disminución de fármacos/i }),
    );
    await user.type(
      screen.getByLabelText(/Plan de disminución/i),
      "texto que debería ser descartado",
    );

    // Now UNCHECK "Disminución de fármacos"
    await user.click(
      screen.getByRole("checkbox", { name: /Disminución de fármacos/i }),
    );

    // Fill observaciones so the form is otherwise valid
    await user.type(
      screen.getByLabelText(/Observaciones/i),
      "Sin cambios al final",
    );

    // Submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.disminucion_farmacos).toBe(false);
    expect(sentBody.plan_disminucion).toBeNull();
  });
});

// ── 6. RBAC ──────────────────────────────────────────────────────────────────

describe("RBAC — Auditor no ve acciones de escritura", () => {
  it("Auditor NO ve 'Agregar seguimiento' ni 'Generar alertas de revisión'", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(MOCK_REGISTRO),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json([]),
      ),
    );

    const user = await setupPageWithPaciente(AUDITOR_TOKEN);

    // Wait for seguimiento panel to load
    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin seguimientos registrados/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // "Agregar seguimiento" should not be visible
    expect(
      screen.queryByRole("button", { name: /Agregar seguimiento/i }),
    ).not.toBeInTheDocument();

    // "Generar alertas de revisión" should not be visible
    expect(
      screen.queryByRole("button", { name: /Generar alertas de revisión/i }),
    ).not.toBeInTheDocument();

    // Suppress unused warning
    void user;
  });
});
