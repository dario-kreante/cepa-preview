/**
 * Seguimiento de reintegro — QA-003: estado y fecha de la solicitud de RECA.
 * Solo los perfiles con escritura ven el botón para registrarla o corregirla.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { ReintegroPage } from "./ReintegroPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

const CASO = {
  id: 7,
  ingreso_id: 10,
  rut: "11.111.111-1",
  nombre: "Paciente Demo",
  tipo_derivacion: "DIEP",
  fecha_caso: "2026-06-20",
  sexo: "F",
  edad: 40,
  region: "Maule",
  comuna: null,
  rubro_empleador: null,
  razon_social: null,
  tipo_trabajador: null,
  estado_reintegro: "pendiente",
  fecha_reintegro: null,
  remitido_isl: false,
  alta_medica: false,
  fecha_alta_medica: null,
  alta_psicologica: false,
  fecha_alta_psico: null,
  tipo_alta: null,
  observaciones: null,
  fecha_solicitud_reca: null,
  estado_solicitud_reca: "pendiente",
};

function servir(caso: Record<string, unknown>, conReca = false) {
  server.use(
    http.get(`${BASE}/api/v1/reintegros/7`, () => HttpResponse.json(caso)),
    http.get(`${BASE}/api/v1/reintegros/7/reca`, () =>
      conReca
        ? HttpResponse.json({
            id: 1, caso_reintegro_id: 7, fecha_reca: "2026-06-30", tipo_reca: "AT", numero_reca: "A-1",
            riesgos_calificados: null, razon_social: "Empresa SA", solicita_medidas: false,
            detalle_medidas: null, fecha_medidas: null, verifica_medidas: false,
            detalle_verificacion: null, fecha_verificacion: null,
          })
        : HttpResponse.json({ detail: "sin reca" }, { status: 404 }),
    ),
  );
}

function renderPagina(rol: keyof typeof TOKENS) {
  tokenStore.setAccess(TOKENS[rol]);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/reintegro?caso=7"]}>
        <AuthProvider>
          <ReintegroPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => tokenStore.clear());

describe("ReintegroPage: solicitud de RECA", () => {
  it("un caso sin fecha ni RECA está Pendiente y ofrece registrar la solicitud", async () => {
    servir(CASO);
    renderPagina("Coordinacion");
    expect(await screen.findByTestId("estado-solicitud-reca")).toHaveTextContent("Pendiente");
    expect(screen.getByTestId("fecha-solicitud-reca")).toHaveTextContent("Sin fecha de solicitud");
    expect(screen.getByRole("button", { name: /Registrar solicitud/i })).toBeInTheDocument();
  });

  it("con fecha y sin RECA está Solicitada y permite corregir la fecha", async () => {
    servir({ ...CASO, fecha_solicitud_reca: "2026-06-24", estado_solicitud_reca: "solicitada" });
    renderPagina("Administrativo");
    expect(await screen.findByTestId("estado-solicitud-reca")).toHaveTextContent("Solicitada");
    expect(screen.getByTestId("fecha-solicitud-reca")).toHaveTextContent(/24/);
    await userEvent.click(screen.getByRole("button", { name: /Corregir fecha/i }));
    expect(await screen.findByText("Corregir solicitud de RECA")).toBeInTheDocument();
  });

  it("con la RECA registrada está Recibida", async () => {
    servir({ ...CASO, fecha_solicitud_reca: "2026-06-24", estado_solicitud_reca: "recibida" }, true);
    renderPagina("Coordinacion");
    expect(await screen.findByTestId("estado-solicitud-reca")).toHaveTextContent("Recibida");
  });

  it("el Auditor ve el estado pero no puede registrar ni corregir", async () => {
    servir({ ...CASO, fecha_solicitud_reca: "2026-06-24", estado_solicitud_reca: "solicitada" });
    renderPagina("Auditor");
    expect(await screen.findByTestId("estado-solicitud-reca")).toHaveTextContent("Solicitada");
    expect(screen.queryByTestId("btn-solicitud-reca")).not.toBeInTheDocument();
  });
});
