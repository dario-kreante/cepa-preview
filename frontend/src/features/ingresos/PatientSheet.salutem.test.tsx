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

// Rol Coordinacion (el token solo se decodifica, no se verifica)
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const FOLIO = "F-2026-0055";

function fichaSalutem(id: number, citaId: number, fecha: string, especialidad: string) {
  return {
    id,
    folio: FOLIO,
    origen: "SALUTEM",
    created_at: "2026-09-15T12:00:00Z",
    contenido: {
      citaId,
      citaFecha: fecha,
      especialidadNombre: especialidad,
      profesionalNombre: "Dra. Paula Rojas",
    },
  };
}

function setupMocks(fichasIniciales: unknown[] = []) {
  let fichas = [...fichasIniciales];
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente: {
          id: 7, rut: "16.215.806-6", nombre: "Paciente Prueba", sexo: "F", edad: 42,
          region: "Maule", comuna: "Talca", telefono: null, correo: null,
        },
        ingresos: [{
          id: 55, paciente_id: 7, folio: FOLIO, folio_manual: false, numero_siniestro: null,
          fecha_ingreso: "2025-01-01", fecha_diep_diat: null, tipo_derivacion: "DIEP",
          tipo_ingreso: "convenio", modelo_tratamiento: "ambulatorio", diagnostico: "Ansiedad",
          razon_social: null, estado: "activo", tipo_alta: null, fecha_alta: null,
          flag_revision: false, observaciones: null, tratamiento_iniciado: true,
        }],
        farmacos: [], licencias: [], controles: [], reintegro: [],
      }),
    ),
    http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio`, () => HttpResponse.json(fichas)),
  );
  return {
    alImportar(nuevas: unknown[]) {
      server.use(
        http.post(`${BASE}/api/v1/fichas-clinicas/pull-salutem`, () => {
          fichas = [...fichas, ...nuevas];
          return HttpResponse.json(nuevas);
        }),
      );
    },
  };
}

function renderSheet() {
  tokenStore.setAccess(FAKE_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <PatientSheet pacienteId={7} open onOpenChange={() => {}} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function abrirPestanaSalutem() {
  await screen.findByText("Paciente Prueba");
  await userEvent.click(await screen.findByRole("tab", { name: /SALUTEM/i }));
}

describe("PatientSheet — pestaña SALUTEM", () => {
  it("lista las atenciones ya importadas con su fecha y especialidad", async () => {
    setupMocks([fichaSalutem(1, 900, "2025-01-22", "Psiquiatría")]);
    renderSheet();
    await abrirPestanaSalutem();
    expect(await screen.findByText(/Psiquiatría/)).toBeInTheDocument();
    expect(screen.getByText(/22\/01\/2025/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /SALUTEM \(1\)/i })).toBeInTheDocument();
  });

  it("importa desde SALUTEM, informa cuántas atenciones trajo y las muestra", async () => {
    const mocks = setupMocks();
    mocks.alImportar([
      fichaSalutem(2, 901, "2025-01-23", "Psicología"),
      fichaSalutem(3, 902, "2025-02-12", "Medicina general"),
    ]);
    renderSheet();
    await abrirPestanaSalutem();
    await userEvent.click(screen.getByRole("button", { name: /importar desde salutem/i }));
    expect(await screen.findByRole("status")).toHaveTextContent(/2 atenciones/i);
    expect(await screen.findByText(/Medicina general/)).toBeInTheDocument();
  });

  it("si SALUTEM no tiene nada nuevo lo dice en vez de quedarse en silencio", async () => {
    const mocks = setupMocks();
    mocks.alImportar([]);
    renderSheet();
    await abrirPestanaSalutem();
    await userEvent.click(screen.getByRole("button", { name: /importar desde salutem/i }));
    expect(await screen.findByRole("status")).toHaveTextContent(/no tiene atenciones nuevas/i);
  });

  it("muestra el motivo cuando SALUTEM rechaza el RUT del paciente", async () => {
    setupMocks();
    server.use(
      http.post(`${BASE}/api/v1/fichas-clinicas/pull-salutem`, () =>
        HttpResponse.json(
          { detail: "SALUTEM no reconoce el RUT del paciente como válido. Revisa el RUT registrado en el ingreso." },
          { status: 422 },
        ),
      ),
    );
    renderSheet();
    await abrirPestanaSalutem();
    await userEvent.click(screen.getByRole("button", { name: /importar desde salutem/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/RUT del paciente/i);
    });
  });
});
