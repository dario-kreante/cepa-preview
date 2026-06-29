/**
 * Tests for CrearRegistroDialog and NuevaRecetaDialog
 *
 * Covers:
 *  1. Receta date coherence: fecha_revision < fecha_emision blocked (no POST).
 *  2. Receta date coherence: fecha_envio < fecha_emision blocked (no POST).
 *  3. Valid receta submit → POST fires → refetched list shows new receta.
 *  4. Crear registro: CTA shown for writer when registro is null.
 *  5. Crear registro: valid submit fires POST → registro panel reflects created registro.
 *  6. RBAC: Auditor sees neither "Nueva receta" nor "Crear registro".
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
import type { RegistroFarmacologicoRead, RecetaRead } from "./api";

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

const MOCK_RECETA: RecetaRead = {
  id: 100,
  registro_id: 1,
  marca_medicamento: "Losartán 50mg",
  fecha_emision: "2026-06-01",
  fecha_revision: "2026-07-01",
  fecha_envio: null,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
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

/** Wire MSW, render page, search for Juan Pérez and select him. */
async function setupPageWithPaciente(token = WRITER_TOKEN) {
  renderPage(token);
  const user = userEvent.setup();

  const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
  await user.type(input, "Juan");

  await waitFor(
    () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
    { timeout: 3000 },
  );

  await user.click(screen.getByText("Juan Pérez"));
  return user;
}

// ── 1. Receta date coherence: fecha_revision < fecha_emision blocked ──────────

describe("NuevaRecetaDialog — coherencia de fechas", () => {
  it("bloquea submit cuando fecha_revision < fecha_emision y NO llama POST", async () => {
    const postSpy = vi.fn();

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
      http.post(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () => {
        postSpy();
        return HttpResponse.json(MOCK_RECETA, { status: 201 });
      }),
    );

    const user = await setupPageWithPaciente();

    // Wait for the registro panel to appear and button to be enabled
    await waitFor(
      () =>
        expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // The "Nueva receta" header button should now be enabled (registro exists)
    const btnNuevaReceta = await screen.findByRole("button", {
      name: /Nueva receta/i,
    });
    await waitFor(() => expect(btnNuevaReceta).not.toBeDisabled(), {
      timeout: 3000,
    });
    await user.click(btnNuevaReceta);

    // Dialog opens
    await screen.findByRole("dialog");

    await user.type(
      screen.getByLabelText(/Marca del medicamento/i),
      "Enalapril",
    );

    // fecha_emision = 2026-06-10; fecha_revision = 2026-06-01 (BEFORE emision)
    await user.type(screen.getByLabelText(/Fecha de emisión/i), "2026-06-10");
    await user.type(screen.getByLabelText(/Fecha de revisión/i), "2026-06-01");

    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    // Validation error shown
    await waitFor(() => {
      expect(
        screen.getByText(
          /La fecha de revisión debe ser igual o posterior a la fecha de emisión/i,
        ),
      ).toBeInTheDocument();
    });

    // POST must NOT have been called
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("bloquea submit cuando fecha_envio < fecha_emision y NO llama POST", async () => {
    const postSpy = vi.fn();

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
      http.post(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () => {
        postSpy();
        return HttpResponse.json(MOCK_RECETA, { status: 201 });
      }),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () =>
        expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    const btnNuevaReceta = await screen.findByRole("button", {
      name: /Nueva receta/i,
    });
    await waitFor(() => expect(btnNuevaReceta).not.toBeDisabled(), {
      timeout: 3000,
    });
    await user.click(btnNuevaReceta);

    await screen.findByRole("dialog");

    await user.type(
      screen.getByLabelText(/Marca del medicamento/i),
      "Enalapril",
    );
    // fecha_emision = 2026-06-10; fecha_revision valid; fecha_envio before emision
    await user.type(screen.getByLabelText(/Fecha de emisión/i), "2026-06-10");
    await user.type(screen.getByLabelText(/Fecha de revisión/i), "2026-06-20");
    // fecha_envio field (label contains "Fecha de envío")
    const envioInput = screen.getByLabelText(/Fecha de envío/i);
    await user.type(envioInput, "2026-06-01");

    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText(
          /La fecha de envío debe ser igual o posterior a la fecha de emisión/i,
        ),
      ).toBeInTheDocument();
    });

    expect(postSpy).not.toHaveBeenCalled();
  });

  it("submit válido → POST dispara y la lista muestra la nueva receta", async () => {
    const postSpy = vi.fn();
    const state = { recetas: [] as RecetaRead[] };

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
        HttpResponse.json(state.recetas),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json([]),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico/:id/recetas`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.recetas = [MOCK_RECETA];
          return HttpResponse.json(MOCK_RECETA, { status: 201 });
        },
      ),
    );

    const user = await setupPageWithPaciente();

    await waitFor(
      () =>
        expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 },
    );

    const btnNuevaReceta = await screen.findByRole("button", {
      name: /Nueva receta/i,
    });
    await waitFor(() => expect(btnNuevaReceta).not.toBeDisabled(), {
      timeout: 3000,
    });
    await user.click(btnNuevaReceta);

    await screen.findByRole("dialog");

    await user.type(
      screen.getByLabelText(/Marca del medicamento/i),
      "Losartán 50mg",
    );
    await user.type(screen.getByLabelText(/Fecha de emisión/i), "2026-06-01");
    await user.type(screen.getByLabelText(/Fecha de revisión/i), "2026-07-01");

    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.marca_medicamento).toBe("Losartán 50mg");
    expect(sentBody.fecha_emision).toBe("2026-06-01");
    expect(sentBody.fecha_revision).toBe("2026-07-01");

    // After mutation + cache invalidation, refetch shows the new receta
    // (The name also appears in the filter <option>, so getAllByText is used)
    await waitFor(
      () => {
        const els = screen.getAllByText("Losartán 50mg");
        expect(els.length).toBeGreaterThanOrEqual(1);
      },
      { timeout: 3000 },
    );
  });
});

// ── 4-5. CrearRegistroDialog ─────────────────────────────────────────────────

describe("CrearRegistroDialog", () => {
  it("muestra CTA 'Crear registro' para writer cuando no hay registro", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      // 404 → api layer returns null
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(null, { status: 404 }),
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

    await setupPageWithPaciente(WRITER_TOKEN);

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin registro farmacológico/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    expect(
      screen.getByRole("button", { name: /Crear registro farmacológico/i }),
    ).toBeInTheDocument();
  });

  it("submit válido de Crear registro → POST dispara y el panel muestra el registro creado", async () => {
    const postSpy = vi.fn();
    const state = { registro: null as RegistroFarmacologicoRead | null };

    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () => {
        if (state.registro) return HttpResponse.json(state.registro);
        return HttpResponse.json(null, { status: 404 });
      }),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/seguimiento`, () =>
        HttpResponse.json([]),
      ),
      http.post(
        `${BASE}/api/v1/registro-farmacologico`,
        async ({ request }) => {
          const body = await request.json();
          postSpy(body);
          state.registro = { ...MOCK_REGISTRO, medico_tratante: (body as Record<string, string>).medico_tratante };
          return HttpResponse.json(state.registro, { status: 201 });
        },
      ),
    );

    const user = await setupPageWithPaciente(WRITER_TOKEN);

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin registro farmacológico/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Open dialog
    await user.click(
      screen.getByRole("button", { name: /Crear registro farmacológico/i }),
    );

    await screen.findByRole("dialog");

    // Fill in required fields
    await user.type(
      screen.getByLabelText(/Médico tratante/i),
      "Dr. Juan Martínez",
    );

    // Estado is pre-selected as "activo" by default; submit
    const dialog = screen.getByRole("dialog");
    const submitBtn = dialog.querySelector(
      'button[type="submit"]',
    ) as HTMLElement;
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
    });

    const sentBody = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sentBody.medico_tratante).toBe("Dr. Juan Martínez");
    expect(sentBody.estado_farmacologico).toBe("activo");
    expect(sentBody.ingreso_id).toBe(10);

    // After mutation + cache invalidation, registro panel shows médico tratante
    await waitFor(
      () =>
        expect(screen.getByText("Dr. Juan Martínez")).toBeInTheDocument(),
      { timeout: 3000 },
    );
  });
});

// ── 6. RBAC ──────────────────────────────────────────────────────────────────

describe("RBAC — Auditor", () => {
  it("Auditor NO ve 'Nueva receta' ni 'Crear registro'", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE]),
      ),
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id`, () =>
        HttpResponse.json(null, { status: 404 }),
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

    await setupPageWithPaciente(AUDITOR_TOKEN);

    // Wait for no-registro panel
    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin registro farmacológico/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // Neither button should be present
    expect(
      screen.queryByRole("button", { name: /Nueva receta/i }),
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole("button", { name: /Crear registro/i }),
    ).not.toBeInTheDocument();
  });
});
