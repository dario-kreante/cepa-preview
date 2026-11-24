/**
 * QA-010 (QA 23-11-2026) — pestaña Reintegro:
 *  - Lista global sin buscar: casos activos y «Pendientes por registrar».
 *  - `?paciente=<id>&nuevo=1` (alerta de proyección): con caso activo lo muestra; sin él abre el
 *    alta precargada (ocupación y tipo de trabajador incluidos).
 *  - Marcar «Remitido a ISL» sin cerrar el caso.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { ReintegroPage } from "./ReintegroPage";
import { validarFechaRemision } from "./solicitudRecaSchema";

const BASE = import.meta.env.VITE_API_BASE_URL;

const PACIENTE = { id: 42, rut: "11.111.111-1", nombre: "Paciente Demo", sexo: "F", edad: 40, region: "Maule" };

function caso(id: number, over: Record<string, unknown> = {}) {
  return {
    id,
    ingreso_id: 10,
    rut: "111111111",
    nombre: "Paciente Demo",
    tipo_derivacion: "DIAT",
    fecha_caso: "2026-11-02",
    sexo: "F",
    edad: 40,
    region: "Maule",
    comuna: null,
    rubro_empleador: null,
    razon_social: null,
    tipo_trabajador: "dependiente",
    ocupacion: "Operario",
    estado_reintegro: "pendiente",
    fecha_reintegro: null,
    remitido_isl: false,
    fecha_remitido_isl: null,
    alta_medica: false,
    fecha_alta_medica: null,
    alta_psicologica: false,
    fecha_alta_psico: null,
    tipo_alta: null,
    observaciones: null,
    fecha_solicitud_reca: null,
    estado_solicitud_reca: "pendiente",
    ...over,
  };
}

const PANEL = {
  activos: [
    {
      caso_id: 7, ingreso_id: 10, paciente_id: 42, paciente_nombre: "Paciente Demo", rut: "111111111",
      folio: "F-2026-001", estado_reintegro: "parcial", fecha_caso: "2026-11-02",
      proyeccion: "3 semanas aproximadamente", fecha_proyeccion: "2026-11-10", es_isl: true,
      estado_solicitud_reca: "pendiente", reca_por_solicitar: true, pendiente_remitir_isl: true,
    },
    {
      caso_id: 8, ingreso_id: 11, paciente_id: 43, paciente_nombre: "Paciente Clínico", rut: null,
      folio: "F-2026-002", estado_reintegro: "pendiente", fecha_caso: "2026-11-05",
      proyeccion: null, fecha_proyeccion: null, es_isl: false,
      estado_solicitud_reca: "pendiente", reca_por_solicitar: false, pendiente_remitir_isl: false,
    },
  ],
  pendientes_registro: [
    {
      paciente_id: 44, paciente_nombre: "Paciente Sin Caso", rut: "222222222", ingreso_id: 12,
      folio: "F-2026-003", alerta_id: 90, proyeccion: "1 semana aproximadamente",
      fecha_control: "2026-11-18", plazo_estimado: "2026-11-25",
    },
  ],
};

function render_(ruta: string, rol: keyof typeof TOKENS = "Coordinacion") {
  tokenStore.setAccess(TOKENS[rol]);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
        <AuthProvider>
          <ReintegroPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

type IngresoMock = { id: number; folio: string; tipo_derivacion: string; razon_social: string | null; estado: string };

function servirPaciente(
  pacienteId: number,
  activos: unknown[],
  ingresos: IngresoMock[] = [
    { id: 10, folio: "F-1", tipo_derivacion: "DIAT", razon_social: "Forestal SpA", estado: "activo" },
  ],
) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/${pacienteId}/vista-360`, () =>
      HttpResponse.json({ paciente: { ...PACIENTE, id: pacienteId }, ingresos }),
    ),
    http.get(`${BASE}/api/v1/reintegros`, ({ request }) => {
      const u = new URL(request.url);
      if (u.searchParams.get("paciente_id") === String(pacienteId)) return HttpResponse.json(activos);
      return HttpResponse.json([]);
    }),
  );
}

function servirCaso(c: ReturnType<typeof caso>) {
  server.use(
    http.get(`${BASE}/api/v1/reintegros/${c.id}`, () => HttpResponse.json(c)),
    http.get(`${BASE}/api/v1/reintegros/${c.id}/reca`, () => HttpResponse.json({ detail: "sin reca" }, { status: 404 })),
  );
}

beforeEach(() => {
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  tokenStore.clear();
});

describe("Lista global de la pestaña Reintegro", () => {
  it("sin buscar muestra los casos activos con proyección y pendientes", async () => {
    server.use(http.get(`${BASE}/api/v1/reintegros/panel`, () => HttpResponse.json(PANEL)));
    render_("/reintegro");

    const fila = await screen.findByTestId("activo-7");
    expect(within(fila).getByText("Paciente Demo")).toBeInTheDocument();
    expect(within(fila).getByText("F-2026-001")).toBeInTheDocument();
    expect(within(fila).getByText("3 semanas aproximadamente")).toBeInTheDocument();
    expect(within(fila).getByText("RECA por solicitar")).toBeInTheDocument();
    expect(within(fila).getByText("No remitido a ISL")).toBeInTheDocument();
    const clinico = screen.getByTestId("activo-8");
    expect(within(clinico).queryByText("RECA por solicitar")).not.toBeInTheDocument();
    expect(within(clinico).getByText("Sin RUT")).toBeInTheDocument();
    expect(screen.getByText(/Casos de reintegro activos \(2\)/)).toBeInTheDocument();
  });

  it("muestra los pendientes por registrar con su plazo estimado", async () => {
    server.use(http.get(`${BASE}/api/v1/reintegros/panel`, () => HttpResponse.json(PANEL)));
    render_("/reintegro");

    const fila = await screen.findByTestId("pendiente-44");
    expect(within(fila).getByText("Paciente Sin Caso")).toBeInTheDocument();
    expect(within(fila).getByText("1 semana aproximadamente")).toBeInTheDocument();
    expect(screen.getByText(/Pendientes por registrar \(1\)/)).toBeInTheDocument();
  });

  it("al pinchar un caso activo lo carga", async () => {
    server.use(http.get(`${BASE}/api/v1/reintegros/panel`, () => HttpResponse.json(PANEL)));
    servirCaso(caso(7));
    render_("/reintegro");

    await userEvent.click(await screen.findByTestId("activo-7"));

    expect(await screen.findByText("Caso N° 7")).toBeInTheDocument();
  });

  it("«Registrar caso» abre el alta del paciente pendiente", async () => {
    server.use(http.get(`${BASE}/api/v1/reintegros/panel`, () => HttpResponse.json(PANEL)));
    servirPaciente(44, [], [
      { id: 11, folio: "F-OTRO", tipo_derivacion: "Particular", razon_social: null, estado: "activo" },
      { id: 12, folio: "F-2026-003", tipo_derivacion: "DIEP", razon_social: "Agrícola SpA", estado: "activo" },
    ]);
    render_("/reintegro");

    await userEvent.click(await screen.findByTestId("btn-registrar-44"));

    const dialogo = await screen.findByRole("dialog", { name: /Nuevo caso de reintegro/i });
    // Precarga desde el ingreso del control de la proyección (no el primero del paciente).
    expect(within(dialogo).getByLabelText(/Tipo de derivación/i)).toHaveValue("DIEP");
    expect(within(dialogo).getByLabelText(/Razón social/i)).toHaveValue("Agrícola SpA");
  });

  it("sin permiso de escritura no ofrece registrar", async () => {
    server.use(http.get(`${BASE}/api/v1/reintegros/panel`, () => HttpResponse.json(PANEL)));
    render_("/reintegro", "Auditor");

    await screen.findByTestId("pendiente-44");
    expect(screen.queryByTestId("btn-registrar-44")).not.toBeInTheDocument();
  });
});

describe("Desde la alerta de proyección (?paciente=&nuevo=1)", () => {
  it("sin caso activo abre el alta precargada con ocupación y tipo de trabajador", async () => {
    servirPaciente(42, []);
    server.use(
      http.get(`${BASE}/api/v1/reintegros/precarga`, () =>
        HttpResponse.json({ ocupacion: "Temporero", tipo_trabajador: "independiente" }),
      ),
    );
    render_("/reintegro?paciente=42&nuevo=1");

    const dialogo = await screen.findByRole("dialog", { name: /Nuevo caso de reintegro/i });
    expect(within(dialogo).getByLabelText(/Nombre/i)).toHaveValue("Paciente Demo");
    await waitFor(() => expect(within(dialogo).getByLabelText(/Ocupación/i)).toHaveValue("Temporero"));
    expect(within(dialogo).getByLabelText(/Tipo de trabajador/i)).toHaveValue("independiente");
    expect(screen.queryByTestId("panel-reintegro-global")).not.toBeInTheDocument();
  });

  it("envía la ocupación al crear el caso", async () => {
    servirPaciente(42, []);
    let body: Record<string, unknown> | null = null;
    server.use(
      http.get(`${BASE}/api/v1/reintegros/precarga`, () =>
        HttpResponse.json({ ocupacion: "Temporero", tipo_trabajador: "dependiente" }),
      ),
      http.post(`${BASE}/api/v1/reintegros`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(caso(30, { ocupacion: "Temporero" }), { status: 201 });
      }),
    );
    servirCaso(caso(30));
    render_("/reintegro?paciente=42&nuevo=1");
    const user = userEvent.setup();

    const dialogo = await screen.findByRole("dialog", { name: /Nuevo caso de reintegro/i });
    await waitFor(() => expect(within(dialogo).getByLabelText(/Ocupación/i)).toHaveValue("Temporero"));
    await user.type(within(dialogo).getByLabelText(/Fecha del caso/i), "2026-11-20");
    await user.click(within(dialogo).getByRole("button", { name: /Crear caso/i }));

    await waitFor(() => expect(body).not.toBeNull());
    expect(body).toMatchObject({ ingreso_id: 10, ocupacion: "Temporero", tipo_trabajador: "dependiente" });
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: /Nuevo caso de reintegro/i })).not.toBeInTheDocument(),
    );
  });

  it("con un caso activo lo muestra y no abre el alta", async () => {
    servirPaciente(42, [caso(7)]);
    servirCaso(caso(7));
    render_("/reintegro?paciente=42&nuevo=1");

    expect(await screen.findByText("Caso N° 7")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: /Nuevo caso de reintegro/i })).not.toBeInTheDocument();
  });

  it("el Auditor ve el paciente pero no se le abre el alta", async () => {
    servirPaciente(42, []);
    render_("/reintegro?paciente=42&nuevo=1", "Auditor");

    expect(await screen.findByTestId("paciente-seleccionado")).toHaveTextContent("Paciente Demo");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("cerrar el alta no la vuelve a abrir", async () => {
    servirPaciente(42, []);
    render_("/reintegro?paciente=42&nuevo=1");
    const user = userEvent.setup();

    const dialogo = await screen.findByRole("dialog", { name: /Nuevo caso de reintegro/i });
    await user.click(within(dialogo).getByRole("button", { name: /Cancelar/i }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByTestId("btn-nuevo-caso")).toBeEnabled();
  });
});

describe("Remitido a ISL sin cerrar el caso", () => {
  it("marca la remisión con su fecha", async () => {
    let body: Record<string, unknown> | null = null;
    servirCaso(caso(7));
    server.use(
      http.patch(`${BASE}/api/v1/reintegros/7/remitido-isl`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(caso(7, { remitido_isl: true, fecha_remitido_isl: "2026-11-09" }));
      }),
    );
    render_("/reintegro?caso=7");
    const user = userEvent.setup();

    expect(await screen.findByTestId("remitido-isl")).toHaveTextContent("No");
    await user.click(screen.getByTestId("btn-remitido-isl"));
    const dialogo = await screen.findByRole("dialog", { name: /Marcar remitido a ISL/i });
    const fecha = within(dialogo).getByLabelText(/Fecha de remisión/i);
    await user.clear(fecha);
    await user.type(fecha, "2026-11-09");
    await user.click(within(dialogo).getByRole("button", { name: /Guardar/i }));

    await waitFor(() => expect(body).toEqual({ fecha_remitido_isl: "2026-11-09" }));
  });

  it("muestra la fecha de remisión y ofrece corregirla", async () => {
    servirCaso(caso(7, { remitido_isl: true, fecha_remitido_isl: "2026-11-09" }));
    render_("/reintegro?caso=7");

    expect(await screen.findByTestId("remitido-isl")).toHaveTextContent(/Sí · 09/);
    expect(screen.getByTestId("btn-remitido-isl")).toHaveTextContent("Corregir fecha");
    expect(screen.getByText("Operario")).toBeInTheDocument();
  });

  it("el Auditor no puede marcar la remisión", async () => {
    servirCaso(caso(7));
    render_("/reintegro?caso=7", "Auditor");

    await screen.findByTestId("remitido-isl");
    expect(screen.queryByTestId("btn-remitido-isl")).not.toBeInTheDocument();
  });

  it("valida la fecha sin llamar al servidor", () => {
    expect(validarFechaRemision("", "2026-11-02", "2026-11-24")).toMatch(/Indica la fecha/);
    expect(validarFechaRemision("2026-11-25", "2026-11-02", "2026-11-24")).toMatch(/futura/);
    expect(validarFechaRemision("2026-11-01", "2026-11-02", "2026-11-24")).toMatch(/02-11-2026/);
    expect(validarFechaRemision("2026-11-09", "2026-11-02", "2026-11-24")).toBeNull();
  });
});
