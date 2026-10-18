import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ProfesionalesPage } from "./ProfesionalesPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// JWT con rol Coordinacion
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const PROF = {
  id: 7,
  nombre: "Dra. Ana Rojas",
  especialidad: "Psiquiatría",
  origen: "SALUTEM",
  activo: true,
  created_at: "2026-10-16T00:00:00Z",
  salutem_profesional_id: 99,
  especialidades: ["Psiquiatría", "Psicología"],
  sucursales: ["Talca"],
  primera_atencion: "2026-01-05",
  ultima_atencion: "2026-09-30",
  sincronizado_en: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
};

const ACTIVIDAD = {
  profesional_id: 7,
  total_atenciones: 42,
  atenciones_por_especialidad: [{ especialidad: "Psiquiatría", total: 40 }],
  total_controles: 12,
  pacientes_distintos: 15,
  primera_atencion: "2026-01-05",
  ultima_atencion: "2026-09-30",
  ultimas_atenciones: [
    {
      ficha_id: 501,
      fecha: "2026-09-30",
      especialidad: "Psiquiatría",
      folio: "F-123",
      ingreso_id: 10,
      paciente_id: 33,
      paciente: "María González",
    },
  ],
};

function renderPage() {
  tokenStore.setAccess(WRITER_TOKEN);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <ProfesionalesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProfesionalesPage", () => {
  it("muestra origen, especialidades, última atención y sincronización relativa", async () => {
    server.use(http.get(`${BASE}/api/v1/profesionales`, () => HttpResponse.json([PROF])));
    renderPage();
    const fila = await screen.findByTestId("row-prof-7");
    expect(within(fila).getByText("SALUTEM")).toBeInTheDocument();
    expect(within(fila).getByText("Psiquiatría, Psicología")).toBeInTheDocument();
    expect(within(fila).getByText("30/09/2026")).toBeInTheDocument();
    expect(within(fila).getByText("hace 3 horas")).toBeInTheDocument();
  });

  it("al hacer clic en la fila abre el detalle con la actividad y link al ingreso", async () => {
    server.use(
      http.get(`${BASE}/api/v1/profesionales`, () => HttpResponse.json([PROF])),
      http.get(`${BASE}/api/v1/profesionales/7/actividad`, () =>
        HttpResponse.json(ACTIVIDAD),
      ),
    );
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("row-prof-7"));

    const detalle = await screen.findByTestId("detalle-actividad");
    expect(within(detalle).getByText("42")).toBeInTheDocument();
    expect(within(detalle).getByText("Psiquiatría · 40")).toBeInTheDocument();
    const link = within(detalle).getByTestId("link-atencion-501");
    expect(link).toHaveAttribute("href", "/ingresos?paciente=33");
    expect(within(detalle).getByText(/folio F-123/)).toBeInTheDocument();
  });

  it("importar muestra creados/actualizados/adoptados/vinculados y los errores", async () => {
    server.use(
      http.get(`${BASE}/api/v1/profesionales`, () => HttpResponse.json([PROF])),
      http.post(`${BASE}/api/v1/profesionales/importar-salutem`, () =>
        HttpResponse.json({
          creados: 2,
          actualizados: 3,
          adoptados: 1,
          vinculados: 4,
          errores: ["Profesional 55: nombre vacío"],
        }),
      ),
    );
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("btn-importar-salutem"));

    const res = await screen.findByTestId("resultado-importacion");
    expect(res).toHaveTextContent("2 creados");
    expect(res).toHaveTextContent("3 actualizados");
    expect(res).toHaveTextContent("1 adoptados");
    expect(res).toHaveTextContent("4 vinculados");
    await waitFor(() =>
      expect(within(res).getByText("Profesional 55: nombre vacío")).toBeInTheDocument(),
    );
  });
});
