import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ConveniosPage } from "./ConveniosPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// JWT con rol Coordinacion
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const SALUTEM_ACTIVO = {
  id: 1,
  nombre: "Convenio ISL MAULE",
  salutem_id: 10,
  activo_salutem: true,
  visible: true,
  seleccionable: true,
  sincronizado_en: "2026-11-23T07:10:00Z",
};
const SALUTEM_INACTIVO = {
  id: 2,
  nombre: "Proyecto ISL Biobío",
  salutem_id: 11,
  activo_salutem: false,
  visible: false,
  seleccionable: false,
  sincronizado_en: "2026-11-22T07:10:00Z",
};
const MANUAL = {
  id: 3,
  nombre: "Convenio Rangers",
  salutem_id: null,
  activo_salutem: false,
  visible: true,
  seleccionable: true,
  sincronizado_en: null,
};

function renderPage() {
  tokenStore.setAccess(WRITER_TOKEN);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <ConveniosPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function usarListado(lista = [SALUTEM_ACTIVO, SALUTEM_INACTIVO, MANUAL]) {
  server.use(http.get(`${BASE}/api/v1/convenios`, () => HttpResponse.json(lista)));
}

describe("ConveniosPage", () => {
  it("lista convenios con origen, estado en SALUTEM y visible", async () => {
    usarListado();
    renderPage();

    const salutem = await screen.findByTestId("row-convenio-1");
    expect(within(salutem).getByText("Convenio ISL MAULE")).toBeInTheDocument();
    expect(within(salutem).getByText("SALUTEM")).toBeInTheDocument();
    expect(within(salutem).getByText("Activo")).toBeInTheDocument();
    expect(within(salutem).getByRole("checkbox")).toBeChecked();

    const inactivo = screen.getByTestId("row-convenio-2");
    expect(within(inactivo).getByText("Inactivo")).toBeInTheDocument();
    expect(within(inactivo).getByRole("checkbox")).not.toBeChecked();

    const manual = screen.getByTestId("row-convenio-3");
    expect(within(manual).getByText("SIGE")).toBeInTheDocument();
    expect(within(manual).getByText("—")).toBeInTheDocument();

    expect(screen.getByTestId("ultima-actualizacion")).toHaveTextContent(
      /Última actualización: \d{2}-\d{2}-\d{4} \d{2}:\d{2}/,
    );
  });

  it("Actualizar desde SALUTEM muestra el resultado", async () => {
    usarListado();
    server.use(
      http.post(`${BASE}/api/v1/convenios/actualizar-salutem`, () =>
        HttpResponse.json({ creados: 1, actualizados: 0, desactivados: 0, errores: [] }),
      ),
    );
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("btn-actualizar-salutem"));

    expect(await screen.findByText(/1 nuevo/)).toBeInTheDocument();
  });

  it("si la actualización trae errores, el aviso los muestra", async () => {
    usarListado();
    server.use(
      http.post(`${BASE}/api/v1/convenios/actualizar-salutem`, () =>
        HttpResponse.json({
          creados: 0, actualizados: 0, desactivados: 0,
          errores: ["SALUTEM devolvió el catálogo de convenios vacío; no se desactivó nada."],
        }),
      ),
    );
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("btn-actualizar-salutem"));

    // El aviso (toast) también lleva el detalle, no solo el panel de errores de la página.
    await waitFor(() => {
      const aviso = document.querySelector("[data-sonner-toast]");
      expect(aviso?.textContent).toContain("SALUTEM devolvió el catálogo de convenios vacío");
    });
  });

  it("si SALUTEM falla muestra el mensaje del 502", async () => {
    usarListado();
    server.use(
      http.post(`${BASE}/api/v1/convenios/actualizar-salutem`, () =>
        HttpResponse.json({ detail: "SALUTEM no respondió; intenta más tarde." }, { status: 502 }),
      ),
    );
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("btn-actualizar-salutem"));

    expect(
      await screen.findByText("SALUTEM no respondió; intenta más tarde."),
    ).toBeInTheDocument();
  });

  it("agregar un convenio manual avisa que conviene crearlo en SALUTEM", async () => {
    usarListado();
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("btn-agregar-convenio"));

    expect(await screen.findByText(/conviene crearlo también en SALUTEM/)).toBeInTheDocument();
  });

  it("409 al agregar muestra «Ya existe un convenio con ese nombre.»", async () => {
    usarListado();
    server.use(
      http.post(`${BASE}/api/v1/convenios`, () =>
        HttpResponse.json({ detail: "duplicado" }, { status: 409 }),
      ),
    );
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("btn-agregar-convenio"));
    await user.type(await screen.findByTestId("input-convenio-nombre"), "Convenio Rangers");
    await user.click(screen.getByTestId("btn-guardar-convenio"));

    expect(await screen.findByText("Ya existe un convenio con ese nombre.")).toBeInTheDocument();
  });

  it("desmarcar Visible llama PATCH {visible:false}", async () => {
    usarListado();
    let cuerpo: unknown = null;
    server.use(
      http.patch(`${BASE}/api/v1/convenios/1`, async ({ request }) => {
        cuerpo = await request.json();
        return HttpResponse.json({ ...SALUTEM_ACTIVO, visible: false });
      }),
    );
    renderPage();
    const user = userEvent.setup();
    const fila = await screen.findByTestId("row-convenio-1");
    await user.click(within(fila).getByRole("checkbox"));

    await waitFor(() => expect(cuerpo).toEqual({ visible: false }));
  });

  it("un convenio de SALUTEM no ofrece renombrar", async () => {
    usarListado();
    renderPage();

    const salutem = await screen.findByTestId("row-convenio-1");
    expect(within(salutem).queryByTestId("btn-renombrar-convenio-1")).not.toBeInTheDocument();
    const manual = screen.getByTestId("row-convenio-3");
    expect(within(manual).getByTestId("btn-renombrar-convenio-3")).toBeInTheDocument();
  });
});
