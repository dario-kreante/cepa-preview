/**
 * Evaluación clínica del control (ficha del CEPA en SALUTEM): tiempo estimado de
 * tratamiento, proyección de reintegro laboral y factores de riesgo acogidos.
 *
 * Covers:
 *  1. El detalle de la fila muestra la evaluación y las observaciones (también al Auditor).
 *  2. Un writer edita la evaluación → PATCH .../evaluacion con el body correcto.
 *  3. RBAC: el Auditor no ve el botón "Evaluación".
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

const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const MOCK_PACIENTE = {
  id: 7,
  rut: "15.123.456-7",
  nombre: "Humberto Escobar",
  sexo: "M",
  edad: 60,
  region: "Maule",
  comuna: "Talca",
  telefono: null,
  correo: null,
};

const MOCK_VISTA_360 = {
  paciente: MOCK_PACIENTE,
  ingresos: [{ id: 10, paciente_id: 7, fecha_ingreso: "2026-09-01", estado: "activo" }],
};

const MOCK_CONTROL: ControlMedicoRead = {
  id: 400,
  ingreso_id: 10,
  fecha_control: "2026-09-30",
  semana_control: 5,
  medico_tratante: "PILAR GARCÍA",
  region_derivacion: "Maule",
  proximo_control: "2026-10-15",
  proximo_agendado: false,
  tiene_licencia: true,
  resumen_termino_lm: "Licencia tipo 6 por 15 días",
  total_dias_lm: 15,
  tipo_licencia: "6",
  tipo_reposo: "total",
  gaf: null,
  gaf_tramo: "51-60",
  estado_reca: null,
  observaciones: "Paciente con ánimo bajo.",
  tiempo_estimado_tratamiento: "3 meses",
  proyeccion_reintegro: "Más de 1 mes",
  factores_riesgo: "sobrecarga y hostilidad de jefatura",
  origen: "SALUTEM",
  salutem_cita_id: 99,
};

function renderPage(token: string) {
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

async function abrirControles(
  token: string,
  extraHandlers: Parameters<typeof server.use>[0][] = [],
) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/buscar`, () => HttpResponse.json([MOCK_PACIENTE])),
    http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () => HttpResponse.json(MOCK_VISTA_360)),
    ...extraHandlers,
  );
  renderPage(token);
  const user = userEvent.setup();
  await user.type(screen.getByPlaceholderText("Buscar por RUT, folio, nombre o ID SALUTEM"), "Humberto");
  await user.click(await screen.findByText("Humberto Escobar", {}, { timeout: 8000 }));
  await screen.findByText("PILAR GARCÍA", {}, { timeout: 8000 });
  return user;
}

describe("Evaluación clínica del control", () => {
  it("el detalle de la fila muestra la evaluación y las observaciones, también al Auditor", async () => {
    const user = await abrirControles(AUDITOR_TOKEN, [
      http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`, () =>
        HttpResponse.json([MOCK_CONTROL]),
      ),
    ]);

    expect(screen.queryByText("sobrecarga y hostilidad de jefatura")).not.toBeInTheDocument();

    await user.click(screen.getByTestId(`btn-detalle-control-${MOCK_CONTROL.id}`));

    const detalle = screen.getByTestId(`detalle-control-${MOCK_CONTROL.id}`);
    expect(within(detalle).getByText("Tiempo estimado de tratamiento")).toBeInTheDocument();
    expect(within(detalle).getByText("3 meses")).toBeInTheDocument();
    expect(within(detalle).getByText("Proyección de reintegro laboral")).toBeInTheDocument();
    expect(within(detalle).getByText("Más de 1 mes")).toBeInTheDocument();
    expect(within(detalle).getByText("Factores de riesgo acogidos")).toBeInTheDocument();
    expect(within(detalle).getByText("sobrecarga y hostilidad de jefatura")).toBeInTheDocument();
    expect(within(detalle).getByText("Paciente con ánimo bajo.")).toBeInTheDocument();

    // RBAC: sin botón de edición para el Auditor.
    expect(screen.queryByTestId(`btn-evaluacion-${MOCK_CONTROL.id}`)).not.toBeInTheDocument();
  });

  it("un campo sin dato se muestra como guion", async () => {
    const user = await abrirControles(AUDITOR_TOKEN, [
      http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`, () =>
        HttpResponse.json([{ ...MOCK_CONTROL, factores_riesgo: null }]),
      ),
    ]);

    await user.click(screen.getByTestId(`btn-detalle-control-${MOCK_CONTROL.id}`));

    const fila = within(screen.getByTestId(`detalle-control-${MOCK_CONTROL.id}`))
      .getByText("Factores de riesgo acogidos")
      .closest("div") as HTMLElement;
    expect(within(fila).getByText("—")).toBeInTheDocument();
  });

  it("un writer edita la evaluación y se envía el PATCH con los tres campos", async () => {
    const patchSpy = vi.fn();
    const state = { control: { ...MOCK_CONTROL, factores_riesgo: null } as ControlMedicoRead };

    const user = await abrirControles(WRITER_TOKEN, [
      http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingresoId`, () =>
        HttpResponse.json([state.control]),
      ),
      http.patch(`${BASE}/api/v1/controles-medicos/:controlId/evaluacion`, async ({ request }) => {
        const body = (await request.json()) as Record<string, string | null>;
        patchSpy(body);
        state.control = { ...state.control, ...body };
        return HttpResponse.json(state.control);
      }),
    ]);

    await user.click(screen.getByTestId(`btn-evaluacion-${MOCK_CONTROL.id}`));
    const dialog = await screen.findByRole("dialog");

    // Precargado con lo que trajo SALUTEM.
    expect(within(dialog).getByLabelText(/Tiempo estimado de tratamiento/i)).toHaveValue("3 meses");

    await user.type(within(dialog).getByLabelText(/Factores de riesgo acogidos/i), "Sobrecarga laboral");
    await user.click(within(dialog).getByRole("button", { name: /Guardar/i }));

    await waitFor(() => expect(patchSpy).toHaveBeenCalledOnce());
    expect(patchSpy.mock.calls[0][0]).toEqual({
      tiempo_estimado_tratamiento: "3 meses",
      proyeccion_reintegro: "Más de 1 mes",
      factores_riesgo: "Sobrecarga laboral",
    });
  });
});
