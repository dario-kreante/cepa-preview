/**
 * SolicitudRecaDialog — QA-003: registrar o corregir la fecha de solicitud de la RECA.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { SolicitudRecaDialog } from "./SolicitudRecaDialog";
import { hoyChile } from "./solicitudRecaSchema";
import type { CasoReintegroRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

const CASO = {
  id: 7,
  ingreso_id: 10,
  rut: "11.111.111-1",
  nombre: "Paciente Demo",
  tipo_derivacion: "DIEP",
  fecha_caso: "2026-06-20",
  region: "Maule",
  estado_reintegro: "pendiente",
  fecha_solicitud_reca: null,
  estado_solicitud_reca: "pendiente",
} as CasoReintegroRead;

function renderDialog(caso: Partial<CasoReintegroRead> = {}, onOpenChange = () => {}) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <SolicitudRecaDialog caso={{ ...CASO, ...caso }} open onOpenChange={onOpenChange} />
    </QueryClientProvider>,
  );
}

function capturar() {
  const spy = vi.fn();
  server.use(
    http.patch(`${BASE}/api/v1/reintegros/7/solicitud-reca`, async ({ request }) => {
      const body = (await request.json()) as Record<string, string>;
      spy(body);
      return HttpResponse.json({ ...CASO, ...body, estado_solicitud_reca: "solicitada" });
    }),
  );
  return spy;
}

function fechar(valor: string) {
  fireEvent.change(screen.getByLabelText(/Fecha de solicitud/i), { target: { value: valor } });
}

describe("SolicitudRecaDialog", () => {
  it("no manda nada al abrirse (StrictMode: sin mutaciones en el montaje)", () => {
    const spy = capturar();
    renderDialog();
    expect(spy).not.toHaveBeenCalled();
  });

  it("registra la fecha y cierra", async () => {
    const spy = capturar();
    const cerrar = vi.fn();
    renderDialog({}, cerrar);
    fechar("2026-06-25");
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ fecha_solicitud_reca: "2026-06-25" }));
    await waitFor(() => expect(cerrar).toHaveBeenCalledWith(false));
  });

  it("limita el selector entre la fecha del caso y hoy", () => {
    renderDialog();
    const input = screen.getByLabelText(/Fecha de solicitud/i);
    expect(input).toHaveAttribute("min", "2026-06-20");
    expect(input).toHaveAttribute("max", hoyChile());
  });

  it("rechaza una fecha futura sin llamar al servidor", async () => {
    const spy = capturar();
    renderDialog();
    fechar("2999-01-01");
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no puede ser futura");
    expect(spy).not.toHaveBeenCalled();
  });

  it("rechaza una fecha anterior a la del caso sin llamar al servidor", async () => {
    const spy = capturar();
    renderDialog();
    fechar("2026-06-19");
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("20-06-2026");
    expect(spy).not.toHaveBeenCalled();
  });

  it("sin fecha pide indicarla", async () => {
    const spy = capturar();
    renderDialog();
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Indica la fecha/);
    expect(spy).not.toHaveBeenCalled();
  });

  it("al corregir parte de la fecha registrada y lo dice en el título", () => {
    renderDialog({ fecha_solicitud_reca: "2026-06-22", estado_solicitud_reca: "solicitada" });
    expect(screen.getByText("Corregir solicitud de RECA")).toBeInTheDocument();
    expect(screen.getByLabelText(/Fecha de solicitud/i)).toHaveValue("2026-06-22");
  });

  it("muestra el mensaje del backend si rechaza la fecha", async () => {
    server.use(
      http.patch(`${BASE}/api/v1/reintegros/7/solicitud-reca`, () =>
        HttpResponse.json({ detail: "La fecha de solicitud de la RECA no puede ser futura." }, { status: 422 }),
      ),
    );
    renderDialog();
    fechar("2026-06-25");
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no puede ser futura");
  });
});
