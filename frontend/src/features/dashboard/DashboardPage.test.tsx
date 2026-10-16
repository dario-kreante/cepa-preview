/**
 * Dashboard operativo: lee /dashboard/operativo (SALUTEM + pendientes de gestión).
 *
 * Covers:
 *  1. Muestra KPIs del período y pendientes de hoy, con la tasa de inasistencia.
 *  2. Por defecto pide los últimos 30 días; el preset "7 días" vuelve a pedir con otro rango.
 *  3. Etiqueta legible de los tipos de alerta y mensajes vacíos.
 */
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { DashboardPage } from "./DashboardPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

const RESPUESTA = {
  periodo_desde: "2026-09-17",
  periodo_hasta: "2026-10-16",
  pacientes_activos: 42,
  ingresos_periodo: 5,
  altas_periodo: 2,
  atenciones: 120,
  inasistencias: 30,
  anulaciones: 4,
  tasa_inasistencia: 20,
  agendadas_proximas: 18,
  controles_periodo: 9,
  licencias_activas: 11,
  licencias_pendientes_isl: 3,
  odas_vencidas: 1,
  odas_por_vencer: 2,
  ept_abiertos: 6,
  pacientes_pendientes_folio: 0,
  alertas_abiertas: 3,
  alertas_por_tipo: [
    { etiqueta: "oda_por_vencer", total: 2 },
    { etiqueta: "paciente_pendiente_folio", total: 1 },
  ],
  activos_por_programa: [],
  atenciones_por_especialidad: [],
  atenciones_por_profesional: [],
  tendencia_semanal: [],
};

function renderizar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function diasDelRango(url: URL): number {
  const d = new Date(url.searchParams.get("fecha_desde") + "T00:00:00");
  const h = new Date(url.searchParams.get("fecha_hasta") + "T00:00:00");
  return Math.round((h.getTime() - d.getTime()) / 86_400_000) + 1;
}

describe("DashboardPage", () => {
  it("muestra actividad del período y pendientes de hoy", async () => {
    server.use(http.get(`${BASE}/api/v1/dashboard/operativo`, () => HttpResponse.json(RESPUESTA)));
    renderizar();

    await waitFor(() => expect(screen.getByTestId("kpi-Atenciones")).toHaveTextContent("120"));
    expect(screen.getByTestId("kpi-Inasistencias")).toHaveTextContent("30");
    expect(screen.getByText("20% de las citas")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-Casos activos")).toHaveTextContent("42");
    expect(screen.getByText("3 sin enviar al ISL")).toBeInTheDocument();
    expect(screen.getByText(/período 17-09-2026 al 16-10-2026/)).toBeInTheDocument();
    expect(screen.getByText("ODA por vencer")).toBeInTheDocument();
    expect(screen.getByText("Paciente pendiente de folio")).toBeInTheDocument();
    expect(screen.getByText(/Sin atenciones registradas en SALUTEM/)).toBeInTheDocument();
    expect(screen.getByText("No hay casos activos.")).toBeInTheDocument();
  });

  it("pide 30 días por defecto y 7 días al elegir el preset", async () => {
    const rangos: number[] = [];
    server.use(
      http.get(`${BASE}/api/v1/dashboard/operativo`, ({ request }) => {
        rangos.push(diasDelRango(new URL(request.url)));
        return HttpResponse.json(RESPUESTA);
      }),
    );
    renderizar();
    await waitFor(() => expect(rangos).toEqual([30]));

    await userEvent.click(screen.getByRole("button", { name: "7 días" }));
    await waitFor(() => expect(rangos).toEqual([30, 7]));
  });
});
