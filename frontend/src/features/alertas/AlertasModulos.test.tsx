import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { AppShell } from "@/app/shell/AppShell";
import { EptPage } from "@/features/ept/EptPage";
import { LicenciasPage } from "@/features/licencias/LicenciasPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Payload: {"sub":"1","username":"coord","role":"Coordinacion",...}
const TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function alerta(id: number, o: Record<string, unknown> = {}) {
  return {
    id,
    tipo: "plazo_insumos_ept",
    estado: "pendiente",
    caso_id: 100 + id,
    caso_tipo: "ept",
    usuario_id: null,
    plazo_objetivo: "2026-11-20T00:00:00Z",
    ventana_dias: 3,
    generada_en: "2026-11-17T10:00:00Z",
    resuelta_en: null,
    email_enviado: false,
    paciente_id: 7,
    paciente_nombre: "María González",
    ...o,
  };
}

// 2 EPT pendientes, 1 EPT resuelta, 2 de licencia pendientes (una en un control), 1 de ODA.
const ALERTAS = [
  alerta(1),
  alerta(2, { paciente_nombre: "Pedro Soto", paciente_id: 8, caso_id: 202 }),
  alerta(3, { estado: "resuelta" }),
  alerta(4, { tipo: "vencimiento_licencia", caso_tipo: "licencia", caso_id: 44 }),
  alerta(5, { tipo: "licencia_en_control", caso_tipo: "control_medico", caso_id: 55, paciente_nombre: "Pedro Soto", paciente_id: 8 }),
  alerta(6, { tipo: "oda_por_vencer", caso_tipo: "oda" }),
];

function conAlertas(data: object[]) {
  server.use(http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json(data)));
}

function montar(ui: React.ReactNode, ruta = "/") {
  tokenStore.setAccess(TOKEN);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  server.use(
    http.get(`${BASE}/api/v1/pendientes-folio`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/casos-ept/:id`, () => HttpResponse.json({ id: 101, ingreso_id: 1, mes: "Nov", fecha_ingreso_ept: "2026-11-01", nombre_trabajador: "María González", rut_trabajador: "1-9", region_trabajador: "Maule", eista: "E", factor_riesgo: "sobrecarga", corresponde_ept: true, estado: "abierto" })),
  );
});

describe("alertas pendientes al entrar a EPT", () => {
  it("lista paciente, tipo y vencimiento de las pendientes, y su cantidad es la del menú", async () => {
    conAlertas(ALERTAS);
    montar(
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<EptPage />} />
        </Route>
      </Routes>,
    );
    const lista = await screen.findByTestId("alertas-pendientes-modulo");
    const filas = within(lista).getAllByRole("button");
    expect(filas).toHaveLength(2);
    expect(within(lista).getByText("Alertas pendientes de revisión (2)")).toBeInTheDocument();
    expect(within(lista).getByText("María González")).toBeInTheDocument();
    expect(within(lista).getAllByText("Plazo de insumos EPT (hoy)")).toHaveLength(2);
    expect(within(lista).getAllByText(/20.11.2026/)).toHaveLength(2);

    // El número rojo del menú para el mismo usuario.
    const itemMenu = screen.getByRole("link", { name: /Seguimiento EPT/ });
    expect(within(itemMenu).getByText("2")).toBeInTheDocument();
  });

  it("al hacer clic abre el caso EPT de la alerta", async () => {
    conAlertas(ALERTAS);
    montar(<EptPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Abrir alerta/ }))[0]);
    expect(await screen.findByText(/Caso N° 101/)).toBeInTheDocument();
  });

  it("sin alertas EPT pendientes no muestra la sección", async () => {
    conAlertas([alerta(6, { tipo: "oda_por_vencer", caso_tipo: "oda" })]);
    montar(<EptPage />);
    expect(await screen.findByText("Seguimiento EPT")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByTestId("alertas-pendientes-modulo")).toBeNull();
  });

  it("si fallan las alertas avisa y deja la página usable", async () => {
    server.use(http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json({}, { status: 500 })));
    montar(<EptPage />);
    expect(await screen.findByText("No se pudieron cargar las alertas.")).toBeInTheDocument();
    expect(screen.getByLabelText("Buscar pacientes")).toBeInTheDocument();
  });
});

describe("alertas pendientes al entrar a Licencias", () => {
  it("lista las alertas de licencia (incluidas las de un control) con la cantidad del menú", async () => {
    conAlertas(ALERTAS);
    montar(
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<LicenciasPage />} />
        </Route>
      </Routes>,
    );
    const lista = await screen.findByTestId("alertas-pendientes-modulo");
    expect(within(lista).getAllByRole("button")).toHaveLength(2);
    expect(within(lista).getByText("Licencia emitida en control")).toBeInTheDocument();
    const itemMenu = screen.getByRole("link", { name: /Licencias médicas/ });
    expect(within(itemMenu).getByText("2")).toBeInTheDocument();
  });

  it("al hacer clic abre las licencias de ese paciente", async () => {
    conAlertas(ALERTAS);
    server.use(
      http.get(`${BASE}/api/v1/pacientes/:id/vista-360`, () =>
        HttpResponse.json({ paciente: { id: 7, nombre: "María González" }, ingresos: [{ id: 5, folio: "F-1" }] }),
      ),
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({ ingreso_id: 5, dias_acumulados: 0, historial: [] }),
      ),
    );
    montar(<LicenciasPage />);
    await userEvent.click((await screen.findAllByRole("button", { name: /Abrir alerta/ }))[0]);
    expect(await screen.findByText("Sin licencias para este paciente.")).toBeInTheDocument();
  });

  it("sin alertas de licencia no muestra la sección", async () => {
    conAlertas([]);
    montar(<LicenciasPage />);
    expect(await screen.findByText("Licencias médicas")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByTestId("alertas-pendientes-modulo")).toBeNull();
  });
});
