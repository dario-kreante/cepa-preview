/**
 * Ficha de un paciente borrador (pendiente de folio, creado desde SALUTEM).
 *
 *  1. Muestra el aviso y "Completar registro" (solo escritores) → /ingresos/nuevo?paciente=<id>.
 *  2. El Auditor ve el aviso pero no el botón.
 *  3. Con RUT/sexo/edad/región nulos no muestra "null" ni "undefined".
 *  4. Editar la ficha de un paciente sin edad no inventa un 0 ni envía datos inventados.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { PatientSheet } from "./PatientSheet";

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

const AVISO = /Este paciente viene de SALUTEM y le falta el folio para completar su registro/;

function mockVista(paciente: object, ingresos: object[] = []) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/:paciente_id/vista-360`, () =>
      HttpResponse.json({
        paciente,
        ingresos,
        farmacos: [],
        licencias: [],
        controles: [],
        reintegro: [],
      }),
    ),
    http.get(`${BASE}/api/v1/fichas-clinicas/:folio`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/ingresos/:ingreso_id/licencias`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`, () =>
      HttpResponse.json([]),
    ),
  );
}

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{pathname + search}</p>;
}

function renderSheet(token: string) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/ingresos"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/ingresos"
              element={<PatientSheet pacienteId={7} open onOpenChange={() => {}} />}
            />
            <Route path="*" element={<Ubicacion />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PatientSheet — paciente borrador", () => {
  it("muestra el aviso y 'Completar registro' lleva al alta con el paciente", async () => {
    mockVista(BORRADOR);
    renderSheet(TOKENS.Administrativo);

    expect(await screen.findByText(AVISO)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Completar registro/i }));
    expect(await screen.findByTestId("ubicacion")).toHaveTextContent("/ingresos/nuevo?paciente=7");
  });

  it("el Auditor ve el aviso pero no el botón", async () => {
    mockVista(BORRADOR);
    renderSheet(TOKENS.Auditor);

    expect(await screen.findByText(AVISO)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Completar registro/i })).not.toBeInTheDocument();
  });

  it("un paciente completo no muestra aviso ni botón", async () => {
    mockVista({
      ...BORRADOR,
      rut: "11.222.333-4",
      sexo: "F",
      edad: 42,
      region: "Valparaíso",
      estado_registro: "completo",
      origen: "SIGE",
    });
    renderSheet(TOKENS.Coordinacion);

    expect(await screen.findByText("JUAN PEREZ SOTO")).toBeInTheDocument();
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Completar registro/i })).not.toBeInTheDocument();
  });

  it("con RUT, sexo, edad y región nulos no muestra 'null' ni 'undefined'", async () => {
    mockVista(BORRADOR);
    renderSheet(TOKENS.Coordinacion);

    await screen.findByText(AVISO);
    const dialogo = screen.getByRole("dialog");
    expect(dialogo.textContent).not.toMatch(/null|undefined/i);
    expect(dialogo.textContent).not.toMatch(/años/);
  });

  it("editar la ficha de un paciente sin edad deja la edad vacía y no envía un 0", async () => {
    mockVista(BORRADOR, [
      {
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
      },
    ]);
    const putSpy = vi.fn();
    server.use(
      http.put(`${BASE}/api/v1/ingresos/:ingreso_id`, async ({ request }) => {
        putSpy(await request.json());
        return HttpResponse.json({});
      }),
    );
    renderSheet(TOKENS.Coordinacion);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /Editar ficha/i }));
    const dialog = within(await screen.findByRole("dialog", { name: /Editar ficha/i }));

    expect(dialog.getByLabelText(/Edad/i)).toHaveValue(null);
    expect(dialog.getByLabelText(/Región/i)).toHaveValue("");
    expect(dialog.getByLabelText(/Sexo/i)).toHaveValue("");

    await user.click(dialog.getByRole("button", { name: /Guardar cambios/i }));
    await waitFor(() => expect(dialog.getAllByText(/Requerido|fuera de rango/i).length).toBeGreaterThan(0));
    expect(putSpy).not.toHaveBeenCalled();
  });
});
