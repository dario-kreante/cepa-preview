import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { PatientSheet } from "./PatientSheet";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Coordinacion role token (not server-verified, only decoded)
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const MOCK_PACIENTE = {
  id: 7,
  rut: "11.222.333-4",
  nombre: "Carmen Soto",
  sexo: "F",
  edad: 42,
  region: "Valparaíso",
  comuna: "Viña del Mar",
  telefono: "+56912345678",
  correo: "csoto@example.com",
};

const MOCK_INGRESO = {
  id: 55,
  paciente_id: 7,
  folio: "F-2026-0055",
  folio_manual: false,
  numero_siniestro: null,
  fecha_ingreso: "2026-01-15",
  fecha_diep_diat: null,
  tipo_derivacion: "DIEP",
  tipo_ingreso: "convenio",
  modelo_tratamiento: "ambulatorio",
  diagnostico: "Trastorno de ansiedad generalizada",
  razon_social: null,
  estado: "activo",
  tipo_alta: null,
  fecha_alta: null,
  flag_revision: false,
  observaciones: null,
  tratamiento_iniciado: true,
};

const MOCK_LICENCIA = {
  id: 11,
  ingreso_id: 55,
  folio_lm: "LM-2026-0011",
  tipo_lm: "1",
  tipo_reposo: "total",
  fecha_inicio: "2026-02-01",
  fecha_termino: "2026-02-14",
  fecha_emision: "2026-02-01",
  inicio_reposo: "2026-02-01",
  fin_reposo: "2026-02-14",
  cantidad_dias: 14,
  indicacion_reposo: null,
  diagnostico: "Trastorno de ansiedad",
  origen: "sistema",
  envio_isl: "pendiente",
  fecha_envio_isl: null,
  eeag_gaf: null,
  observaciones: null,
  anulada: false,
};

function setupMocks() {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente: MOCK_PACIENTE,
        ingresos: [MOCK_INGRESO],
        farmacos: [],
        licencias: [],
        controles: [],
        reintegro: [],
      })
    ),
    http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () =>
      HttpResponse.json([MOCK_LICENCIA])
    ),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`, () =>
      HttpResponse.json([])
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`, () =>
      HttpResponse.json([])
    ),
  );
}

function renderSheet(pacienteId: number | null, open = true) {
  tokenStore.setAccess(FAKE_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <PatientSheet
            pacienteId={pacienteId}
            open={open}
            onOpenChange={() => {}}
          />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("PatientSheet", () => {
  it("muestra el nombre del paciente en el header cuando carga", async () => {
    setupMocks();
    renderSheet(7);
    await waitFor(() => {
      expect(screen.getByText("Carmen Soto")).toBeInTheDocument();
    });
  });

  it("muestra el RUT del paciente", async () => {
    setupMocks();
    renderSheet(7);
    await waitFor(() => {
      expect(screen.getByText(/11\.222\.333-4/)).toBeInTheDocument();
    });
  });

  it("muestra las 5 pestañas", async () => {
    setupMocks();
    renderSheet(7);
    await waitFor(() => {
      expect(screen.getByText("Carmen Soto")).toBeInTheDocument();
    });
    expect(screen.getByRole("tab", { name: /Resumen/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Licencias/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Fármacos/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Controles/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Observaciones/i })).toBeInTheDocument();
  });

  it("muestra la licencia en la pestaña Licencias", async () => {
    setupMocks();
    renderSheet(7);
    await waitFor(() => {
      expect(screen.getByText("Carmen Soto")).toBeInTheDocument();
    });
    // Click on Licencias tab
    const licTab = screen.getByRole("tab", { name: /Licencias/i });
    await userEvent.click(licTab);
    await waitFor(() => {
      expect(screen.getByText(/Folio LM-2026-0011/)).toBeInTheDocument();
    });
    expect(screen.getByText(/14 días/)).toBeInTheDocument();
  });

  it("muestra el diagnóstico del ingreso primario en Resumen", async () => {
    setupMocks();
    renderSheet(7);
    await waitFor(() => {
      expect(
        screen.getByText("Trastorno de ansiedad generalizada")
      ).toBeInTheDocument();
    });
  });

  it("no renderiza nada cuando está cerrado (open=false)", () => {
    // No mocks needed since pacienteId=null and open=false
    renderSheet(null, false);
    expect(screen.queryByText("Carmen Soto")).not.toBeInTheDocument();
  });
});
