/**
 * BUG-2608-01 — la ficha del paciente permite editar el ingreso (salvo RUT y folio).
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { PatientSheet } from "./PatientSheet";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Coordinacion role token (not server-verified, only decoded)
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const PACIENTE = {
  id: 7,
  rut: "112223334",
  nombre: "Carmen Soto",
  sexo: "F",
  edad: 42,
  region: "Valparaíso",
  comuna: "Viña del Mar",
  telefono: "+56912345678",
  correo: "csoto@example.com",
};

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
  diagnostico: "Trastorno de ansiedad generalizada",
  razon_social: null,
  estado: "activo",
  tipo_alta: null,
  fecha_alta: null,
  flag_revision: false,
  observaciones: null,
  tratamiento_iniciado: true,
};

function mocksBase() {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente: PACIENTE,
        ingresos: [INGRESO],
        farmacos: [],
        licencias: [],
        controles: [],
        reintegro: [],
      }),
    ),
    http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio`, () => HttpResponse.json([])),
  );
}

function renderSheet() {
  tokenStore.setAccess(FAKE_TOKEN);
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

async function abrirEdicion() {
  const user = userEvent.setup();
  renderSheet();
  const boton = await screen.findByRole("button", { name: /Editar ficha/i });
  expect(boton).toBeEnabled();
  await user.click(boton);
  const dialog = await screen.findByRole("dialog", { name: /Editar ficha/i });
  return { user, dialog: within(dialog) };
}

describe("PatientSheet — editar ficha (BUG-2608-01)", () => {
  it("abre el formulario con los datos actuales y RUT y folio de solo lectura", async () => {
    mocksBase();
    const { dialog } = await abrirEdicion();

    expect(dialog.getByLabelText(/Nombre/i)).toHaveValue("Carmen Soto");
    expect(dialog.getByLabelText(/Diagnóstico/i)).toHaveValue("Trastorno de ansiedad generalizada");
    expect(dialog.getByLabelText(/Fecha de ingreso/i)).toHaveValue("2026-01-15");
    // RUT y folio se muestran, pero no son campos editables
    expect(dialog.getByText("F-2026-0055")).toBeInTheDocument();
    expect(dialog.getByText(/11\.222\.333-4|112223334/)).toBeInTheDocument();
    expect(dialog.queryByLabelText(/^RUT$/i)).not.toBeInTheDocument();
    expect(dialog.queryByLabelText(/^Folio$/i)).not.toBeInTheDocument();
  });

  it("guarda con PUT al ingreso sin enviar RUT ni folio y cierra el formulario", async () => {
    mocksBase();
    const putSpy = vi.fn();
    server.use(
      http.put(`${BASE}/api/v1/ingresos/:ingreso_id`, async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>;
        putSpy(params.ingreso_id, body);
        return HttpResponse.json({ ...INGRESO, diagnostico: body.diagnostico });
      }),
    );
    const { user, dialog } = await abrirEdicion();

    const diagnostico = dialog.getByLabelText(/Diagnóstico/i);
    await user.clear(diagnostico);
    await user.type(diagnostico, "Trastorno adaptativo");
    await user.click(dialog.getByRole("button", { name: /Guardar cambios/i }));

    await waitFor(() => expect(putSpy).toHaveBeenCalledOnce());
    const [ingresoId, body] = putSpy.mock.calls[0];
    expect(ingresoId).toBe("55");
    expect(body.diagnostico).toBe("Trastorno adaptativo");
    expect(body.nombre).toBe("Carmen Soto");
    expect(body).not.toHaveProperty("rut");
    expect(body).not.toHaveProperty("folio");
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: /Editar ficha/i })).not.toBeInTheDocument(),
    );
  });

  it("si el guardado falla, lo dice y conserva lo escrito", async () => {
    mocksBase();
    server.use(
      http.put(`${BASE}/api/v1/ingresos/:ingreso_id`, () =>
        HttpResponse.json({ detail: "Error interno" }, { status: 500 }),
      ),
    );
    const { user, dialog } = await abrirEdicion();

    const diagnostico = dialog.getByLabelText(/Diagnóstico/i);
    await user.clear(diagnostico);
    await user.type(diagnostico, "Trastorno adaptativo");
    await user.click(dialog.getByRole("button", { name: /Guardar cambios/i }));

    expect(await dialog.findByRole("alert")).toHaveTextContent(/No se pudo guardar/i);
    expect(dialog.getByLabelText(/Diagnóstico/i)).toHaveValue("Trastorno adaptativo");
  });
});

describe("PatientSheet — accesos rápidos del ingreso", () => {
  it("'Nueva licencia' abre el alta de licencia con el folio del ingreso", async () => {
    mocksBase();
    const user = userEvent.setup();
    renderSheet();
    const boton = await screen.findByRole("button", { name: /Nueva licencia/i });
    expect(boton).toBeEnabled();
    await user.click(boton);
    const dialog = await screen.findByRole("dialog", { name: /Nueva licencia médica/i });
    expect(within(dialog).getByText(/F-2026-0055/)).toBeInTheDocument();
  });

  it("'Agendar control' abre el registro de control médico", async () => {
    mocksBase();
    const user = userEvent.setup();
    renderSheet();
    const boton = await screen.findByRole("button", { name: /Agendar control/i });
    expect(boton).toBeEnabled();
    await user.click(boton);
    expect(await screen.findByRole("dialog", { name: /Nuevo control médico/i })).toBeInTheDocument();
  });
});
