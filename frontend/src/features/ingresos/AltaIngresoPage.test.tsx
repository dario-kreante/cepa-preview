import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen } from "@testing-library/react";
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
});
