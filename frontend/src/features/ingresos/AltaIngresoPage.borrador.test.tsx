/**
 * Alta de ingreso que completa un paciente borrador (?paciente=<id>).
 *
 *  1. Precarga nombre, RUT, edad y región desde GET /api/v1/pacientes/{id}.
 *  2. Envía paciente_id en el POST /api/v1/ingresos.
 *  3. Borrador sin RUT: el RUT es opcional, se muestra la identificación de SALUTEM
 *     y el POST no lleva RUT.
 *  4. Sin ?paciente= el RUT sigue siendo obligatorio.
 */
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { AltaIngresoPage } from "./AltaIngresoPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

const BORRADOR = {
  id: 7,
  rut: null,
  nombre: "JUAN PEREZ SOTO",
  sexo: null,
  edad: null,
  region: null,
  comuna: null,
  telefono: null,
  correo: null,
  estado_registro: "pendiente_folio",
  origen: "SALUTEM",
};

const PENDIENTE = {
  id: 7,
  nombre: "JUAN PEREZ SOTO",
  rut: null,
  identificacion_salutem: "sin_id_1141409",
  salutem_persona_id: 1141409,
  creado_en: "2026-10-16T09:00:00Z",
  primera_atencion: "2026-10-15",
  ultima_atencion: "2026-10-15",
  atenciones: 1,
  especialidades: ["Médico/a"],
};

const INGRESO_OK = {
  id: 1,
  paciente_id: 7,
  folio: "F-2026-0001",
  estado: "activo",
  fecha_ingreso: "2026-10-16",
  folio_manual: false,
  numero_siniestro: null,
  fecha_diep_diat: null,
  tipo_derivacion: "DIEP",
  tipo_ingreso: "consulta_espontanea",
  modelo_tratamiento: "ambulatorio",
  diagnostico: "Ansiedad",
  razon_social: null,
  tipo_alta: null,
  fecha_alta: null,
  flag_revision: false,
  observaciones: null,
  tratamiento_iniciado: false,
};

function mockAlta(paciente: object = BORRADOR) {
  const enviados: Record<string, unknown>[] = [];
  server.use(
    http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () => HttpResponse.json([PENDIENTE])),
    http.get(`${BASE}/api/v1/pacientes/7`, () => HttpResponse.json(paciente)),
    http.post(`${BASE}/api/v1/ingresos`, async ({ request }) => {
      enviados.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(INGRESO_OK, { status: 201 });
    }),
  );
  return enviados;
}

let ultimoQc: QueryClient;

function renderPage(ruta: string) {
  tokenStore.setAccess(TOKENS.Administrativo);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  ultimoQc = qc;
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
        <AuthProvider>
          <AltaIngresoPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function completarCampos(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Edad"), "40");
  await user.type(screen.getByLabelText("Región"), "Maule");
  await user.selectOptions(screen.getByLabelText("Sexo"), "M");
  await user.type(screen.getByLabelText("Diagnóstico"), "Ansiedad");
  await user.type(screen.getByLabelText("Modelo de tratamiento"), "ambulatorio");
  await user.type(screen.getByLabelText("Fecha de ingreso"), "2026-10-16");
}

describe("AltaIngresoPage — completar un paciente borrador", () => {
  it("precarga el nombre y envía paciente_id; sin RUT en el borrador, no se pide", async () => {
    const enviados = mockAlta();
    renderPage("/ingresos/nuevo?paciente=7");
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByLabelText("Nombre")).toHaveValue("JUAN PEREZ SOTO"));
    // Identificación de SALUTEM a la vista, RUT opcional
    expect(await screen.findByText("sin_id_1141409")).toBeInTheDocument();
    expect(screen.getByLabelText(/^RUT/)).toHaveValue("");
    // Los datos que faltan quedan vacíos, no inventados
    expect(screen.getByLabelText("Edad")).toHaveValue("");
    expect(screen.getByLabelText("Región")).toHaveValue("");

    await completarCampos(user);
    await user.click(screen.getByRole("button", { name: /crear ingreso/i }));

    await waitFor(() => expect(enviados).toHaveLength(1));
    expect(enviados[0].paciente_id).toBe(7);
    expect(enviados[0].nombre).toBe("JUAN PEREZ SOTO");
    expect(enviados[0].rut ?? null).toBeNull();
    expect(enviados[0].edad).toBe(40);
  });

  it("un RUT escrito en el borrador sin RUT igual se valida", async () => {
    const enviados = mockAlta();
    renderPage("/ingresos/nuevo?paciente=7");
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByLabelText("Nombre")).toHaveValue("JUAN PEREZ SOTO"));
    await user.type(screen.getByLabelText(/^RUT/), "11.111.111-2");
    await user.click(screen.getByRole("button", { name: /crear ingreso/i }));
    expect(await screen.findByText(/RUT inválido/i)).toBeInTheDocument();
    expect(enviados).toHaveLength(0);
  });

  it("precarga RUT, edad y región de un borrador que ya los tiene", async () => {
    mockAlta({ ...BORRADOR, rut: "11.111.111-1", sexo: "M", edad: 33, region: "Maule" });
    renderPage("/ingresos/nuevo?paciente=7");

    await waitFor(() => expect(screen.getByLabelText("Nombre")).toHaveValue("JUAN PEREZ SOTO"));
    expect(screen.getByLabelText(/^RUT/)).toHaveValue("11.111.111-1");
    expect(screen.getByLabelText("Edad")).toHaveValue("33");
    expect(screen.getByLabelText("Región")).toHaveValue("Maule");
    expect(screen.getByLabelText("Sexo")).toHaveValue("M");
  });

  it("sin ?paciente= el RUT sigue siendo obligatorio", async () => {
    const enviados = mockAlta();
    renderPage("/ingresos/nuevo");
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Nombre"), "Ana");
    await user.click(screen.getByRole("button", { name: /crear ingreso/i }));
    expect((await screen.findAllByText("Requerido")).length).toBeGreaterThan(0);
    expect(enviados).toHaveLength(0);
  });

  it("al crear el ingreso invalida las alertas (la de Falta folio se resuelve)", async () => {
    mockAlta();
    renderPage("/ingresos/nuevo?paciente=7");
    const spy = vi.spyOn(ultimoQc, "invalidateQueries");
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByLabelText("Nombre")).toHaveValue("JUAN PEREZ SOTO"));
    await completarCampos(user);
    await user.click(screen.getByRole("button", { name: /crear ingreso/i }));

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["alertas"] })),
    );
  });

  it("un paciente con registro completo no muestra el formulario de completar", async () => {
    mockAlta({ ...BORRADOR, estado_registro: "completo", rut: "11.111.111-1" });
    renderPage("/ingresos/nuevo?paciente=7");

    expect(await screen.findByText("Este paciente ya tiene su registro completo.")).toBeInTheDocument();
    expect(screen.queryByText("Completar registro")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /crear ingreso/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ingresos/i })).toHaveAttribute("href", "/ingresos");
  });

  it("un paciente descartado indica que fue descartado", async () => {
    mockAlta({ ...BORRADOR, estado_registro: "descartado" });
    renderPage("/ingresos/nuevo?paciente=7");

    expect(await screen.findByText("Este paciente fue descartado.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /crear ingreso/i })).not.toBeInTheDocument();
  });
});
