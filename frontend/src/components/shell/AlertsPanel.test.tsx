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
    expect(tituloAlerta("licencia_en_control")).toBe("Licencia emitida en control");
    expect(tituloAlerta("receta_en_control")).toBe("Receta emitida en control");
  });

  it("nombra la alerta de paciente nuevo pendiente de folio", () => {
    expect(tituloAlerta("paciente_pendiente_folio")).toBe("Paciente nuevo pendiente de folio");
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
          origen: "SALUTEM",
        }),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([
          { archivo_id: 1, nombre: "LICENCIA.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" },
        ]),
      ),
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <AlertsPanel />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByText("Licencia emitida en control"));
    const dialogo = await screen.findByRole("dialog");
    expect(await within(dialogo).findByText(/DRA\. PAULA ROJAS/)).toBeInTheDocument();
    expect(within(dialogo).getByText(/LM tipo 6 por 30 días/)).toBeInTheDocument();
    expect(await within(dialogo).findByText("LICENCIA.pdf")).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: /ir a controles/i })).toBeInTheDocument();
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
      http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json([alertaLicencia()])),
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
      http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json([alertaLicencia()])),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/v1/controles-medicos/5`, () =>
        HttpResponse.json({ detail: "Control no encontrado" }, { status: 404 }),
      ),
    );
    renderPanel();
    await userEvent.click(await screen.findByText("Licencia emitida en control"));
    const dialogo = await screen.findByRole("dialog");
    expect(
      await within(dialogo).findByText("No se encontró el control (pudo ser anulado en SALUTEM)."),
    ).toBeInTheDocument();
    expect(within(dialogo).queryByText(/cargando control/i)).not.toBeInTheDocument();
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

  it("tipo desconocido o nulo cae a /ingresos", () => {
    expect(routeForCaso("otro", 1)).toBe("/ingresos");
    expect(routeForCaso(null, null)).toBe("/ingresos");
  });
});

describe("AlertsPanel: leída al verla y resolver", () => {
  // jsdom no implementa IntersectionObserver: un doble que el test controla.
  type Callback = (entradas: Array<{ isIntersecting: boolean; target: Element }>) => void;
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
        o.cb(o.elementos.map((target) => ({ isIntersecting: visible, target })));
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
        return HttpResponse.json({ ...alertaLicencia(), id: Number(params.id), estado: body.estado });
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
    expect(screen.queryByRole("button", { name: /marcar como leída/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /resolver/i })).toBeInTheDocument();
  });

  it("una alerta pendiente queda leída tras verse 1,5 s en pantalla", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    const cambios = conAlertas([alertaLicencia()]);
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    mostrarTodo(true);
    await esperarVisible(1600);
    await vi.waitFor(() => expect(cambios).toEqual([{ id: "1", estado: "leida" }]));
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
    await vi.waitFor(() => expect(cambios).toEqual([{ id: "2", estado: "leida" }]));
  });

  it("una alerta leída se puede resolver", async () => {
    tokenStore.setAccess(TOKENS.Administrativo);
    const cambios = conAlertas([{ ...alertaLicencia(), estado: "leida" }]);
    renderPanel();
    await userEvent.click(await screen.findByRole("button", { name: /resolver/i }));
    await vi.waitFor(() => expect(cambios).toEqual([{ id: "1", estado: "resuelta" }]));
  });

  it("el Auditor ve las alertas, sin botón y sin marcarlas como leídas", async () => {
    tokenStore.setAccess(TOKENS.Auditor);
    const cambios = conAlertas([alertaLicencia()]);
    renderPanel();
    await screen.findByText("Licencia emitida en control");
    expect(screen.queryByRole("button", { name: /resolver/i })).not.toBeInTheDocument();
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
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/"]}>
          <AuthProvider>
            <Routes>
              <Route path="/" element={<AlertsPanel />} />
              <Route path="/pendientes-folio" element={<p>pantalla pendientes</p>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await userEvent.click(await screen.findByText("Paciente nuevo pendiente de folio"));
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
      { ...base, id: 1, tipo: "oda_por_vencer", estado: "pendiente", usuario_id: null },
      { ...base, id: 2, tipo: "plazo_isl", estado: "leida", usuario_id: null },
      { ...base, id: 3, tipo: "plazo_ept", estado: "pendiente", usuario_id: 999 },
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
    conAlertas([{ ...base, id: 1, tipo: "oda_por_vencer", estado: "leida", usuario_id: null }]);
    const onClose = vi.fn();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
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
    await userEvent.click(screen.getByRole("button", { name: "Cerrar alertas" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
