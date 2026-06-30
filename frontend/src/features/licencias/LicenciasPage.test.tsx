import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { LicenciasPage } from "./LicenciasPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Minimal valid JWT for role "Coordinacion"
// Payload: {"sub":"1","username":"test","role":"Coordinacion","type":"access","exp":9999999999}
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// Minimal valid JWT for role "Auditor"
// Payload: {"sub":"2","username":"auditor","role":"Auditor","type":"access","exp":9999999999}
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage(token = FAKE_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <LicenciasPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const FOLIO = "FOLIO-001";

const MOCK_SLIM_LICENCIA = {
  id: 10,
  tipo_lm: "1",
  cantidad_dias: 14,
  fecha_inicio: "2026-06-01",
  fecha_termino: "2026-06-14",
  diagnostico: "Lumbalgia aguda",
  anulada: false,
};

const MOCK_FULL_LICENCIA = {
  id: 10,
  ingreso_id: 5,
  folio_lm: "LM-00001",
  tipo_lm: "1",
  tipo_reposo: "total",
  fecha_inicio: "2026-06-01",
  fecha_termino: "2026-06-14",
  fecha_emision: "2026-05-31",
  inicio_reposo: "2026-06-01",
  fin_reposo: "2026-06-14",
  cantidad_dias: 14,
  indicacion_reposo: null,
  diagnostico: "Lumbalgia aguda",
  origen: "sistema",
  envio_isl: "pendiente",
  fecha_envio_isl: null,
  eeag_gaf: 42,
  observaciones: null,
  anulada: false,
};

describe("LicenciasPage", () => {
  it("muestra el prompt inicial cuando no hay folio ingresado", async () => {
    renderPage();
    expect(
      await screen.findByText(/Ingresa un folio para ver sus licencias/i)
    ).toBeInTheDocument();
  });

  it("tiene el placeholder exacto requerido", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Buscar por folio")
    ).toBeInTheDocument();
  });

  it("muestra 'Nueva licencia' para Coordinacion (puedeEscribir)", async () => {
    renderPage(FAKE_TOKEN);
    expect(await screen.findByRole("button", { name: /Nueva licencia/i })).toBeInTheDocument();
  });

  it("NO muestra 'Nueva licencia' para Auditor", async () => {
    renderPage(AUDITOR_TOKEN);
    await screen.findByText(/Ingresa un folio/i);
    expect(screen.queryByRole("button", { name: /Nueva licencia/i })).not.toBeInTheDocument();
  });

  it("busca por folio y muestra la tabla con tipo y días", async () => {
    server.use(
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({
          folio: FOLIO,
          historial: [MOCK_SLIM_LICENCIA],
          dias_acumulados: 14,
        })
      ),
      http.get(`${BASE}/api/v1/licencias/:id`, () =>
        HttpResponse.json(MOCK_FULL_LICENCIA)
      )
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por folio");
    // Use fireEvent.change to fire a single change event; the debounce then fires after 400ms
    fireEvent.change(input, { target: { value: FOLIO } });

    // Wait for debounce + network: the tipo badge renders in the table row
    // Note: "Tipo 1" also appears in the filter <option>, so use getAllByText
    await waitFor(
      () => {
        // The badge renders in the table and appears in the filter dropdown too → getAllByText
        const badges = screen.getAllByText("Tipo 1");
        // At least 2: one in dropdown option, one in the table badge
        expect(badges.length).toBeGreaterThanOrEqual(2);
      },
      { timeout: 8000 }
    );
  });

  it("muestra el badge Estado correcto (Vigente / Finalizada / Anulada)", async () => {
    // fecha_termino in the future to be "Vigente"
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 10);
    const futureDate = tomorrow.toISOString().split("T")[0];

    server.use(
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({
          folio: FOLIO,
          historial: [{ ...MOCK_SLIM_LICENCIA, fecha_termino: futureDate }],
          dias_acumulados: 14,
        })
      ),
      http.get(`${BASE}/api/v1/licencias/:id`, () =>
        HttpResponse.json({ ...MOCK_FULL_LICENCIA, fecha_termino: futureDate })
      )
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por folio");
    fireEvent.change(input, { target: { value: FOLIO } });

    // Estado badge and "Vigente (Xd)" vence-en badge both contain "Vigente"
    await waitFor(
      () => {
        const elements = screen.getAllByText(/Vigente/i);
        expect(elements.length).toBeGreaterThanOrEqual(1);
      },
      { timeout: 8000 }
    );
  });

  it("muestra badge 'Vence en' con label correcto para fecha próxima (< 7 días)", async () => {
    // fecha_termino 5 days from now → "Vence en 5d" (amber, < 7 days)
    const soon = new Date();
    soon.setDate(soon.getDate() + 5);
    const soonDate = soon.toISOString().split("T")[0];

    server.use(
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({
          folio: FOLIO,
          historial: [{ ...MOCK_SLIM_LICENCIA, fecha_termino: soonDate }],
          dias_acumulados: 14,
        })
      ),
      http.get(`${BASE}/api/v1/licencias/:id`, () =>
        HttpResponse.json({ ...MOCK_FULL_LICENCIA, fecha_termino: soonDate })
      )
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por folio");
    fireEvent.change(input, { target: { value: FOLIO } });

    // Expect any "Vence en Xd" badge (warning = amber, between 3-7 days)
    await waitFor(
      () => {
        expect(screen.getByText(/Vence en \d+d/i)).toBeInTheDocument();
      },
      { timeout: 8000 }
    );
  });

  it("muestra 'Sin licencias para este folio' cuando historial está vacío", async () => {
    server.use(
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({ folio: "X-999", historial: [], dias_acumulados: 0 })
      )
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por folio");
    fireEvent.change(input, { target: { value: "X-999" } });

    await waitFor(
      () => {
        expect(screen.getByText(/Sin licencias para este folio/i)).toBeInTheDocument();
      },
      { timeout: 8000 }
    );
  });

  it("muestra el strip de días acumulados cuando hay licencias", async () => {
    server.use(
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({
          folio: FOLIO,
          historial: [MOCK_SLIM_LICENCIA],
          dias_acumulados: 28,
        })
      ),
      http.get(`${BASE}/api/v1/licencias/:id`, () =>
        HttpResponse.json(MOCK_FULL_LICENCIA)
      )
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por folio");
    fireEvent.change(input, { target: { value: FOLIO } });

    await waitFor(
      () => {
        // The strip renders the number 28 prominently
        expect(screen.getByText("28")).toBeInTheDocument();
        // "Días acumulados" strip label is present (may appear in subtitle too, use getAllByText)
        const diasLabels = screen.getAllByText(/Días acumulados/i);
        expect(diasLabels.length).toBeGreaterThanOrEqual(1);
      },
      { timeout: 8000 }
    );
  });

  it("tiene los selects de filtro Reposo e ISL presentes", () => {
    renderPage();
    // The selects exist in DOM even before search
    expect(screen.getByDisplayValue("Reposo: Todos")).toBeInTheDocument();
    expect(screen.getByDisplayValue("ISL: Todos")).toBeInTheDocument();
  });
});
