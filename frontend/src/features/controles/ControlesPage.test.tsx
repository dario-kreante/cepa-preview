import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ControlesPage } from "./ControlesPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Minimal valid JWT for role "Coordinacion"
// Payload: {"sub":"1","username":"test","role":"Coordinacion","type":"access","exp":9999999999}
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// Minimal valid JWT for role "Auditor"
// Payload: {"sub":"2","username":"auditor","role":"Auditor","type":"access","exp":9999999999}
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage(token = WRITER_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <ControlesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ── Test fixtures ────────────────────────────────────────────────────────────

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

const MOCK_CONTROLES = [
  {
    id: 200,
    ingreso_id: 10,
    fecha_control: "2026-03-10",
    semana_control: 8,
    medico_tratante: "Dr. Andrés Molina",
    region_derivacion: "Metropolitana",
    proximo_control: "2026-04-07",
    proximo_agendado: true,
    tiene_licencia: true,
    resumen_termino_lm: null,
    total_dias_lm: 14,
    tipo_licencia: "1",
    tipo_reposo: "total",
    gaf: 65,
    estado_reca: "aprobado",
    observaciones: null,
  },
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("ControlesPage", () => {
  it("muestra el prompt inicial cuando no hay búsqueda", async () => {
    renderPage();
    expect(
      await screen.findByText(/Escribe un RUT, folio o nombre para buscar pacientes/i)
    ).toBeInTheDocument();
  });

  it("tiene el placeholder exacto requerido", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Buscar por RUT, folio o nombre")
    ).toBeInTheDocument();
  });

  it("muestra 'Nuevo control' para Coordinacion (puedeEscribir)", async () => {
    renderPage(WRITER_TOKEN);
    expect(
      await screen.findByRole("button", { name: /Nuevo control/i })
    ).toBeInTheDocument();
  });

  it("NO muestra 'Nuevo control' para Auditor (RBAC)", async () => {
    renderPage(AUDITOR_TOKEN);
    // Wait for the page to render past the initial loading state
    await screen.findByText(/Escribe un RUT, folio o nombre para buscar pacientes/i);
    expect(
      screen.queryByTestId("btn-nuevo-control")
    ).not.toBeInTheDocument();
  });

  it("busca pacientes, selecciona uno y muestra controles con semana, días LM, reposo, GAF y RECA", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("q")) {
          return HttpResponse.json([MOCK_PACIENTE]);
        }
        return HttpResponse.json([]);
      }),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360)
      ),
      http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`, () =>
        HttpResponse.json(MOCK_CONTROLES)
      )
    );

    renderPage();

    // Type in search
    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "Juan");

    // Paciente list appears
    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Select the paciente row
    await userEvent.click(screen.getByText("Juan Pérez"));

    // Semana column
    await waitFor(
      () => expect(screen.getByText("8")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Días LM column
    expect(screen.getByText("14")).toBeInTheDocument();

    // Reposo badge — "total" → "Total" (also appears as a filter <option>, hence getAllByText)
    const totalEls = screen.getAllByText("Total");
    expect(totalEls.length).toBeGreaterThanOrEqual(1);

    // GAF numeric value
    expect(screen.getByText("65")).toBeInTheDocument();

    // RECA badge — "aprobado" → "Aprobado" (also appears as a filter <option>)
    const aprobadoEls = screen.getAllByText("Aprobado");
    expect(aprobadoEls.length).toBeGreaterThanOrEqual(1);

    // Agendado badge (proximo_agendado: true)
    expect(screen.getByText("Agendado")).toBeInTheDocument();

    // Médico tratante
    expect(screen.getByText("Dr. Andrés Molina")).toBeInTheDocument();
  });

  it("muestra empty state cuando el paciente no tiene ingresos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE])
      ),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json({ paciente: MOCK_PACIENTE, ingresos: [] })
      )
    );

    renderPage();

    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "Juan");

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

  it("muestra empty state cuando el ingreso no tiene controles", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE])
      ),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360)
      ),
      http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`, () =>
        HttpResponse.json([])
      )
    );

    renderPage();

    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    await userEvent.click(screen.getByText("Juan Pérez"));

    await waitFor(
      () =>
        expect(
          screen.getByText(/No hay controles médicos registrados para este ingreso/i)
        ).toBeInTheDocument(),
      { timeout: 8000 }
    );
  });
});
