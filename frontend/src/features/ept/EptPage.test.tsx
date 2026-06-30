import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { EptPage } from "./EptPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// ── Auth tokens ──────────────────────────────────────────────────────────────

// Payload: {"sub":"1","username":"admin","role":"Administrativo","type":"access","exp":9999999999}
const ADMIN_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJBZG1pbmlzdHJhdGl2byIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// Payload: {"sub":"2","username":"coord","role":"Coordinacion","type":"access","exp":9999999999}
const COORD_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJjb29yZCIsInJvbGUiOiJDb29yZGluYWNpb24iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// ── Render helper ────────────────────────────────────────────────────────────

function renderPage(token = ADMIN_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <EptPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

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

const MOCK_CASO: import("./api").CasoEptRead = {
  id: 55,
  ingreso_id: 10,
  mes: "Enero 2026",
  fecha_ingreso_ept: "2026-01-20",
  nombre_trabajador: "María González",
  rut_trabajador: "12.345.678-9",
  region_trabajador: "Metropolitana",
  eista: "EISTA-001",
  factor_riesgo: "carga",
  corresponde_ept: true,
  estado: "abierto",
  razon_social: "Empresa S.A.",
  unidad_cargo_horario: "Bodega · Operario",
  created_at: "2026-01-20T10:00:00Z",
  updated_at: "2026-01-20T10:00:00Z",
};

// ── Helper: set up paciente search + vista360 + POST mocks ───────────────────

function setupPacienteHandlers(captureBody?: (b: unknown) => void) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/buscar`, ({ request }) => {
      const url = new URL(request.url);
      if (url.searchParams.get("q")) return HttpResponse.json([MOCK_PACIENTE]);
      return HttpResponse.json([]);
    }),
    http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
      HttpResponse.json(MOCK_VISTA_360)
    ),
    http.post(`${BASE}/api/v1/casos-ept`, async ({ request }) => {
      const body = await request.json();
      captureBody?.(body);
      return HttpResponse.json(MOCK_CASO, { status: 201 });
    }),
    // Also handle useCaso after creation
    http.get(`${BASE}/api/v1/casos-ept/:casoId`, () =>
      HttpResponse.json(MOCK_CASO)
    )
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("EptPage", () => {
  // ── Basic render ───────────────────────────────────────────────────────────

  it("muestra el título y subtítulo correctos", async () => {
    renderPage();
    expect(
      await screen.findByText("Seguimiento EPT")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Evaluaciones de Puesto de Trabajo/i)
    ).toBeInTheDocument();
  });

  it("tiene el placeholder exacto requerido", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Buscar por RUT, folio o nombre")
    ).toBeInTheDocument();
  });

  it("muestra input de carga por caso_id", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Cargar caso N°")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Cargar/i })
    ).toBeInTheDocument();
  });

  // ── RBAC: "Nueva EPT" button ───────────────────────────────────────────────

  it("muestra 'Nueva EPT' para Administrativo (puedeEscribirEpt)", async () => {
    renderPage(ADMIN_TOKEN);
    expect(
      await screen.findByTestId("btn-nueva-ept")
    ).toBeInTheDocument();
  });

  it("NO muestra 'Nueva EPT' para Coordinacion (RBAC EPT más estricto)", async () => {
    renderPage(COORD_TOKEN);
    await screen.findByText("Seguimiento EPT");
    expect(screen.queryByTestId("btn-nueva-ept")).not.toBeInTheDocument();
  });

  // ── (a) Alta paciente-driven ───────────────────────────────────────────────

  it("(a) busca paciente, selecciona, abre dialog, envía POST con ingreso_id:10, renderiza detalle del caso", async () => {
    let capturedBody: unknown;
    setupPacienteHandlers((b) => {
      capturedBody = b;
    });

    renderPage(ADMIN_TOKEN);

    // Search for paciente
    const searchInput = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(searchInput, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Select paciente
    await userEvent.click(screen.getByText("Juan Pérez"));

    // Wait for ingreso to resolve and Nueva EPT button to become enabled
    await waitFor(
      () => {
        const btn = screen.getByTestId("btn-nueva-ept");
        expect(btn).not.toBeDisabled();
      },
      { timeout: 8000 }
    );

    // Click Nueva EPT
    await userEvent.click(screen.getByTestId("btn-nueva-ept"));

    // Dialog should be open
    await waitFor(
      () => expect(screen.getByRole("dialog")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Fill required fields
    await userEvent.type(screen.getByLabelText(/Mes/i), "Enero 2026");
    await userEvent.type(
      screen.getByLabelText(/Fecha de ingreso EPT/i),
      "2026-01-20"
    );
    await userEvent.type(
      screen.getByLabelText(/Nombre del trabajador/i),
      "María González"
    );
    await userEvent.type(
      screen.getByLabelText(/RUT del trabajador/i),
      "12.345.678-9"
    );
    await userEvent.type(
      screen.getByLabelText(/Región del trabajador/i),
      "Metropolitana"
    );
    await userEvent.type(screen.getByLabelText(/EISTA/i), "EISTA-001");

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /Crear caso EPT/i }));

    // POST body must contain ingreso_id: 10
    await waitFor(
      () => {
        expect(capturedBody).toBeDefined();
        expect((capturedBody as Record<string, unknown>).ingreso_id).toBe(10);
      },
      { timeout: 8000 }
    );

    // Caso detail renders — nombre_trabajador
    await waitFor(
      () => expect(screen.getByText("María González")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Estado badge "Abierto"
    expect(screen.getByText("Abierto")).toBeInTheDocument();
  });

  // ── (b) Cargar por caso_id ─────────────────────────────────────────────────

  it("(b) carga caso por id → GET /api/v1/casos-ept/{id} → renderiza detalle", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, ({ params }) => {
        if (String(params.casoId) === "55") {
          return HttpResponse.json(MOCK_CASO);
        }
        return new HttpResponse(null, { status: 404 });
      })
    );

    renderPage(ADMIN_TOKEN);

    const casoInput = screen.getByTestId("input-caso-id");
    await userEvent.type(casoInput, "55");

    await userEvent.click(screen.getByTestId("btn-cargar-caso"));

    // Detail renders
    await waitFor(
      () => expect(screen.getByText("María González")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    expect(screen.getByText("Abierto")).toBeInTheDocument();
    expect(screen.getByText("EISTA-001")).toBeInTheDocument();
  });

  // ── Empty / error states ───────────────────────────────────────────────────

  it("muestra empty state cuando el paciente no tiene ingresos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE])
      ),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json({ paciente: MOCK_PACIENTE, ingresos: [] })
      )
    );

    renderPage(ADMIN_TOKEN);

    const searchInput = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(searchInput, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    await userEvent.click(screen.getByText("Juan Pérez"));

    await waitFor(
      () =>
        expect(
          screen.getByText(/Este paciente no tiene ingresos registrados/i)
        ).toBeInTheDocument(),
      { timeout: 8000 }
    );
  });
});
