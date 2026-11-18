/**
 * QA-004 — Reporte de ingresos.
 *  1. Una fila por ingreso (nombre, RUT, folio, tipo, programa, región) y «Pendiente» sin folio.
 *  2. Pide el período de la URL (?desde=…&hasta=…).
 *  3. Muestra los totales por tipo de ingreso, región, programa y convenio.
 *  4. Cambiar de fechas y aplicar vuelve a pedir; los atajos Semana / Mes fijan el rango.
 *  5. Rango invertido deshabilita «Aplicar».
 */
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { ReporteIngresosPage } from "./ReporteIngresosPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

const RESPUESTA = {
  periodo_desde: "2026-11-09",
  periodo_hasta: "2026-11-15",
  total: 2,
  total_con_folio: 1,
  total_pendientes: 1,
  por_tipo_ingreso: [
    { etiqueta: "convenio", total: 1 },
    { etiqueta: "Pendiente de folio", total: 1 },
  ],
  por_region: [
    { etiqueta: "Maule", total: 1 },
    { etiqueta: "Sin región", total: 1 },
  ],
  por_programa: [
    { etiqueta: "DIEP", total: 1 },
    { etiqueta: "Sin programa", total: 1 },
  ],
  por_convenio: [
    { etiqueta: "ISL", total: 1 },
    { etiqueta: "Sin convenio", total: 1 },
  ],
  items: [
    {
      paciente_id: 1, ingreso_id: 10, paciente_nombre: "Ana Uno", paciente_rut: "11111111-1",
      folio: "F-1", pendiente: false, tipo_ingreso: "convenio", programa: "DIEP",
      region: "Maule", tipo_convenio: "ISL", fecha: "2026-11-10",
    },
    {
      paciente_id: 2, ingreso_id: null, paciente_nombre: "Pendiente Cuatro", paciente_rut: null,
      folio: null, pendiente: true, tipo_ingreso: null, programa: null,
      region: null, tipo_convenio: null, fecha: "2026-11-12",
    },
  ],
};

function renderPage(ruta = "/reportes/ingresos?desde=2026-11-09&hasta=2026-11-15") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
        <ReporteIngresosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockApi(capturas: URL[] = []) {
  server.use(
    http.get(`${BASE}/api/v1/reportes/ingresos`, ({ request }) => {
      capturas.push(new URL(request.url));
      return HttpResponse.json(RESPUESTA);
    }),
  );
}

describe("ReporteIngresosPage", () => {
  it("lista una fila por ingreso y marca los pendientes de folio", async () => {
    mockApi();
    renderPage();
    const filaAna = (await screen.findByText("Ana Uno")).closest("tr")!;
    expect(within(filaAna).getByText("11111111-1")).toBeInTheDocument();
    expect(within(filaAna).getByText("F-1")).toBeInTheDocument();
    expect(within(filaAna).getByText("Convenio")).toBeInTheDocument();
    expect(within(filaAna).getByText("DIEP")).toBeInTheDocument();
    expect(within(filaAna).getByText("Maule")).toBeInTheDocument();
    const filaPen = screen.getByText("Pendiente Cuatro").closest("tr")!;
    expect(within(filaPen).getByText("Pendiente")).toBeInTheDocument();
  });

  it("pide el período de la URL y muestra los totales", async () => {
    const capturas: URL[] = [];
    mockApi(capturas);
    renderPage();
    await screen.findByText("Ana Uno");
    expect(capturas[0].searchParams.get("fecha_desde")).toBe("2026-11-09");
    expect(capturas[0].searchParams.get("fecha_hasta")).toBe("2026-11-15");
    expect(screen.getByTestId("total-ingresos")).toHaveTextContent("2");
    expect(screen.getByTestId("total-con-folio")).toHaveTextContent("1");
    expect(screen.getByTestId("total-pendientes")).toHaveTextContent("1");
    for (const titulo of ["Por tipo de ingreso", "Por región", "Por programa", "Por convenio"]) {
      expect(screen.getByRole("heading", { name: titulo })).toBeInTheDocument();
    }
    const tipos = screen.getByTestId("totales-tipo");
    expect(within(tipos).getByText("Convenio")).toBeInTheDocument();
    expect(within(tipos).getByText("Pendiente de folio")).toBeInTheDocument();
    expect(within(screen.getByTestId("totales-convenio")).getByText("ISL")).toBeInTheDocument();
  });

  it("al cambiar las fechas y aplicar, vuelve a pedir", async () => {
    const capturas: URL[] = [];
    mockApi(capturas);
    renderPage();
    await screen.findByText("Ana Uno");
    const user = userEvent.setup();
    const desde = screen.getByLabelText("Desde");
    await user.clear(desde);
    await user.type(desde, "2026-11-01");
    await user.click(screen.getByTestId("btn-aplicar"));
    await waitFor(() =>
      expect(capturas.at(-1)!.searchParams.get("fecha_desde")).toBe("2026-11-01"),
    );
  });

  it("los atajos Esta semana y Este mes fijan el rango", async () => {
    const capturas: URL[] = [];
    mockApi(capturas);
    renderPage();
    await screen.findByText("Ana Uno");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Esta semana" }));
    await waitFor(() => expect(capturas.length).toBeGreaterThan(1));
    const sem = capturas.at(-1)!.searchParams;
    expect(new Date(sem.get("fecha_desde")! + "T00:00:00").getDay()).toBe(1); // lunes
    await user.click(screen.getByRole("button", { name: "Este mes" }));
    await waitFor(() =>
      expect(capturas.at(-1)!.searchParams.get("fecha_desde")).toMatch(/-01$/),
    );
  });

  it("rango invertido deshabilita Aplicar", async () => {
    mockApi();
    renderPage();
    await screen.findByText("Ana Uno");
    const user = userEvent.setup();
    const hasta = screen.getByLabelText("Hasta");
    await user.clear(hasta);
    await user.type(hasta, "2026-11-01");
    expect(screen.getByTestId("btn-aplicar")).toBeDisabled();
    expect(screen.getByText(/posterior/i)).toBeInTheDocument();
  });

  it("sin ingresos en el período muestra un aviso", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/ingresos`, () =>
        HttpResponse.json({ ...RESPUESTA, total: 0, total_con_folio: 0, total_pendientes: 0, items: [],
          por_tipo_ingreso: [], por_region: [], por_programa: [], por_convenio: [] }),
      ),
    );
    renderPage();
    expect(await screen.findByText(/No hay ingresos en este período/i)).toBeInTheDocument();
  });
});
