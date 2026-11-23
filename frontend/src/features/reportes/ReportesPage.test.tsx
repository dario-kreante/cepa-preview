import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ReportesPage } from "./ReportesPage";
import { ODA_VENCIDA, odasVencidasResp } from "./testData";

const BASE = import.meta.env.VITE_API_BASE_URL;

// JWT sin firma válida: el frontend solo decodifica el payload (rol Coordinacion / Auditor).
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage(ruta = "/reportes", token = WRITER_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
        <AuthProvider>
          <Toaster />
          <ReportesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportesPage — pestaña Adherencia", () => {
  it("explica el criterio del denominador bajo el KPI", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/adherencia/:folio_id`, () =>
        HttpResponse.json({
          folio_id: 1,
          citas_agendadas: 3,
          citas_realizadas: 2,
          pct_adherencia: 66.67,
          sesiones_realizadas: 2,
          sesiones_plan: null,
          aumentos_isl: 0,
          pct_avance: null,
        }),
      ),
    );
    renderPage();
    fireEvent.click(screen.getByText("Adherencia", { selector: "button *, button" }));
    fireEvent.change(screen.getByTestId("input-folio-adherencia"), { target: { value: "1" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByTestId("kpi-adherencia")).toBeTruthy();
    expect(screen.getByTestId("ayuda-adherencia").textContent).toBe(
      "Atendidas sobre el total de citas atendidas más inasistencias. Las anuladas y las futuras no cuentan.",
    );
  });
});

describe("ReportesPage — pestaña desde la URL", () => {
  it("?tab=odas abre la pestaña de ODAS vencidas", () => {
    renderPage("/reportes?tab=odas");
    expect(screen.getByTestId("vista-vencidas").getAttribute("aria-pressed")).toBe("true");
  });
});

describe("ReportesPage — ODAS vencidas (QA-007)", () => {
  it("muestra paciente, RUT y N° ISL en vez de ids internos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json({
          fecha_consulta: "2026-11-17",
          total: 1,
          items: [
            {
              id: 21,
              folio_id: 14,
              identificador: "395331",
              folio: "F-2026-0057",
              paciente_nombre: "Paciente Prueba Francisca Valladares",
              paciente_rut: "11.111.111-1",
              fecha_registro: "2026-10-14",
              fecha_vencimiento: "2026-11-03",
              programa: "DIEP",
              region: "Maule",
              comuna: null,
            },
          ],
        }),
      ),
    );
    renderPage("/reportes?tab=odas");
    expect(await screen.findByText("Paciente Prueba Francisca Valladares")).toBeTruthy();
    expect(screen.getByText("395331")).toBeTruthy();
    expect(screen.getByText("11.111.111-1")).toBeTruthy();
    expect(screen.queryByText("21")).toBeNull();
  });
});

// ── Carga del Reporte Prestador del ISL (QA-004) ─────────────────────────────

const RESUMEN = {
  archivo: "reporte.xlsx",
  filas_leidas: 4,
  creadas: 1,
  actualizadas: 1,
  sin_cambios: 0,
  match_por_siniestro: 2,
  match_por_rut: 0,
  match_por_id_salutem: 0,
  sin_paciente: [
    { fila: 4, numero_orden: "900002", tipo_orden: "Ambulatoria", numero_siniestro: "1000002", rut_trabajador: null },
  ],
  errores: [{ fila: 5, motivo: "Orden 3: fecha inválida «x»." }],
  ventana_dias: 7,
  por_vencer_paciente_activo: 1,
  por_vencer: [
    { oda_id: 1, ingreso_id: 1, folio: "F-1", numero_orden: "900001", fecha_vencimiento: "2026-11-02" },
  ],
};

describe("ReportesPage — Cargar reporte ISL", () => {
  beforeEach(() => {
    // ?tab=odas carga solo el informe de vencidas: se responde vacío.
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () => HttpResponse.json(odasVencidasResp([]))),
    );
  });

  it("el Auditor no ve el botón de carga", () => {
    renderPage("/reportes?tab=odas", AUDITOR_TOKEN);
    expect(screen.queryByTestId("btn-cargar-reporte-isl")).toBeNull();
  });

  it("previsualiza en dry run, confirma y muestra el resumen", async () => {
    const llamadas: string[] = [];
    server.use(
      http.post(`${BASE}/api/v1/odas/importar`, async ({ request }) => {
        const dry = new URL(request.url).searchParams.get("dry_run");
        llamadas.push(dry ?? "");
        return HttpResponse.json({ ...RESUMEN, dry_run: dry === "true" });
      }),
    );
    renderPage("/reportes?tab=odas");
    fireEvent.click(screen.getByTestId("btn-cargar-reporte-isl"));

    const boton = await screen.findByTestId("btn-previsualizar-isl");
    expect((boton as HTMLButtonElement).disabled).toBe(true);
    const archivo = new File(["x"], "reporte.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    fireEvent.change(screen.getByTestId("input-archivo-isl"), { target: { files: [archivo] } });
    fireEvent.click(boton);

    expect((await screen.findByTestId("estado-importacion")).textContent).toMatch(/Previsualización/);
    expect(screen.getByTestId("dato-creadas").textContent).toBe("1");
    expect(screen.getByTestId("dato-sin-paciente").textContent).toBe("1");
    expect(screen.getByText(/siniestro 1000002/)).toBeTruthy();
    expect(screen.getByText(/Fila 5: Orden 3/)).toBeTruthy();
    expect(screen.getByTestId("por-vencer").textContent).toMatch(/1 ODA\(S\).*7 días/);

    fireEvent.click(screen.getByTestId("btn-confirmar-isl"));
    await waitFor(() =>
      expect(screen.getByTestId("estado-importacion").textContent).toBe("Carga completada."),
    );
    expect(llamadas).toEqual(["true", "false"]);
    expect(screen.getByTestId("btn-cerrar-isl")).toBeTruthy();
  });

  it("muestra el error del backend si el archivo no sirve", async () => {
    server.use(
      http.post(`${BASE}/api/v1/odas/importar`, () =>
        HttpResponse.json({ detail: "Faltan columnas en el archivo: N° Siniestro." }, { status: 422 }),
      ),
    );
    renderPage("/reportes?tab=odas");
    fireEvent.click(screen.getByTestId("btn-cargar-reporte-isl"));
    fireEvent.change(await screen.findByTestId("input-archivo-isl"), {
      target: { files: [new File(["x"], "malo.xlsx")] },
    });
    fireEvent.click(screen.getByTestId("btn-previsualizar-isl"));
    expect(await screen.findByText("Faltan columnas en el archivo: N° Siniestro.")).toBeTruthy();
    expect(screen.queryByTestId("resumen-importacion")).toBeNull();
  });
});


// ── QA-006: listado por paciente ──────────────────────────────────────────────

const ESTADO_RESP = {
  fecha_consulta: "2026-11-18",
  total: 3,
  dias_por_vencer: 15,
  items: [
    { ingreso_id: 1, folio: "F-1", paciente_nombre: "Ana Activa", paciente_rut: "1-9", fecha_ingreso: "2026-03-02", estado_caso: "activo", programa: "PIPT", estado_oda: "por_vencer", fecha_vencimiento: "2026-11-27", dias_para_vencer: 9 },
    { ingreso_id: 2, folio: "F-2", paciente_nombre: "Camilo Cerrado", paciente_rut: "2-7", fecha_ingreso: "2026-01-10", estado_caso: "cerrado", programa: null, estado_oda: "vigente", fecha_vencimiento: "2026-12-30", dias_para_vencer: 42 },
    { ingreso_id: 3, folio: "F-3", paciente_nombre: "Elena Encuadre", paciente_rut: null, fecha_ingreso: "2026-02-01", estado_caso: "encuadre", programa: null, estado_oda: "sin_oda", fecha_vencimiento: null, dias_para_vencer: null },
  ],
};

describe("ReportesPage — ODA por paciente (QA-006)", () => {
  it("Consultar lista paciente, fecha de ingreso, estado del caso y estado de la ODA", async () => {
    server.use(http.get(`${BASE}/api/v1/reportes/odas-estado`, () => HttpResponse.json(ESTADO_RESP)));
    renderPage("/reportes");
    fireEvent.click(screen.getByTestId("tab-odas"));
    expect(screen.getByTestId("vista-estado").getAttribute("aria-pressed")).toBe("true");
    expect(screen.queryByText("Ana Activa")).toBeNull(); // no carga sola fuera del enlace del dashboard
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByText("Ana Activa")).toBeTruthy();
    const fila = (n: string) => screen.getByText(n).closest("tr")!.textContent!;
    expect(fila("Ana Activa")).toMatch(/02\/03\/2026/);
    expect(fila("Ana Activa")).toMatch(/Activo/);
    expect(fila("Ana Activa")).toMatch(/Por vencer/);
    expect(fila("Ana Activa")).toMatch(/en 9 días/);
    expect(fila("Camilo Cerrado")).toMatch(/Cerrado/);
    expect(fila("Camilo Cerrado")).toMatch(/Vigente/);
    expect(fila("Elena Encuadre")).toMatch(/Encuadre/);
    expect(fila("Elena Encuadre")).toMatch(/Sin ODA/);
  });

  it("envía el filtro de estado del caso", async () => {
    let query = "";
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-estado`, ({ request }) => {
        query = new URL(request.url).search;
        return HttpResponse.json(ESTADO_RESP);
      }),
    );
    renderPage("/reportes");
    fireEvent.click(screen.getByTestId("tab-odas"));
    fireEvent.change(screen.getByTestId("filtro-estado-caso"), { target: { value: "cerrado" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    await screen.findByText("Ana Activa");
    expect(query).toBe("?estado_caso=cerrado");
  });
});

// ── QA-007: pantalla de ODA vencidas ──────────────────────────────────────────

describe("ReportesPage — ODA vencidas: carga, columnas, gestión, filtro y Excel (QA-007)", () => {
  it("con StrictMode (como en main.tsx) la carga automática termina y consulta una sola vez", async () => {
    let consultas = 0;
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () => {
        consultas += 1;
        return HttpResponse.json(odasVencidasResp([ODA_VENCIDA]));
      }),
    );
    tokenStore.setAccess(WRITER_TOKEN);
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    render(
      <StrictMode>
        <QueryClientProvider client={qc}>
          <MemoryRouter initialEntries={["/reportes?tab=odas"]}>
            <AuthProvider>
              <ReportesPage />
            </AuthProvider>
          </MemoryRouter>
        </QueryClientProvider>
      </StrictMode>,
    );
    expect(await screen.findByText("Paciente Prueba")).toBeTruthy();
    expect(screen.queryByText("Consultando…")).toBeNull();
    expect(consultas).toBe(1);
  });

  it("al llegar por el enlace del dashboard (?tab=odas) carga sola, sin apretar Consultar", async () => {
    let llamadas = 0;
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () => {
        llamadas++;
        return HttpResponse.json(odasVencidasResp([ODA_VENCIDA]));
      }),
    );
    renderPage("/reportes?tab=odas");
    expect(await screen.findByText("Paciente Prueba")).toBeTruthy();
    expect(llamadas).toBe(1);
  });

  it("muestra nombre, RUT, N° ODA/OPA, tipo, inicio, término, atenciones y cobertura; varias órdenes con « / »", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json(
          odasVencidasResp([
            {
              ...ODA_VENCIDA,
              ordenes: [
                { identificador: "111", tipo: "ODA", fecha_inicio: "2026-09-01", fecha_termino: "2026-09-30" },
                { identificador: "222", tipo: null, fecha_inicio: null, fecha_termino: "2026-10-20" },
              ],
              fechas_atencion: ["2026-09-10", "2026-10-25"],
              cobertura: "SOLICITAR",
            },
          ]),
        ),
      ),
    );
    renderPage("/reportes?tab=odas");
    const fila = (await screen.findByText("Paciente Prueba")).closest("tr")!;
    const celdas = Array.from(fila.querySelectorAll("td")).map((c) => c.textContent);
    expect(celdas.slice(0, 8)).toEqual([
      "Paciente Prueba",
      "11.111.111-1",
      "111 / 222",
      "ODA / —",
      "01/09/2026 / —",
      "30/09/2026 / 20/10/2026",
      "10/09/2026 / 25/10/2026",
      "SOLICITAR",
    ]);
  });

  it("un atendido sin ODA muestra SOLICITAR, «—» en los campos de la orden y sin selector de gestión", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json(
          odasVencidasResp([
            ODA_VENCIDA,
            {
              id: null,
              folio_id: 30,
              identificador: null,
              folio: "F-2026-0099",
              paciente_nombre: "Atendida Sin Orden",
              paciente_rut: "22.222.222-2",
              fecha_registro: null,
              fecha_vencimiento: null,
              programa: "Programa Regular",
              region: "Maule",
              comuna: null,
              ordenes: [],
              fechas_atencion: ["2026-11-02", "2026-11-09"],
              cobertura: "SOLICITAR",
              estado_gestion: null,
            },
          ]),
        ),
      ),
    );
    renderPage("/reportes?tab=odas");
    const fila = (await screen.findByText("Atendida Sin Orden")).closest("tr")!;
    const celdas = Array.from(fila.querySelectorAll("td")).map((c) => c.textContent);
    expect(celdas).toEqual([
      "Atendida Sin Orden",
      "22.222.222-2",
      "—",
      "—",
      "—",
      "—",
      "02/11/2026 / 09/11/2026",
      "SOLICITAR",
      "—",
    ]);
    expect(fila.querySelector("select")).toBeNull();
    // La fila con ODA sigue ofreciendo el selector.
    expect(screen.getByTestId("gestion-21")).toBeTruthy();
  });

  it("aclara que el informe también incluye atendidos sin ODA", async () => {
    renderPage("/reportes?tab=odas");
    expect(screen.getByText(/atendidos sin ODA/i)).toBeTruthy();
  });

  it("el escritor cambia la gestión desde la tabla y se guarda en el backend", async () => {
    let cuerpo: unknown = null;
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json(odasVencidasResp([ODA_VENCIDA])),
      ),
      http.patch(`${BASE}/api/v1/odas/:id/gestion`, async ({ request, params }) => {
        cuerpo = { id: params.id, ...((await request.json()) as object) };
        return HttpResponse.json({ id: Number(params.id), estado_gestion: "solicitada" });
      }),
    );
    renderPage("/reportes?tab=odas");
    const select = (await screen.findByTestId("gestion-21")) as HTMLSelectElement;
    expect(select.value).toBe("pendiente");
    fireEvent.change(select, { target: { value: "solicitada" } });
    await waitFor(() => expect(cuerpo).toEqual({ id: "21", estado_gestion: "solicitada" }));
    await waitFor(() => expect((screen.getByTestId("gestion-21") as HTMLSelectElement).value).toBe("solicitada"));
  });

  it("el Auditor ve la gestión pero no puede editarla", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json(odasVencidasResp([{ ...ODA_VENCIDA, estado_gestion: "recibida" }])),
      ),
    );
    renderPage("/reportes?tab=odas", AUDITOR_TOKEN);
    expect((await screen.findByTestId("gestion-21")).tagName).not.toBe("SELECT");
    expect(screen.getByTestId("gestion-21").textContent).toBe("Recibida");
  });

  it("filtra por programa", async () => {
    const consultas: string[] = [];
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, ({ request }) => {
        consultas.push(new URL(request.url).search);
        return HttpResponse.json(odasVencidasResp([ODA_VENCIDA]));
      }),
    );
    renderPage("/reportes?tab=odas");
    await screen.findByText("Paciente Prueba");
    const opciones = Array.from(
      (screen.getByTestId("filtro-programa") as HTMLSelectElement).options,
    ).map((o) => o.textContent);
    expect(opciones).toEqual(["Todos", "Regular", "Ley Karin", "PIPT"]);
    fireEvent.change(screen.getByTestId("filtro-programa"), { target: { value: "ley_karin" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    await waitFor(() => expect(consultas).toEqual(["", "?programa=ley_karin"]));
  });

  it("descarga la tabla en Excel con el filtro vigente", async () => {
    let pedido = "";
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json(odasVencidasResp([ODA_VENCIDA])),
      ),
      http.get(`${BASE}/api/v1/reportes/odas-vencidas/excel`, ({ request }) => {
        pedido = new URL(request.url).search;
        return new HttpResponse(new Uint8Array([80, 75, 3, 4]), {
          headers: {
            "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          },
        });
      }),
    );
    const crear = vi.fn(() => "blob:x");
    (URL as unknown as { createObjectURL: unknown }).createObjectURL = crear;
    (URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = vi.fn();
    const clic = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    renderPage("/reportes?tab=odas");
    await screen.findByText("Paciente Prueba");
    fireEvent.change(screen.getByTestId("filtro-programa"), { target: { value: "pipt" } });
    fireEvent.click(screen.getByTestId("btn-excel-odas"));
    await waitFor(() => expect(clic).toHaveBeenCalled());
    expect(pedido).toBe("?programa=pipt");
    expect(crear).toHaveBeenCalled();
    clic.mockRestore();
  });
});

// ── Licencias: folio real ─────────────────────────────────────────────────────

describe("ReportesPage — Licencias muestra el folio real", () => {
  it("la columna Folio usa el folio y no el id interno", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/licencias`, () =>
        HttpResponse.json({
          periodo_desde: "2026-01-01",
          periodo_hasta: "2026-12-31",
          items: [
            { folio_id: 4242, folio: "F-2026-0007", rut_paciente: "3-5", total_dias_acumulados: 12, licencias_internas: 1, licencias_externas: 0 },
          ],
        }),
      ),
    );
    renderPage("/reportes");
    fireEvent.click(screen.getByTestId("tab-licencias"));
    fireEvent.change(document.getElementById("r-desde")!, { target: { value: "2026-01-01" } });
    fireEvent.change(document.getElementById("r-hasta")!, { target: { value: "2026-12-31" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByText("F-2026-0007")).toBeTruthy();
    expect(screen.queryByText("4242")).toBeNull();
  });
});

describe("ReportesPage — pestaña Convenio elige del catálogo", () => {
  function conConvenios() {
    server.use(
      http.get(`${BASE}/api/v1/convenios/para-reportes`, () =>
        HttpResponse.json(["Convenio SSM", "ISL"]),
      ),
    );
  }

  function abrirConvenio() {
    renderPage("/reportes");
    fireEvent.click(screen.getByTestId("tab-convenio"));
    fireEvent.change(document.getElementById("r-desde")!, { target: { value: "2026-01-01" } });
    fireEvent.change(document.getElementById("r-hasta")!, { target: { value: "2026-12-31" } });
  }

  it("la pestaña Convenio ofrece los convenios del catálogo y los valores antiguos", async () => {
    conConvenios();
    abrirConvenio();
    expect(await screen.findByRole("option", { name: "Convenio SSM" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "ISL" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Elige un convenio" })).toBeTruthy();
  });

  it("generar sin elegir convenio muestra «Indica el tipo de convenio.»", async () => {
    conConvenios();
    abrirConvenio();
    await screen.findByRole("option", { name: "ISL" });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    expect(await screen.findByText("Indica el tipo de convenio.")).toBeTruthy();
  });

  it("genera con el convenio elegido", async () => {
    conConvenios();
    let recibido: string | null = null;
    server.use(
      http.get(`${BASE}/api/v1/reportes/convenio`, ({ request }) => {
        recibido = new URL(request.url).searchParams.get("tipo_convenio");
        return HttpResponse.json({
          periodo_desde: "2026-01-01",
          periodo_hasta: "2026-12-31",
          items: [],
        });
      }),
    );
    abrirConvenio();
    await screen.findByRole("option", { name: "Convenio SSM" });
    fireEvent.change(document.getElementById("convenio")!, { target: { value: "Convenio SSM" } });
    fireEvent.click(screen.getByTestId("btn-generar-reporte"));
    await waitFor(() => expect(recibido).toBe("Convenio SSM"));
  });
});
