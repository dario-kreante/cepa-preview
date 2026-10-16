import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { AlertsPanel, routeForCaso, tituloAlerta } from "./AlertsPanel";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("tituloAlerta", () => {
  it("nombra las alertas de licencia y receta del control", () => {
    expect(tituloAlerta("licencia_en_control")).toBe(
      "Licencia emitida en control",
    );
    expect(tituloAlerta("receta_en_control")).toBe("Receta emitida en control");
  });

  it("nombra la alerta de paciente nuevo pendiente de folio", () => {
    expect(tituloAlerta("paciente_pendiente_folio")).toBe(
      "Paciente nuevo pendiente de folio",
    );
  });

  it("los demás tipos conservan su título derivado", () => {
    expect(tituloAlerta("vencimiento_licencia")).toBe("Vencimiento licencia");
  });
});

describe("AlertsPanel: alertas de licencia del control", () => {
  it("al hacer clic en una alerta de licencia abre el control con sus documentos", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([
          {
            id: 1,
            tipo: "licencia_en_control",
            estado: "pendiente",
            caso_id: 5,
            caso_tipo: "control_medico",
            usuario_id: null,
            plazo_objetivo: "2026-10-15T00:00:00Z",
            ventana_dias: 0,
            generada_en: "2026-10-15T19:35:00Z",
            resuelta_en: null,
            email_enviado: false,
          },
        ]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/v1/controles-medicos/5`, () =>
        HttpResponse.json({
          id: 5,
          ingreso_id: 10,
          fecha_control: "2026-10-15",
          medico_tratante: "DRA. PAULA ROJAS",
          tiene_licencia: true,
          resumen_termino_lm: "LM tipo 6 por 30 días",
          tipo_reposo: "parcial",
          gaf_tramo: "41-50",
          origen: "SALUTEM",
        }),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([
          {
            archivo_id: 1,
            nombre: "LICENCIA.pdf",
            tipo: "documento",
            fecha_creacion: "2026-10-15T16:29:00",
          },
        ]),
      ),
    );
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <AlertsPanel />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(
      await screen.findByText("Licencia emitida en control"),
    );
    const dialogo = await screen.findByRole("dialog");
    expect(
      await within(dialogo).findByText(/DRA\. PAULA ROJAS/),
    ).toBeInTheDocument();
    expect(
      within(dialogo).getByText(/LM tipo 6 por 30 días/),
    ).toBeInTheDocument();
    expect(
      within(dialogo).getByText("Tipo de reposo").nextSibling,
    ).toHaveTextContent("Parcial");
    expect(within(dialogo).getByText("GAF").nextSibling).toHaveTextContent(
      "41-50",
    );
    expect(
      await within(dialogo).findByText("LICENCIA.pdf"),
    ).toBeInTheDocument();
    expect(
      within(dialogo).getByRole("button", { name: /ir a controles/i }),
    ).toBeInTheDocument();
  });
});

function alertaLicencia() {
  return {
    id: 1,
    tipo: "licencia_en_control",
    estado: "pendiente",
    caso_id: 5,
    caso_tipo: "control_medico",
    usuario_id: null,
    plazo_objetivo: "2026-10-15T00:00:00Z",
    ventana_dias: 0,
    generada_en: "2026-10-15T19:35:00Z",
    resuelta_en: null,
    email_enviado: false,
  };
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <AlertsPanel />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AlertsPanel: detalle de la alerta de control", () => {
  it("la meta dice Control con la fecha UTC del plazo (sin correrla al día anterior)", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([alertaLicencia()]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
    );
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    expect(screen.getByText(/^Control: 15 oct/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Plazo:/)).not.toBeInTheDocument();
  });

  it("si el control no existe el diálogo lo dice en vez de quedarse cargando", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([alertaLicencia()]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/v1/controles-medicos/5`, () =>
        HttpResponse.json({ detail: "Control no encontrado" }, { status: 404 }),
      ),
    );
    renderPanel();
    await userEvent.click(
      await screen.findByText("Licencia emitida en control"),
    );
    const dialogo = await screen.findByRole("dialog");
    expect(
      await within(dialogo).findByText(
        "No se encontró el control (pudo ser anulado en SALUTEM).",
      ),
    ).toBeInTheDocument();
    expect(
      within(dialogo).queryByText(/cargando control/i),
    ).not.toBeInTheDocument();
  });
});

describe("AlertsPanel: alerta de inasistencia", () => {
  it('muestra "Inasistencia a cita" con la fecha de la cita y abre la ficha del paciente', async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([
          {
            ...alertaLicencia(),
            id: 7,
            tipo: "inasistencia",
            caso_tipo: "salutem_cita",
            caso_id: 777001,
            paciente_id: 42,
          },
        ]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
    );
    renderPanel();
    expect(await screen.findByText("Inasistencia a cita")).toBeInTheDocument();
    expect(screen.getByText("Cita SALUTEM #777001")).toBeInTheDocument();
    expect(screen.getByText(/^Cita: 15 oct/i)).toBeInTheDocument();
  });

  it("tituloAlerta y routeForCaso conocen la inasistencia", () => {
    expect(tituloAlerta("inasistencia")).toBe("Inasistencia a cita");
    expect(routeForCaso("salutem_cita", 777001, 42)).toBe(
      "/ingresos?paciente=42",
    );
    expect(routeForCaso("salutem_cita", 777001)).toBe("/ingresos");
  });
});

describe("routeForCaso", () => {
  it("enruta EPT con deep-link por caso_id", () => {
    expect(routeForCaso("ept", 42)).toBe("/ept?caso=42");
  });

  it("EPT sin caso_id cae a la página del módulo", () => {
    expect(routeForCaso("ept", null)).toBe("/ept");
  });

  it("mapea cada caso_tipo a su módulo", () => {
    expect(routeForCaso("control_medico", 1)).toBe("/controles");
    expect(routeForCaso("receta", 1)).toBe("/farmacos");
    expect(routeForCaso("licencia", 1)).toBe("/licencias");
    expect(routeForCaso("oda", 1)).toBe("/ingresos");
    expect(routeForCaso("ingreso", 1)).toBe("/ingresos");
  });

  it("ODA con paciente abre su ficha directo en la pestaña ODA", () => {
    expect(routeForCaso("oda", 3, 42)).toBe("/ingresos?paciente=42&tab=odas");
    expect(routeForCaso("ingreso", 3, 42)).toBe("/ingresos?paciente=42");
  });

  it("tipo desconocido o nulo cae a /ingresos", () => {
    expect(routeForCaso("otro", 1)).toBe("/ingresos");
    expect(routeForCaso(null, null)).toBe("/ingresos");
  });
});

describe("AlertsPanel: leída al verla y resolver", () => {
  // jsdom no implementa IntersectionObserver: un doble que el test controla.
  type Callback = (
    entradas: Array<{ isIntersecting: boolean; target: Element }>,
  ) => void;
  let observadores: Array<{ cb: Callback; elementos: Element[] }> = [];
  class ObservadorFalso {
    private registro: { cb: Callback; elementos: Element[] };
    constructor(cb: Callback) {
      this.registro = { cb, elementos: [] };
      observadores.push(this.registro);
    }
    observe(el: Element) {
      this.registro.elementos.push(el);
    }
    unobserve() {}
    disconnect() {
      this.registro.elementos = [];
    }
  }
  function mostrarTodo(visible: boolean) {
    act(() => {
      for (const o of observadores) {
        o.cb(
          o.elementos.map((target) => ({ isIntersecting: visible, target })),
        );
      }
    });
  }

  beforeEach(() => {
    observadores = [];
    vi.stubGlobal("IntersectionObserver", ObservadorFalso);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  function conAlertas(alertas: unknown[]) {
    const cambios: Array<{ id: string; estado: string }> = [];
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json(alertas)),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.patch(`${BASE}/api/v1/alertas/:id`, async ({ request, params }) => {
        const body = (await request.json()) as { estado: string };
        cambios.push({ id: String(params.id), estado: body.estado });
        return HttpResponse.json({
          ...alertaLicencia(),
          id: Number(params.id),
          estado: body.estado,
        });
      }),
    );
    return cambios;
  }

  async function esperarVisible(ms: number) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, ms));
    });
  }

  it("no hay botón para marcar como leída; sí para resolver", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    conAlertas([alertaLicencia()]);
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    expect(
      screen.queryByRole("button", { name: /marcar como leída/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /resolver/i }),
    ).toBeInTheDocument();
  });

  it("una alerta pendiente queda leída tras verse 1,5 s en pantalla", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    const cambios = conAlertas([alertaLicencia()]);
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    mostrarTodo(true);
    await esperarVisible(1600);
    await vi.waitFor(() =>
      expect(cambios).toEqual([{ id: "1", estado: "leida" }]),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("si sale de la pantalla antes de 1,5 s no se marca", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    const cambios = conAlertas([alertaLicencia()]);
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    mostrarTodo(true);
    await esperarVisible(500);
    mostrarTodo(false);
    await esperarVisible(1500);
    expect(cambios).toEqual([]);
  });

  it("Coordinación no marca como leída la alerta asignada a otra persona", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    const cambios = conAlertas([
      { ...alertaLicencia(), id: 1, usuario_id: 99 },
      { ...alertaLicencia(), id: 2, usuario_id: null },
    ]);
    renderPanel();
    await screen.findAllByText("Licencia emitida en control");
    mostrarTodo(true);
    await esperarVisible(1600);
    await vi.waitFor(() =>
      expect(cambios).toEqual([{ id: "2", estado: "leida" }]),
    );
  });

  it("una alerta leída se puede resolver", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    const cambios = conAlertas([{ ...alertaLicencia(), estado: "leida" }]);
    renderPanel();
    await userEvent.click(
      await screen.findByRole("button", { name: /resolver/i }),
    );
    await vi.waitFor(() =>
      expect(cambios).toEqual([{ id: "1", estado: "resuelta" }]),
    );
  });

  it("el Auditor ve las alertas, sin botón y sin marcarlas como leídas", async () => {
    tokenStore.setAccess(TOKENS.Auditor);
    const cambios = conAlertas([alertaLicencia()]);
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    expect(
      screen.queryByRole("button", { name: /resolver/i }),
    ).not.toBeInTheDocument();
    mostrarTodo(true);
    await esperarVisible(1600);
    expect(cambios).toEqual([]);
  });
});

describe("AlertsPanel: paciente pendiente de folio", () => {
  it("se titula 'Paciente nuevo pendiente de folio' y al hacer clic navega a /pendientes-folio", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([
          {
            id: 9,
            tipo: "paciente_pendiente_folio",
            estado: "pendiente",
            caso_id: 7,
            caso_tipo: "paciente",
            usuario_id: null,
            plazo_objetivo: null,
            ventana_dias: 0,
            generada_en: "2026-10-16T09:00:00Z",
            resuelta_en: null,
            email_enviado: false,
          },
        ]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
    );
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route path="/" element={<AlertsPanel />} />
              <Route
                path="/pendientes-folio"
                element={<p>pantalla pendientes</p>}
              />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await userEvent.click(
      await screen.findByText("Paciente nuevo pendiente de folio"),
    );
    expect(await screen.findByText("pantalla pendientes")).toBeInTheDocument();
  });

  it("routeForCaso lleva el caso 'paciente' a /pendientes-folio", () => {
    expect(routeForCaso("paciente", 7)).toBe("/pendientes-folio");
  });
});

describe("AlertsPanel: sin leer y ventana flotante", () => {
  function conAlertas(alertas: unknown[]) {
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json(alertas)),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
    );
  }
  const base = {
    caso_id: 7,
    caso_tipo: "oda",
    plazo_objetivo: null,
    ventana_dias: 0,
    generada_en: "2026-10-15T19:35:00Z",
    resuelta_en: null,
    email_enviado: false,
  };

  it("destaca solo las pendientes para quien mira; las de otro profesional van rotuladas", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    conAlertas([
      {
        ...base,
        id: 1,
        tipo: "oda_por_vencer",
        estado: "pendiente",
        usuario_id: null,
      },
      { ...base, id: 2, tipo: "plazo_isl", estado: "leida", usuario_id: null },
      {
        ...base,
        id: 3,
        tipo: "plazo_ept",
        estado: "pendiente",
        usuario_id: 999,
      },
    ]);
    const { container } = renderPanel();
    await screen.findByText("Oda por vencer");
    expect(container.querySelectorAll("[data-sin-leer]")).toHaveLength(1);
    expect(screen.getAllByLabelText("Sin leer")).toHaveLength(1);
    expect(screen.getByText("Asignada a otro profesional")).toBeInTheDocument();
    expect(screen.getByText("· 1 sin leer")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sin leer (1)" }));
    expect(screen.getByText("Oda por vencer")).toBeInTheDocument();
    expect(screen.queryByText("Plazo isl")).not.toBeInTheDocument();
    expect(screen.queryByText("Plazo ept")).not.toBeInTheDocument();
  });

  it("al ir a una alerta la ventana se cierra; también con su botón", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    conAlertas([
      {
        ...base,
        id: 1,
        tipo: "oda_por_vencer",
        estado: "leida",
        usuario_id: null,
      },
    ]);
    const onClose = vi.fn();
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <AlertsPanel onClose={onClose} />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByText("Oda por vencer"));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.click(
      screen.getByRole("button", { name: "Cerrar alertas" }),
    );
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});

describe("AlertsPanel: licencia emitida en una atención médica que no es control", () => {
  it("se titula 'en atención médica' y abre la atención con su indicación y documentos", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([
          {
            id: 9,
            tipo: "licencia_en_control",
            estado: "leida",
            caso_id: 16625886,
            caso_tipo: "salutem_atencion",
            usuario_id: null,
            plazo_objetivo: "2026-10-15T00:00:00Z",
            ventana_dias: 0,
            generada_en: "2026-10-16T19:35:00Z",
            resuelta_en: null,
            email_enviado: false,
          },
        ]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/v1/salutem/atenciones/16625886`, () =>
        HttpResponse.json({
          cita_id: 16625886,
          fecha: "2026-10-15",
          especialidad: "Evaluación médica",
          profesional: "DRA. PAULA ROJAS",
          indicacion_licencia: "Reposo por 15 días desde el 15/10/2026",
          tipo_reposo: "Total",
          gaf_tramo: "51-60",
        }),
      ),
      http.get(`${BASE}/api/v1/salutem/atenciones/16625886/archivos`, () =>
        HttpResponse.json([
          {
            archivo_id: 1,
            nombre: "LICENCIA.pdf",
            tipo: "documento",
            fecha_creacion: "2026-10-15T16:29:00",
          },
        ]),
      ),
    );
    renderPanel();

    expect(
      await screen.findByText("Atención SALUTEM #16625886"),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Atención: 15 oct/i)).toBeInTheDocument();
    await userEvent.click(
      screen.getByText("Licencia emitida en atención médica"),
    );

    const dialogo = await screen.findByRole("dialog");
    expect(
      await within(dialogo).findByText(
        /Evaluación médica del 15-10-2026 · DRA\. PAULA ROJAS/,
      ),
    ).toBeInTheDocument();
    expect(
      within(dialogo).getByText("Reposo por 15 días desde el 15/10/2026"),
    ).toBeInTheDocument();
    // El ítem "Indicación de reposo" completo: indicación, tipo de reposo y GAF.
    expect(
      within(dialogo).getByText("Tipo de reposo").nextSibling,
    ).toHaveTextContent("Total");
    expect(within(dialogo).getByText("GAF").nextSibling).toHaveTextContent(
      "51-60",
    );
    expect(
      await within(dialogo).findByText("LICENCIA.pdf"),
    ).toBeInTheDocument();
    expect(
      within(dialogo).queryByRole("button", { name: /ir a controles/i }),
    ).not.toBeInTheDocument();
  });
});

describe("AlertsPanel: gestionar la alerta desde el diálogo", () => {
  const base = {
    estado: "pendiente",
    usuario_id: null,
    plazo_objetivo: "2026-10-15T00:00:00Z",
    ventana_dias: 0,
    generada_en: "2026-10-16T19:35:00Z",
    resuelta_en: null,
    email_enviado: false,
  };
  const CONTEXTO = {
    paciente_id: 82,
    paciente_nombre: "Humberto Escobar",
    ingreso_id: 102,
    folio: "F-2026-0063",
    cita_id: 16625886,
    fecha: "2026-10-15",
  };
  const SUGERIDA = {
    ficha_clinica_id: 207,
    cita_id: 16625886,
    cita_fecha: "2026-10-15",
    texto: "Reposo por 15 días desde el 15/10/2026",
    tipo_lm: null,
    tipo_reposo: "total",
    origen: "sistema",
    fecha_inicio: "2026-10-15",
    fecha_termino: "2026-10-29",
    termino_calculado: true,
    cantidad_dias: 15,
    eeag_gaf_tramo: "51-60",
    avisos: [],
    ya_registrada: false,
  };

  function conAtencion(alerta: Record<string, unknown>, sugeridas: unknown[]) {
    const cambios: Array<{ id: string; estado: string }> = [];
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json([alerta])),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/v1/alertas/:id/contexto`, () =>
        HttpResponse.json(CONTEXTO),
      ),
      http.get(
        `${BASE}/api/v1/fichas-clinicas/:folio/licencias-sugeridas`,
        () => HttpResponse.json(sugeridas),
      ),
      http.get(`${BASE}/api/v1/salutem/atenciones/16625886`, () =>
        HttpResponse.json({
          cita_id: 16625886,
          fecha: "2026-10-15",
          especialidad: "Evaluación médica",
          profesional: "PILAR GARCÍA",
          indicacion_licencia: SUGERIDA.texto,
        }),
      ),
      http.get(`${BASE}/api/v1/salutem/atenciones/16625886/archivos`, () =>
        HttpResponse.json([]),
      ),
      http.patch(`${BASE}/api/v1/alertas/:id`, async ({ request, params }) => {
        const body = (await request.json()) as { estado: string };
        cambios.push({ id: String(params.id), estado: body.estado });
        return HttpResponse.json({ ...alerta, estado: body.estado });
      }),
    );
    return cambios;
  }

  const LICENCIA = {
    ...base,
    id: 21,
    tipo: "licencia_en_control",
    caso_id: 16625886,
    caso_tipo: "salutem_atencion",
  };

  it("muestra el paciente y ofrece registrar la licencia con lo leído de SALUTEM", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    conAtencion(LICENCIA, [
      SUGERIDA,
      { ...SUGERIDA, cita_id: 999, ficha_clinica_id: 1 },
    ]);
    renderPanel();
    await userEvent.click(
      await screen.findByText("Licencia emitida en atención médica"),
    );
    const dialogo = await screen.findByRole("dialog");

    expect(
      await within(dialogo).findByText("Humberto Escobar"),
    ).toBeInTheDocument();
    // Solo la licencia de esta atención, no la de otra cita del mismo folio.
    const botones = await within(dialogo).findAllByRole("button", {
      name: /Registrar licencia/,
    });
    expect(botones).toHaveLength(1);
    expect(botones[0]).toHaveTextContent("Registrar licencia (15 días)");

    await userEvent.click(botones[0]);
    expect(
      await screen.findByText("Nueva licencia médica"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Datos sugeridos desde SALUTEM/),
    ).toBeInTheDocument();
    // GAF e indicación de reposo vienen precargados desde la atención.
    await vi.waitFor(() =>
      expect(screen.getByLabelText(/Tramo de GAF/)).toHaveValue("51-60"),
    );
    expect(screen.getByLabelText(/Indicación de reposo/)).toHaveValue(
      "Reposo por 15 días desde el 15/10/2026",
    );
  });

  it("si la licencia ya está registrada lo dice y no ofrece registrarla", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    conAtencion(LICENCIA, [{ ...SUGERIDA, ya_registrada: true }]);
    renderPanel();
    await userEvent.click(
      await screen.findByText("Licencia emitida en atención médica"),
    );
    const dialogo = await screen.findByRole("dialog");

    expect(
      await within(dialogo).findByText(/ya está registrada/),
    ).toBeInTheDocument();
    expect(
      within(dialogo).queryByRole("button", { name: /Registrar licencia/ }),
    ).not.toBeInTheDocument();
  });

  it("se puede marcar como resuelta desde el diálogo", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    const cambios = conAtencion(LICENCIA, [SUGERIDA]);
    renderPanel();
    await userEvent.click(
      await screen.findByText("Licencia emitida en atención médica"),
    );
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(
      within(dialogo).getByRole("button", { name: "Marcar como resuelta" }),
    );

    await vi.waitFor(() =>
      expect(cambios).toEqual([{ id: "21", estado: "resuelta" }]),
    );
  });

  it("el Auditor ve el paciente pero no puede registrar ni resolver", async () => {
    tokenStore.setAccess(TOKENS.Auditor);
    conAtencion(LICENCIA, [SUGERIDA]);
    renderPanel();
    await userEvent.click(
      await screen.findByText("Licencia emitida en atención médica"),
    );
    const dialogo = await screen.findByRole("dialog");

    expect(
      await within(dialogo).findByText("Humberto Escobar"),
    ).toBeInTheDocument();
    expect(
      within(dialogo).queryByRole("button", { name: /Registrar licencia/ }),
    ).not.toBeInTheDocument();
    expect(
      within(dialogo).queryByRole("button", { name: "Marcar como resuelta" }),
    ).not.toBeInTheDocument();
  });

  it("la alerta de receta lleva a Fármacos con el paciente seleccionado", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    conAtencion({ ...LICENCIA, id: 22, tipo: "receta_en_control" }, []);
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route path="/" element={<AlertsPanel />} />
              <Route path="/farmacos" element={<p>página de fármacos</p>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(
      await screen.findByText("Receta emitida en atención médica"),
    );
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(
      await within(dialogo).findByRole("button", {
        name: /Gestionar en Fármacos/,
      }),
    );

    expect(await screen.findByText("página de fármacos")).toBeInTheDocument();
  });
});
