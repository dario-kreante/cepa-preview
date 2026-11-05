import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AltaIngresoPage } from "./AltaIngresoPage";

const BASE = import.meta.env.VITE_API_BASE_URL;
let lastBody: any = null;
const server = setupServer(
  http.post(`${BASE}/api/v1/ingresos`, async ({ request }) => {
    lastBody = await request.json();
    return HttpResponse.json({ id: 1, paciente_id: 1, folio: "F-2026-0001", estado: "activo", fecha_ingreso: lastBody.fecha_ingreso, folio_manual: false, numero_siniestro: null, fecha_diep_diat: null, tipo_derivacion: lastBody.tipo_derivacion, tipo_ingreso: lastBody.tipo_ingreso, modelo_tratamiento: lastBody.modelo_tratamiento, diagnostico: lastBody.diagnostico, razon_social: null, tipo_alta: null, fecha_alta: null, flag_revision: false, observaciones: null, tratamiento_iniciado: false }, { status: 201 });
  }),
);
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); lastBody = null; });
afterAll(() => server.close());

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter><AltaIngresoPage /></MemoryRouter></QueryClientProvider>);
}

describe("AltaIngresoPage", () => {
  it("rechaza RUT inválido sin llamar a la API", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/RUT/i), "11.111.111-2");
    await userEvent.type(screen.getByLabelText(/Nombre/i), "Ana");
    await userEvent.click(screen.getByRole("button", { name: /crear/i }));
    expect(await screen.findByText(/RUT inválido/i)).toBeInTheDocument();
    expect(lastBody).toBeNull();
  });

  it("la región se elige de una lista, no se escribe a mano", () => {
    renderPage();
    const region = screen.getByRole("combobox", { name: /Región/i });
    expect(region).toHaveValue("");
    expect(screen.getByRole("option", { name: "Maule" })).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: /Ñuble|Metropolitana|Biobío/ })).toHaveLength(3);
  });

  it("marca los obligatorios a simple vista y no los datos que se conocen después", () => {
    renderPage();
    expect(screen.getByText(/\* Campo obligatorio/i)).toBeInTheDocument();
    for (const nombre of [/^RUT \*/, /^Nombre \*/, /^Edad \*/, /^Región \*/, /^Fecha de ingreso \*/, /^Sexo \*/]) {
      expect(screen.getByLabelText(nombre)).toBeInTheDocument();
    }
    expect(screen.getByLabelText("Diagnóstico (opcional)")).toBeInTheDocument();
    expect(screen.getByLabelText("Modelo de tratamiento (opcional)")).toBeInTheDocument();
  });

  it("crea el ingreso sin diagnóstico ni modelo de tratamiento", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/^RUT/), "12.345.678-5");
    await userEvent.type(screen.getByLabelText(/^Nombre/), "Ana");
    await userEvent.type(screen.getByLabelText(/^Edad/), "35");
    await userEvent.selectOptions(screen.getByLabelText(/^Región/), "Maule");
    await userEvent.type(screen.getByLabelText(/^Fecha de ingreso/), "2026-11-05");
    await userEvent.click(screen.getByRole("button", { name: /crear/i }));
    await waitFor(() => expect(lastBody).not.toBeNull());
    expect(lastBody.region).toBe("Maule");
    expect(lastBody.diagnostico).toBeNull();
    expect(lastBody.modelo_tratamiento).toBeNull();
  });
});
