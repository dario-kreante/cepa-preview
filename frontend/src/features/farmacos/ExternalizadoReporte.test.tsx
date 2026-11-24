import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ExternalizadoReporte } from "./ExternalizadoReporte";
import { FarmacosPage } from "./FarmacosPage";

const BASE = import.meta.env.VITE_API_BASE_URL;
const URL_REPORTE = `${BASE}/api/v1/reportes/farmacos-convenio`;

// Payloads: {"role":"Coordinacion"} y {"role":"Auditor"} (el frontend solo decodifica).
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const ITEM = {
  origen: "Receta",
  registro_id: 1,
  fecha: "2031-05-03",
  paciente_id: 7,
  paciente_nombre: "Paciente Ficticio",
  paciente_rut: "11.111.111-1",
  folio: "F-001",
  ingreso_id: 10,
  programa: "Programa Regular",
  farmaco: "Melatonina 3 mg",
  dosis: null,
  codigo_sap: null,
  clasificacion: "REVISAR",
  detalle: "Coincide con opciones de distintos convenios (Convenio 001 y Convenio 002).",
  coincidencias: ["MELATONINA 3MG.30CAP.", "MELATONINA 3 MG 60 CAPS"],
};

function respuesta(items = [ITEM]) {
  return {
    fecha_desde: "2031-05-01",
    fecha_hasta: "2031-05-31",
    total: items.length,
    resumen: [
      { clasificacion: "Convenio 002", total: 0 },
      { clasificacion: "Convenio 001", total: 0 },
      { clasificacion: "REVISAR", total: items.length },
      { clasificacion: "Fuera de convenio", total: 0 },
    ],
    items,
  };
}

function envolver(ui: React.ReactNode, token = WRITER_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function elegirPeriodo() {
  fireEvent.change(screen.getByLabelText("Desde *"), { target: { value: "2031-05-01" } });
  fireEvent.change(screen.getByLabelText("Hasta *"), { target: { value: "2031-05-31" } });
}

describe("ExternalizadoReporte", () => {
  it("exige el período antes de generar", () => {
    envolver(<ExternalizadoReporte />);
    expect((screen.getByTestId("btn-generar-externalizado") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Desde *"), { target: { value: "2031-05-31" } });
    fireEvent.change(screen.getByLabelText("Hasta *"), { target: { value: "2031-05-01" } });
    expect(screen.getByText("La fecha desde no puede ser posterior a la fecha hasta.")).toBeTruthy();
    expect((screen.getByTestId("btn-generar-externalizado") as HTMLButtonElement).disabled).toBe(true);
  });

  it("muestra cada fármaco con su clasificación, el detalle y el resumen", async () => {
    let consulta: URLSearchParams | null = null;
    server.use(
      http.get(URL_REPORTE, ({ request }) => {
        consulta = new URL(request.url).searchParams;
        return HttpResponse.json(respuesta());
      }),
    );
    envolver(<ExternalizadoReporte />);
    elegirPeriodo();
    fireEvent.click(screen.getByTestId("btn-generar-externalizado"));
    expect(await screen.findByText("Melatonina 3 mg")).toBeTruthy();
    expect(screen.getByText("Paciente Ficticio")).toBeTruthy();
    expect(screen.getByText("MELATONINA 3MG.30CAP. / MELATONINA 3 MG 60 CAPS")).toBeTruthy();
    expect(screen.getByTestId("ext-resumen").textContent).toContain("REVISAR: 1");
    expect(consulta!.get("fecha_desde")).toBe("2031-05-01");
    expect(consulta!.get("paciente_id")).toBeNull();
  });

  it("puede acotarse al paciente elegido", async () => {
    let consulta: URLSearchParams | null = null;
    server.use(
      http.get(URL_REPORTE, ({ request }) => {
        consulta = new URL(request.url).searchParams;
        return HttpResponse.json(respuesta([]));
      }),
    );
    envolver(<ExternalizadoReporte paciente={{ id: 7, nombre: "Paciente Ficticio" }} />);
    elegirPeriodo();
    fireEvent.click(screen.getByTestId("ext-solo-paciente"));
    fireEvent.click(screen.getByTestId("btn-generar-externalizado"));
    expect(await screen.findByText("Sin fármacos recetados en el período.")).toBeTruthy();
    expect(consulta!.get("paciente_id")).toBe("7");
  });

  it("descarga el Excel con el mismo período", async () => {
    let pedido = false;
    server.use(
      http.get(`${URL_REPORTE}/excel`, () => {
        pedido = true;
        return new HttpResponse(new Blob(["x"]), {
          headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
        });
      }),
    );
    URL.createObjectURL = () => "blob:prueba";
    URL.revokeObjectURL = () => {};
    envolver(<ExternalizadoReporte />);
    elegirPeriodo();
    fireEvent.click(screen.getByTestId("btn-excel-externalizado"));
    await waitFor(() => expect(pedido).toBe(true));
  });
});

describe("FarmacosPage — vista del reporte Externalizado", () => {
  it("Coordinación cambia a la vista del reporte", () => {
    envolver(<FarmacosPage />);
    fireEvent.click(screen.getByTestId("vista-farmacos-externalizado"));
    expect(screen.getByTestId("btn-generar-externalizado")).toBeTruthy();
    expect(screen.queryByLabelText("Buscar pacientes")).toBeNull();
  });

  it("Auditor no ve el reporte", () => {
    envolver(<FarmacosPage />, AUDITOR_TOKEN);
    expect(screen.queryByTestId("vista-farmacos-externalizado")).toBeNull();
    expect(screen.getByLabelText("Buscar pacientes")).toBeTruthy();
  });
});
