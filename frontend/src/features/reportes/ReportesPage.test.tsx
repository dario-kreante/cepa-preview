import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { ReportesPage } from "./ReportesPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("ReportesPage — pestaña Adherencia", () => {
  it("explica el criterio del denominador bajo el KPI", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/adherencia/:folio_id`, () =>
        HttpResponse.json({
          folio_id: 1,
          citas_agendadas: 3,
          citas_realizadas: 2,
          pct_adherencia: 66.67,
          sesiones_realizadas: 2,
          sesiones_plan: null,
          aumentos_isl: 0,
          pct_avance: null,
        }),
      ),
    );
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <ReportesPage />
      </QueryClientProvider>,
    );
    fireEvent.click(
      screen.getByText("Adherencia", { selector: "button *, button" }),
    );
    fireEvent.change(screen.getByTestId("input-folio-adherencia"), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByTestId("kpi-adherencia")).toBeTruthy();
    expect(screen.getByTestId("ayuda-adherencia").textContent).toBe(
      "Atendidas sobre el total de citas atendidas más inasistencias. Las anuladas y las futuras no cuentan.",
    );
  });
});
