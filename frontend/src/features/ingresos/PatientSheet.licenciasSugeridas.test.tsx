/**
 * Licencias detectadas en las atenciones de SALUTEM, para revisión humana.
 *
 * El backend sugiere; el administrativo revisa y registra con el alta de licencia
 * de siempre, que llega precargada con lo que se pudo leer de la indicación.
 */
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { PatientSheet } from "./PatientSheet";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Rol Coordinacion (el token solo se decodifica, no se verifica)
const TOKEN_COORDINACION =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const FOLIO = "F-2026-0061";

const SUGERENCIA_PENDIENTE = {
  ficha_clinica_id: 10,
  cita_fecha: "2024-05-06",
  texto: "Extiendo licencia médica tipo 6 total desde el 09/05/2024 por 21 días",
  tipo_lm: "6",
  tipo_reposo: "total",
  origen: "sistema",
  fecha_inicio: "2024-05-09",
  fecha_termino: "2024-05-29",
  termino_calculado: true,
  cantidad_dias: 21,
  avisos: [],
  ya_registrada: false,
};

const SUGERENCIA_CON_AVISO_REGISTRADA = {
  ficha_clinica_id: 11,
  cita_fecha: "2025-01-20",
  texto: "Paciente con licencia médica extra sistema vigente hasta el 31/01/2024",
  tipo_lm: null,
  tipo_reposo: null,
  origen: "extra_sistema",
  fecha_inicio: null,
  fecha_termino: "2024-01-31",
  termino_calculado: false,
  cantidad_dias: null,
  avisos: [
    "La fecha de término (31/01/2024) es anterior a la atención (20/01/2025): posible error de tipeo en el año.",
  ],
  ya_registrada: true,
};

function setupMocks(sugerencias: unknown[]) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente: {
          id: 7, rut: "16.215.806-6", nombre: "Paciente Prueba", sexo: "F", edad: 42,
          region: "Maule", comuna: "Talca", telefono: null, correo: null,
        },
        ingresos: [{
          id: 81, paciente_id: 7, folio: FOLIO, folio_manual: false, numero_siniestro: null,
          fecha_ingreso: "2024-03-01", fecha_diep_diat: null, tipo_derivacion: "DIEP",
          tipo_ingreso: "convenio", modelo_tratamiento: "ambulatorio", diagnostico: "Ansiedad",
          razon_social: null, estado: "activo", tipo_alta: null, fecha_alta: null,
          flag_revision: false, observaciones: null, tratamiento_iniciado: true,
        }],
        farmacos: [], licencias: [], controles: [], reintegro: [],
      }),
    ),
    http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio/licencias-sugeridas`, () =>
      HttpResponse.json(sugerencias),
    ),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio`, () => HttpResponse.json([])),
  );
}

function renderSheet() {
  tokenStore.setAccess(TOKEN_COORDINACION);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
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

async function abrirPestanaSalutem() {
  await screen.findByText("Paciente Prueba");
  await userEvent.click(await screen.findByRole("tab", { name: /SALUTEM/i }));
}

describe("PatientSheet — licencias detectadas en SALUTEM", () => {
  it("lista las licencias detectadas con sus fechas, avisos y si ya están registradas", async () => {
    setupMocks([SUGERENCIA_PENDIENTE, SUGERENCIA_CON_AVISO_REGISTRADA]);
    renderSheet();
    await abrirPestanaSalutem();

    const seccion = await screen.findByRole("region", { name: /licencias detectadas/i });
    const items = within(seccion).getAllByRole("listitem");
    expect(items).toHaveLength(2);

    const pendiente = within(items[0]);
    // anclado al inicio: la indicación citada también dice "tipo 6" y "21 días"
    expect(pendiente.getByText(/^tipo 6/i)).toBeInTheDocument();
    expect(pendiente.getByText(/09\/05\/2024 al 29\/05\/2024/)).toBeInTheDocument();
    expect(pendiente.getByText("21 días")).toBeInTheDocument();
    expect(pendiente.getByRole("button", { name: /revisar y registrar/i })).toBeInTheDocument();

    const registrada = within(items[1]);
    expect(registrada.getByText(/ya registrada/i)).toBeInTheDocument();
    expect(registrada.getByText(/posible error de tipeo/i)).toBeInTheDocument();
    expect(registrada.queryByRole("button", { name: /revisar y registrar/i })).not.toBeInTheDocument();
  });

  it("'Revisar y registrar' abre el alta de licencia precargada con la sugerencia", async () => {
    setupMocks([SUGERENCIA_PENDIENTE]);
    renderSheet();
    await abrirPestanaSalutem();

    await userEvent.click(await screen.findByRole("button", { name: /revisar y registrar/i }));

    const dialogo = within(await screen.findByRole("dialog", { name: /nueva licencia médica/i }));
    expect(dialogo.getByText(/datos sugeridos desde salutem/i)).toBeInTheDocument();
    expect(dialogo.getByLabelText(/tipo de licencia/i)).toHaveValue("6");
    expect(dialogo.getByLabelText(/tipo de reposo/i)).toHaveValue("total");
    expect(dialogo.getByLabelText(/fecha inicio de la licencia/i)).toHaveValue("2024-05-09");
    expect(dialogo.getByLabelText(/fecha término de la licencia/i)).toHaveValue("2024-05-29");
    expect(dialogo.getByLabelText(/inicio del reposo/i)).toHaveValue("2024-05-09");
    expect(dialogo.getByLabelText(/fin del reposo/i)).toHaveValue("2024-05-29");
    expect(dialogo.getByLabelText(/cantidad de días/i)).toHaveValue(21);
    // lo que la indicación no dice queda para que lo complete el administrativo
    expect(dialogo.getByLabelText(/^diagnóstico$/i)).toHaveValue("");
  });

  it("al registrar la licencia sugerida, el contador de la pestaña Licencias se actualiza", async () => {
    setupMocks([SUGERENCIA_PENDIENTE]);
    const licencias: unknown[] = [];
    server.use(
      http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () => HttpResponse.json(licencias)),
      http.post(`${BASE}/api/v1/licencias`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        const creada = { id: 500, anulada: false, envio_isl: "pendiente", ...body };
        licencias.push(creada);
        return HttpResponse.json(creada, { status: 201 });
      }),
    );
    renderSheet();
    await abrirPestanaSalutem();
    expect(screen.getByRole("tab", { name: /licencias \(0\)/i })).toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: /revisar y registrar/i }));
    const dialogo = within(await screen.findByRole("dialog", { name: /nueva licencia médica/i }));
    await userEvent.type(dialogo.getByLabelText(/^diagnóstico$/i), "Trastorno adaptativo");
    await userEvent.type(dialogo.getByLabelText(/fecha de emisión de la licencia/i), "2024-05-06");
    await userEvent.click(dialogo.getByRole("button", { name: /registrar licencia/i }));

    expect(await screen.findByRole("tab", { name: /licencias \(1\)/i })).toBeInTheDocument();
  });

  it("sin licencias detectadas no muestra la sección", async () => {
    setupMocks([]);
    renderSheet();
    await abrirPestanaSalutem();

    await screen.findByText(/aún no hay atenciones importadas/i);
    expect(screen.queryByRole("region", { name: /licencias detectadas/i })).not.toBeInTheDocument();
  });
});
