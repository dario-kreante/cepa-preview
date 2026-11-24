import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ReportesPage } from "./ReportesPage";

const BASE = import.meta.env.VITE_API_BASE_URL;
const URL_REPORTE = `${BASE}/api/v1/reportes/ambulatorio`;

// JWT sin firma válida: el frontend solo decodifica el payload (rol Auditor, lector del reporte).
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const ITEM = {
  cita_id: 1,
  region: "Maule",
  codigo_region: "07",
  comuna: "Talca",
  codigo_comuna: "07101",
  numero_cuenta: null,
  opa: null,
  oda: "5550001",
  rut: "11.111.111-1",
  nombre: "Paciente Ficticio",
  cantidad: 1,
  codigo_prestacion: "3",
  glosa_prestacion: "Consulta psicológica tratamiento",
  fecha: "2031-03-10",
  hora: "09:30",
  monto_neto: null,
  iva: null,
  monto_total: null,
  folio: "F-001",
  programa: "Programa Regular",
};

function renderPage() {
  tokenStore.setAccess(AUDITOR_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/reportes?tab=ambulatorio"]}>
        <AuthProvider>
          <ReportesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function elegirPeriodo() {
  fireEvent.change(screen.getByLabelText("Desde *"), { target: { value: "2031-03-01" } });
  fireEvent.change(screen.getByLabelText("Hasta *"), { target: { value: "2031-03-31" } });
}

describe("ReportesPage — pestaña Ambulatorio", () => {
  it("está entre las pestañas y exige el período", () => {
    renderPage();
    expect(screen.getByTestId("tab-ambulatorio")).toBeTruthy();
    expect((screen.getByTestId("btn-generar-reporte") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("btn-excel-ambulatorio") as HTMLButtonElement).disabled).toBe(true);
  });

  it("muestra región, comuna y sus códigos y envía los filtros", async () => {
    let consulta: URLSearchParams | null = null;
    server.use(
      http.get(URL_REPORTE, ({ request }) => {
        consulta = new URL(request.url).searchParams;
        return HttpResponse.json({
          fecha_desde: "2031-03-01",
          fecha_hasta: "2031-03-31",
          total: 1,
          items: [ITEM],
        });
      }),
    );
    renderPage();
    elegirPeriodo();
    fireEvent.change(screen.getByLabelText("Programa"), { target: { value: "ley_karin" } });
    fireEvent.change(screen.getByLabelText("Región"), { target: { value: "Maule" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));

    expect(await screen.findByText("Paciente Ficticio")).toBeTruthy();
    for (const texto of ["Talca", "07", "07101", "5550001", "Consulta psicológica tratamiento", "09:30", "F-001"]) {
      expect(screen.getByText(texto)).toBeTruthy();
    }
    expect(screen.getByTestId("total-ambulatorio").textContent).toBe("1 atención");
    expect(consulta!.get("fecha_desde")).toBe("2031-03-01");
    expect(consulta!.get("fecha_hasta")).toBe("2031-03-31");
    expect(consulta!.get("programa")).toBe("ley_karin");
    expect(consulta!.get("region")).toBe("Maule");
  });

  it("sin atenciones muestra el estado vacío", async () => {
    server.use(
      http.get(URL_REPORTE, () =>
        HttpResponse.json({ fecha_desde: "2031-03-01", fecha_hasta: "2031-03-31", total: 0, items: [] }),
      ),
    );
    renderPage();
    elegirPeriodo();
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByText("Sin atenciones realizadas en el período.")).toBeTruthy();
  });

  it("descarga el Excel con los mismos filtros", async () => {
    let consulta: URLSearchParams | null = null;
    server.use(
      http.get(`${URL_REPORTE}/excel`, ({ request }) => {
        consulta = new URL(request.url).searchParams;
        return new HttpResponse(new Blob(["x"]), {
          headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
        });
      }),
    );
    URL.createObjectURL = () => "blob:prueba";
    URL.revokeObjectURL = () => {};
    renderPage();
    elegirPeriodo();
    fireEvent.change(screen.getByLabelText("Región"), { target: { value: "Biobío" } });
    fireEvent.click(screen.getByTestId("btn-excel-ambulatorio"));
    await waitFor(() => expect(consulta?.get("region")).toBe("Biobío"));
  });
});
