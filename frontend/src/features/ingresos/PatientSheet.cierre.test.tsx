import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { PatientSheet } from "./PatientSheet";

// jsdom no trae estas APIs y el Select de Radix las usa al abrirse.
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.scrollIntoView ??= () => {};

const BASE = import.meta.env.VITE_API_BASE_URL;

/** JWT sin firma verificable: la app solo decodifica el rol. */
function tokenDe(role: string): string {
  const b64 = (o: unknown) =>
    btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({
    sub: "1",
    username: "test",
    role,
    type: "access",
    exp: 9999999999,
  })}.firma`;
}

const INGRESO = {
  id: 55,
  paciente_id: 7,
  folio: "F-2026-0055",
  folio_manual: false,
  numero_siniestro: null,
  fecha_ingreso: "2026-01-15",
  fecha_diep_diat: null,
  tipo_derivacion: "DIEP",
  tipo_ingreso: "convenio",
  modelo_tratamiento: "ambulatorio",
  diagnostico: "Ansiedad",
  razon_social: null,
  estado: "activo",
  tipo_alta: null,
  fecha_alta: null,
  flag_revision: false,
  observaciones: null,
  tratamiento_iniciado: true,
  motivo_cierre: null,
  fecha_cierre: null,
  cierre_usuario: null,
};

function montar(ingreso: Record<string, unknown>) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente: { id: 7, rut: "11.222.333-4", nombre: "Carmen Soto", sexo: "F", edad: 42, region: "Valparaíso" },
        ingresos: [ingreso],
        farmacos: [],
        licencias: [],
        controles: [],
        odas: [],
        reintegro: [],
      }),
    ),
    http.get(`${BASE}/api/v1/ingresos/:id/licencias`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:id`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/registro-farmacologico/:id/recetas`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio`, () => HttpResponse.json([])),
  );
}

function renderSheet(role: string) {
  tokenStore.setAccess(tokenDe(role));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <PatientSheet pacienteId={7} open onOpenChange={() => {}} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PatientSheet — cierre del caso (QA-011)", () => {
  it("el botón Cerrar caso abre un diálogo y exige elegir un motivo", async () => {
    montar(INGRESO);
    let enviado: unknown = null;
    server.use(
      http.patch(`${BASE}/api/v1/ingresos/:id/estado`, async ({ request }) => {
        enviado = await request.json();
        return HttpResponse.json({ ...INGRESO, estado: "cerrado", motivo_cierre: "alta_medica" });
      }),
    );
    renderSheet("Administrativo");
    await userEvent.click(await screen.findByTestId("btn-cerrar-caso", {}, { timeout: 8000 }));
    const dialogo = await screen.findByRole("dialog", { name: /cerrar caso/i });
    const confirmar = within(dialogo).getByRole("button", { name: /confirmar cierre/i });
    expect(confirmar).toBeDisabled();
    await userEvent.click(within(dialogo).getByRole("combobox"));
    for (const m of [
      "RECA EC",
      "Alta médica",
      "Alta administrativa",
      "Abandono",
      "Desiste del proceso",
      "Cambio de prestador",
    ]) {
      expect(screen.getByRole("option", { name: m })).toBeInTheDocument();
    }
    await userEvent.click(screen.getByRole("option", { name: "Alta médica" }));
    expect(confirmar).toBeEnabled();
    await userEvent.click(confirmar);
    await waitFor(() => expect(enviado).toEqual({ estado: "cerrado", motivo_cierre: "alta_medica" }));
  });

  it("un caso en encuadre también se puede cerrar", async () => {
    montar({ ...INGRESO, estado: "encuadre" });
    renderSheet("Coordinacion");
    expect(await screen.findByTestId("btn-cerrar-caso", {}, { timeout: 8000 })).toBeInTheDocument();
  });

  it("muestra «Cerrado – motivo» y oculta el cierre en un caso cerrado", async () => {
    montar({
      ...INGRESO,
      estado: "cerrado",
      motivo_cierre: "alta_medica",
      fecha_cierre: "2026-11-18T14:00:00Z",
      cierre_usuario: "pilar",
    });
    renderSheet("Administrativo");
    expect(await screen.findByTestId("estado-ingreso", {}, { timeout: 8000 })).toHaveTextContent(
      "Cerrado – Alta médica",
    );
    expect(screen.queryByTestId("btn-cerrar-caso")).not.toBeInTheDocument();
    expect(screen.queryByTestId("btn-encuadre")).not.toBeInTheDocument();
  });

  it("Administrativo no ve el botón de reabrir; Coordinación sí", async () => {
    const cerrado = { ...INGRESO, estado: "cerrado", motivo_cierre: "abandono" };
    montar(cerrado);
    const { unmount } = renderSheet("Administrativo");
    await screen.findByTestId("estado-ingreso", {}, { timeout: 8000 });
    expect(screen.queryByTestId("btn-reabrir-caso")).not.toBeInTheDocument();
    unmount();
    renderSheet("Coordinacion");
    expect(await screen.findByTestId("btn-reabrir-caso", {}, { timeout: 8000 })).toBeInTheDocument();
  });

  it("Auditor no ve acciones de cierre ni de reapertura", async () => {
    montar(INGRESO);
    const { unmount } = renderSheet("Auditor");
    await screen.findByTestId("estado-ingreso", {}, { timeout: 8000 });
    expect(screen.queryByTestId("btn-cerrar-caso")).not.toBeInTheDocument();
    unmount();
    montar({ ...INGRESO, estado: "cerrado", motivo_cierre: "abandono" });
    renderSheet("Auditor");
    await screen.findByTestId("estado-ingreso", {}, { timeout: 8000 });
    expect(screen.queryByTestId("btn-reabrir-caso")).not.toBeInTheDocument();
  });

  it("Coordinación reabre el caso tras confirmar", async () => {
    montar({ ...INGRESO, estado: "cerrado", motivo_cierre: "abandono" });
    let enviado: unknown = null;
    server.use(
      http.patch(`${BASE}/api/v1/ingresos/:id/estado`, async ({ request }) => {
        enviado = await request.json();
        return HttpResponse.json(INGRESO);
      }),
    );
    renderSheet("Coordinacion");
    await userEvent.click(await screen.findByTestId("btn-reabrir-caso", {}, { timeout: 8000 }));
    const dialogo = await screen.findByRole("dialog", { name: /reabrir caso/i });
    await userEvent.click(within(dialogo).getByRole("button", { name: /confirmar reapertura/i }));
    await waitFor(() => expect(enviado).toEqual({ estado: "activo" }));
  });
});

describe("PatientSheet — historial de cierres (QA-007)", () => {
  it("sin cierres no muestra la sección", async () => {
    montar(INGRESO);
    renderSheet("Coordinacion");
    await screen.findByTestId("estado-ingreso", {}, { timeout: 8000 });
    expect(screen.queryByText("Historial de cierres")).not.toBeInTheDocument();
  });

  it("el aviso de reapertura dice que el cierre queda en el historial, no que se borra", async () => {
    montar({ ...INGRESO, estado: "cerrado", motivo_cierre: "abandono" });
    renderSheet("Coordinacion");
    await userEvent.click(await screen.findByTestId("btn-reabrir-caso", {}, { timeout: 8000 }));
    const dialogo = await screen.findByRole("dialog", { name: /reabrir caso/i });
    expect(dialogo).toHaveTextContent(/queda registrado en el historial de cierres/i);
    expect(dialogo).not.toHaveTextContent(/borrar/i);
    expect(within(dialogo).getByLabelText(/motivo de reapertura/i)).toBeInTheDocument();
  });

  it("cierre → reapertura con motivo → cierre deja dos registros, el más reciente primero", async () => {
    // Backend simulado con estado: el PATCH cierra/reabre y el historial se acumula.
    let ingreso: Record<string, unknown> = { ...INGRESO };
    const cierres: Record<string, unknown>[] = [];
    const cuerpos: unknown[] = [];
    montar(INGRESO);
    server.use(
      http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
        HttpResponse.json({
          paciente: { id: 7, rut: "11.222.333-4", nombre: "Carmen Soto", sexo: "F", edad: 42, region: "Valparaíso" },
          ingresos: [ingreso],
          farmacos: [],
          licencias: [],
          controles: [],
          odas: [],
          reintegro: [],
        }),
      ),
      http.get(`${BASE}/api/v1/ingresos/:id/cierres`, () => HttpResponse.json([...cierres].reverse())),
      http.patch(`${BASE}/api/v1/ingresos/:id/estado`, async ({ request }) => {
        const body = (await request.json()) as {
          estado: string;
          motivo_cierre?: string;
          motivo_reapertura?: string;
        };
        cuerpos.push(body);
        if (body.estado === "cerrado") {
          const n = cierres.length + 1;
          cierres.push({
            id: n,
            motivo_cierre: body.motivo_cierre,
            fecha_cierre: `2026-11-${10 + n}`,
            cerrado_por: "coord_maria",
            cerrado_en: `2026-11-${10 + n}T15:00:00Z`,
            reabierto_por: null,
            reabierto_en: null,
            motivo_reapertura: null,
          });
          ingreso = { ...ingreso, estado: "cerrado", motivo_cierre: body.motivo_cierre };
        } else {
          Object.assign(cierres[cierres.length - 1], {
            reabierto_por: "coord_maria",
            reabierto_en: "2026-11-12T15:00:00Z",
            motivo_reapertura: body.motivo_reapertura ?? null,
          });
          ingreso = { ...ingreso, estado: body.estado, motivo_cierre: null };
        }
        return HttpResponse.json(ingreso);
      }),
    );
    renderSheet("Coordinacion");

    const cerrarCon = async (motivo: string) => {
      await userEvent.click(await screen.findByTestId("btn-cerrar-caso", {}, { timeout: 8000 }));
      const dialogo = await screen.findByRole("dialog", { name: /cerrar caso/i });
      await userEvent.click(within(dialogo).getByRole("combobox"));
      await userEvent.click(screen.getByRole("option", { name: motivo }));
      await userEvent.click(within(dialogo).getByRole("button", { name: /confirmar cierre/i }));
      await waitFor(() => expect(screen.queryByRole("button", { name: /confirmar (cierre|reapertura)/i })).not.toBeInTheDocument());
    };

    await cerrarCon("Abandono");
    await userEvent.click(await screen.findByTestId("btn-reabrir-caso", {}, { timeout: 8000 }));
    const reabrir = await screen.findByRole("dialog", { name: /reabrir caso/i });
    await userEvent.type(within(reabrir).getByLabelText(/motivo de reapertura/i), "Retoma el tratamiento");
    await userEvent.click(within(reabrir).getByRole("button", { name: /confirmar reapertura/i }));
    await waitFor(() => expect(screen.queryByRole("button", { name: /confirmar (cierre|reapertura)/i })).not.toBeInTheDocument());
    await cerrarCon("Alta médica");

    expect(cuerpos).toEqual([
      { estado: "cerrado", motivo_cierre: "abandono" },
      { estado: "activo", motivo_reapertura: "Retoma el tratamiento" },
      { estado: "cerrado", motivo_cierre: "alta_medica" },
    ]);
    const historial = await screen.findByTestId("historial-cierres");
    expect(historial).toHaveTextContent("Historial de cierres");
    await waitFor(() => expect(within(historial).getAllByTestId("cierre-item")).toHaveLength(2));
    const [reciente, anterior] = within(historial).getAllByTestId("cierre-item");
    expect(reciente).toHaveTextContent("Alta médica");
    expect(reciente).toHaveTextContent("Cerrado el 12/11/2026 por coord_maria");
    expect(reciente).not.toHaveTextContent("Reabierto");
    expect(anterior).toHaveTextContent("Abandono");
    expect(anterior).toHaveTextContent("Cerrado el 11/11/2026 por coord_maria");
    expect(anterior).toHaveTextContent("Reabierto el 12/11/2026 por coord_maria — Retoma el tratamiento");
  }, 30000);
});
