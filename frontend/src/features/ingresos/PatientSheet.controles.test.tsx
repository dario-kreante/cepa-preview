/**
 * Pestaña Controles de la ficha (QA-008): etiqueta «Con addendum», notas de SALUTEM y
 * observaciones completas.
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

const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const PACIENTE = {
  id: 7, rut: "11.222.333-4", nombre: "Carmen Soto", sexo: "F", edad: 42,
  region: "Maule", comuna: "Talca", telefono: null, correo: null,
};

const INGRESO = {
  id: 55, paciente_id: 7, folio: "F-2026-0055", folio_manual: false, numero_siniestro: null,
  fecha_ingreso: "2026-01-15", fecha_diep_diat: null, tipo_derivacion: "DIEP",
  tipo_ingreso: "convenio", modelo_tratamiento: "ambulatorio", diagnostico: "Ansiedad",
  razon_social: null, estado: "activo", tipo_alta: null, fecha_alta: null,
  flag_revision: false, observaciones: null, tratamiento_iniciado: true,
};

const OBS_LARGA = "Addendum fecha 04-11-2026, cambio número de días de 4 a 5";

const BASE_CONTROL = {
  ingreso_id: 55, semana_control: 3, region_derivacion: "Maule", proximo_control: null,
  proximo_agendado: false, tiene_licencia: false, resumen_termino_lm: null, total_dias_lm: null,
  tipo_licencia: null, tipo_reposo: null, gaf: null, estado_reca: null, origen: "SALUTEM",
  campos_editados: [], fuera_de_oda: false,
};

const CONTROLES = [
  {
    ...BASE_CONTROL,
    id: 1,
    fecha_control: "2026-10-27",
    medico_tratante: "DRA. PAULA ROJAS",
    observaciones: null,
    tiene_addendum: true,
    notas_salutem: [
      { fecha: "2026-10-28T08:00:00", profesional: "ANA PÉREZ", texto: "Paciente llega tarde", es_addendum: false },
      {
        fecha: "2026-11-23T12:07:28",
        profesional: "PILAR GARCÍA",
        texto: "Prueba addendum. Se corrige próximo control 45 días.",
        es_addendum: true,
      },
    ],
  },
  {
    ...BASE_CONTROL,
    id: 2,
    fecha_control: "2026-10-26",
    medico_tratante: "DR. PEDRO SOTO",
    observaciones: OBS_LARGA,
    tiene_addendum: false,
    notas_salutem: [
      { fecha: "2026-10-26T10:00:00", profesional: null, texto: "Se llamó al empleador", es_addendum: false },
    ],
  },
];

function renderSheet() {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente: PACIENTE, ingresos: [INGRESO], farmacos: [], licencias: [], controles: [],
        odas: [], reintegro: [],
      })
    ),
    http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`, () =>
      HttpResponse.json(CONTROLES)
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`, () =>
      HttpResponse.json([])
    ),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio`, () => HttpResponse.json([])),
  );
  tokenStore.setAccess(FAKE_TOKEN);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <PatientSheet pacienteId={7} open onOpenChange={() => {}} tabInicial="controles" />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("PatientSheet — pestaña Controles (QA-008)", () => {
  it("etiqueta «Con addendum» solo el control que tiene un addendum", async () => {
    renderSheet();
    expect(await screen.findByTestId("badge-addendum-1", {}, { timeout: 8000 })).toHaveTextContent(
      "Con addendum"
    );
    expect(screen.queryByTestId("badge-addendum-2")).not.toBeInTheDocument();
  });

  it("al ver el detalle muestra el addendum completo con fecha y profesional, y las demás notas aparte", async () => {
    renderSheet();
    await userEvent.click(await screen.findByTestId("btn-detalle-control-1", {}, { timeout: 8000 }));

    const notas = screen.getByTestId("notas-salutem-1");
    expect(within(notas).getByText("Addendum")).toBeInTheDocument();
    expect(
      within(notas).getByText("Prueba addendum. Se corrige próximo control 45 días.")
    ).toBeInTheDocument();
    expect(within(notas).getByText("23/11/2026 12:07 · PILAR GARCÍA")).toBeInTheDocument();
    expect(within(notas).getByText("Notas de SALUTEM")).toBeInTheDocument();
    expect(within(notas).getByText("Paciente llega tarde")).toBeInTheDocument();
  });

  it("las observaciones largas se pueden leer completas", async () => {
    renderSheet();
    const corta = await screen.findByTitle(OBS_LARGA, {}, { timeout: 8000 });
    expect(corta).toHaveTextContent(OBS_LARGA);

    await userEvent.click(screen.getByTestId("btn-detalle-control-2"));
    const detalle = screen.getByTestId("detalle-control-2");
    expect(within(detalle).getByText(OBS_LARGA)).toBeInTheDocument();
    expect(within(detalle).getByText("Notas de SALUTEM")).toBeInTheDocument();
    expect(within(detalle).queryByText("Addendum")).not.toBeInTheDocument();
  });
});
