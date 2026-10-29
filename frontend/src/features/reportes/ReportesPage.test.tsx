import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ReportesPage } from "./ReportesPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// JWT sin firma válida: el frontend solo decodifica el payload (rol Coordinacion / Auditor).
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage(ruta = "/reportes", token = WRITER_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
        <AuthProvider>
          <Toaster />
          <ReportesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

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
    renderPage();
    fireEvent.click(screen.getByText("Adherencia", { selector: "button *, button" }));
    fireEvent.change(screen.getByTestId("input-folio-adherencia"), { target: { value: "1" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByTestId("kpi-adherencia")).toBeTruthy();
    expect(screen.getByTestId("ayuda-adherencia").textContent).toBe(
      "Atendidas sobre el total de citas atendidas más inasistencias. Las anuladas y las futuras no cuentan.",
    );
  });
});

describe("ReportesPage — pestaña desde la URL", () => {
  it("?tab=odas abre la pestaña de ODAS vencidas", () => {
    renderPage("/reportes?tab=odas");
    expect(screen.getByText(/ODAS con fecha de vencimiento pasada a hoy/)).toBeTruthy();
  });
});

// ── Carga del Reporte Prestador del ISL (QA-004) ─────────────────────────────

const RESUMEN = {
  archivo: "reporte.xlsx",
  filas_leidas: 4,
  creadas: 1,
  actualizadas: 1,
  sin_cambios: 0,
  match_por_siniestro: 2,
  match_por_rut: 0,
  sin_paciente: [
    { fila: 4, numero_orden: "900002", tipo_orden: "Ambulatoria", numero_siniestro: "1000002", rut_trabajador: null },
  ],
  errores: [{ fila: 5, motivo: "Orden 3: fecha inválida «x»." }],
  ventana_dias: 7,
  por_vencer_paciente_activo: 1,
  por_vencer: [
    { oda_id: 1, ingreso_id: 1, folio: "F-1", numero_orden: "900001", fecha_vencimiento: "2026-11-02" },
  ],
};

describe("ReportesPage — Cargar reporte ISL", () => {
  it("el Auditor no ve el botón de carga", () => {
    renderPage("/reportes?tab=odas", AUDITOR_TOKEN);
    expect(screen.queryByTestId("btn-cargar-reporte-isl")).toBeNull();
  });

  it("previsualiza en dry run, confirma y muestra el resumen", async () => {
    const llamadas: string[] = [];
    server.use(
      http.post(`${BASE}/api/v1/odas/importar`, async ({ request }) => {
        const dry = new URL(request.url).searchParams.get("dry_run");
        llamadas.push(dry ?? "");
        return HttpResponse.json({ ...RESUMEN, dry_run: dry === "true" });
      }),
    );
    renderPage("/reportes?tab=odas");
    fireEvent.click(screen.getByTestId("btn-cargar-reporte-isl"));

    const boton = await screen.findByTestId("btn-previsualizar-isl");
    expect((boton as HTMLButtonElement).disabled).toBe(true);
    const archivo = new File(["x"], "reporte.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    fireEvent.change(screen.getByTestId("input-archivo-isl"), { target: { files: [archivo] } });
    fireEvent.click(boton);

    expect((await screen.findByTestId("estado-importacion")).textContent).toMatch(/Previsualización/);
    expect(screen.getByTestId("dato-creadas").textContent).toBe("1");
    expect(screen.getByTestId("dato-sin-paciente").textContent).toBe("1");
    expect(screen.getByText(/siniestro 1000002/)).toBeTruthy();
    expect(screen.getByText(/Fila 5: Orden 3/)).toBeTruthy();
    expect(screen.getByTestId("por-vencer").textContent).toMatch(/1 ODA\(S\).*7 días/);

    fireEvent.click(screen.getByTestId("btn-confirmar-isl"));
    await waitFor(() =>
      expect(screen.getByTestId("estado-importacion").textContent).toBe("Carga completada."),
    );
    expect(llamadas).toEqual(["true", "false"]);
    expect(screen.getByTestId("btn-cerrar-isl")).toBeTruthy();
  });

  it("muestra el error del backend si el archivo no sirve", async () => {
    server.use(
      http.post(`${BASE}/api/v1/odas/importar`, () =>
        HttpResponse.json({ detail: "Faltan columnas en el archivo: N° Siniestro." }, { status: 422 }),
      ),
    );
    renderPage("/reportes?tab=odas");
    fireEvent.click(screen.getByTestId("btn-cargar-reporte-isl"));
    fireEvent.change(await screen.findByTestId("input-archivo-isl"), {
      target: { files: [new File(["x"], "malo.xlsx")] },
    });
    fireEvent.click(screen.getByTestId("btn-previsualizar-isl"));
    expect(await screen.findByText("Faltan columnas en el archivo: N° Siniestro.")).toBeTruthy();
    expect(screen.queryByTestId("resumen-importacion")).toBeNull();
  });
});
