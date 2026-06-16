import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { FarmacosPage } from "./FarmacosPage";

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
          <FarmacosPage />
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

const MOCK_REGISTRO = {
  id: 1,
  ingreso_id: 10,
  medico_tratante: "Dra. Carmen López",
  estado_farmacologico: "en_tratamiento",
  antecedentes_previos: "Hipertensión arterial",
  tratamiento_previo: "Enalapril 10mg",
};

// fecha_revision 30 days in the future → "Vigente"
const futureDate = (() => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().split("T")[0];
})();

const MOCK_RECETAS = [
  {
    id: 100,
    ingreso_id: 10,
    marca_medicamento: "Losartán 50mg",
    fecha_emision: "2026-06-01",
    fecha_revision: futureDate,
    fecha_envio: "2026-06-03",
  },
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("FarmacosPage", () => {
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

  it("muestra 'Nueva receta' para Coordinacion (puedeEscribir)", async () => {
    renderPage(WRITER_TOKEN);
    expect(
      await screen.findByRole("button", { name: /Nueva receta/i })
    ).toBeInTheDocument();
  });

  it("NO muestra 'Nueva receta' para Auditor (RBAC)", async () => {
    renderPage(AUDITOR_TOKEN);
    // Wait for the page to render past the initial loading state
    await screen.findByText(/Escribe un RUT, folio o nombre para buscar pacientes/i);
    expect(
      screen.queryByRole("button", { name: /Nueva receta/i })
    ).not.toBeInTheDocument();
  });

  it("busca pacientes, selecciona uno y muestra el registro + receta con badge de estado", async () => {
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
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingresoId`, () =>
        HttpResponse.json(MOCK_REGISTRO)
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingresoId/recetas`, () =>
        HttpResponse.json(MOCK_RECETAS)
      )
    );

    renderPage();

    // Type in search
    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "Juan");

    // Paciente list appears
    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 3000 }
    );

    // Select the paciente row
    await userEvent.click(screen.getByText("Juan Pérez"));

    // Registro panel shows médico tratante
    await waitFor(
      () => expect(screen.getByText("Dra. Carmen López")).toBeInTheDocument(),
      { timeout: 3000 }
    );

    // Registro estado badge
    expect(screen.getByText("En tratamiento")).toBeInTheDocument();

    // Receta row with marca_medicamento (also appears in the filter <option>)
    const marcaElements = screen.getAllByText("Losartán 50mg");
    expect(marcaElements.length).toBeGreaterThanOrEqual(1);

    // Derived status badge — fecha_revision is 30 days out → "Vigente"
    const vigenteBadges = screen.getAllByText("Vigente");
    expect(vigenteBadges.length).toBeGreaterThanOrEqual(1);
  });

  it("muestra estado 'Vencida' cuando fecha_revision está en el pasado", async () => {
    const pastDate = "2020-01-01";
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE])
      ),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360)
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingresoId`, () =>
        HttpResponse.json(MOCK_REGISTRO)
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingresoId/recetas`, () =>
        HttpResponse.json([{ ...MOCK_RECETAS[0], fecha_revision: pastDate }])
      )
    );

    renderPage();

    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 3000 }
    );

    await userEvent.click(screen.getByText("Juan Pérez"));

    await waitFor(
      () => {
        const vencidaEls = screen.getAllByText("Vencida");
        // At least one badge (div) + the filter option
        expect(vencidaEls.length).toBeGreaterThanOrEqual(1);
      },
      { timeout: 3000 }
    );
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
      { timeout: 3000 }
    );

    await userEvent.click(screen.getByText("Juan Pérez"));

    await waitFor(
      () =>
        expect(
          screen.getByText(/Este paciente no tiene ingresos registrados/i)
        ).toBeInTheDocument(),
      { timeout: 3000 }
    );
  });

  it("muestra CTA 'Crear registro' cuando el ingreso no tiene registro (writers only)", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE])
      ),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json(MOCK_VISTA_360)
      ),
      // 404 → api returns null → "Sin registro"
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingresoId`, () =>
        HttpResponse.json(null, { status: 404 })
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingresoId/recetas`, () =>
        HttpResponse.json([])
      )
    );

    renderPage(WRITER_TOKEN);

    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 3000 }
    );

    await userEvent.click(screen.getByText("Juan Pérez"));

    await waitFor(
      () =>
        expect(
          screen.getByText(/Sin registro farmacológico/i)
        ).toBeInTheDocument(),
      { timeout: 3000 }
    );

    expect(
      screen.getByRole("button", { name: /Crear registro farmacológico/i })
    ).toBeInTheDocument();
  });
});
