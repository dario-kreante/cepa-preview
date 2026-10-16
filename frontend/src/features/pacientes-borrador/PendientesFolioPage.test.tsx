/**
 * Pantalla "Pendientes de folio": pacientes borrador creados desde SALUTEM.
 *
 * Covers:
 *  1. Lista nombre, identificación SALUTEM, primera atención y especialidad (paciente sin RUT).
 *  2. "Completar registro" lleva a /ingresos/nuevo?paciente=<id>.
 *  3. "Descartar" exige motivo y hace POST con { motivo }.
 *  4. Lista vacía.
 *  5. Menú: el item no aparece para Auditor y muestra el contador para Administrativo.
 */
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { AppShell } from "@/app/shell/AppShell";
import { PendientesFolioPage } from "./PendientesFolioPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

const BORRADOR = {
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

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{pathname + search}</p>;
}

function renderizarPagina() {
  tokenStore.setAccess(TOKENS.Administrativo);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Toaster />
      <MemoryRouter initialEntries={["/pendientes-folio"]}>
        <AuthProvider>
          <Routes>
            <Route path="/pendientes-folio" element={<PendientesFolioPage />} />
            <Route path="*" element={<Ubicacion />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderizarMenu(token: string) {
  tokenStore.setAccess(token);
  server.use(
    http.get(`${BASE}/api/v1/alertas`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
    http.get(`${BASE}/api/v1/dashboard/activos`, () => HttpResponse.json({})),
  );
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<div>inicio</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PendientesFolioPage", () => {
  it("lista el borrador sin RUT con su identificación SALUTEM", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () => HttpResponse.json([BORRADOR])),
    );
    renderizarPagina();

    expect(await screen.findByText("JUAN PEREZ SOTO")).toBeInTheDocument();
    expect(screen.getByText("sin_id_1141409")).toBeInTheDocument();
    expect(screen.getAllByText("15-10-2026").length).toBeGreaterThan(0);
    expect(screen.getByText("Médico/a")).toBeInTheDocument();
  });

  it("'Completar registro' lleva al alta de ingreso con el paciente", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () => HttpResponse.json([BORRADOR])),
    );
    renderizarPagina();

    await userEvent.click(await screen.findByRole("button", { name: /completar registro/i }));

    expect(await screen.findByTestId("ubicacion")).toHaveTextContent("/ingresos/nuevo?paciente=7");
  });

  it("'Descartar' exige motivo y envía { motivo }", async () => {
    let cuerpo: unknown = null;
    server.use(
      http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () => HttpResponse.json([BORRADOR])),
      http.post(`${BASE}/api/v1/pacientes/7/descartar`, async ({ request }) => {
        cuerpo = await request.json();
        return HttpResponse.json({ ...BORRADOR, estado_registro: "descartado", origen: "SALUTEM" });
      }),
    );
    renderizarPagina();

    await userEvent.click(await screen.findByRole("button", { name: /^descartar$/i }));
    const confirmar = await screen.findByRole("button", { name: /descartar paciente/i });

    // Sin motivo no se envía.
    await userEvent.click(confirmar);
    expect(await screen.findByText(/indica el motivo/i)).toBeInTheDocument();
    expect(cuerpo).toBeNull();

    await userEvent.type(screen.getByLabelText(/motivo/i), "No es paciente del CEPA");
    await userEvent.click(confirmar);

    await waitFor(() => expect(cuerpo).toEqual({ motivo: "No es paciente del CEPA" }));
  });

  it("sin borradores avisa que no hay pendientes", async () => {
    server.use(http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () => HttpResponse.json([])));
    renderizarPagina();

    expect(await screen.findByText(/no hay pacientes pendientes de folio/i)).toBeInTheDocument();
  });
});

describe("Menú · Pendientes de folio", () => {
  it("no aparece para Auditor (ni se pide la lista)", async () => {
    let pedida = false;
    server.use(
      http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () => {
        pedida = true;
        return HttpResponse.json([]);
      }),
    );
    renderizarMenu(TOKENS.Auditor);
    // El resto del menú sí está; el item restringido no.
    expect(await screen.findByText("Controles médicos")).toBeInTheDocument();
    expect(screen.queryByText("Pendientes de folio")).not.toBeInTheDocument();
    expect(pedida).toBe(false);
  });

  it("muestra el contador para Administrativo", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/pendientes-folio`, () =>
        HttpResponse.json([BORRADOR, { ...BORRADOR, id: 8 }]),
      ),
    );
    renderizarMenu(TOKENS.Administrativo);

    const item = await screen.findByRole("link", { name: /pendientes de folio/i });
    await waitFor(() => expect(item).toHaveTextContent("2"));
  });
});
