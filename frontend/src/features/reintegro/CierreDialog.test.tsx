/**
 * CierreDialog — QA-003: altas unificadas.
 *  - «Tipo de alta» ofrece solo Terapéutica, Abandono y Derivación (opcional).
 *  - Un reintegro total exige alta médica, alta psicológica o un tipo de alta.
 *  - Cada casilla de alta marcada exige su fecha.
 *  - Un caso antiguo con tipo «medica»/«psicologica» se sigue viendo y no se pierde al editar.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { CierreDialog } from "./CierreDialog";
import type { CasoReintegroRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

const CASO: CasoReintegroRead = {
  id: 7,
  ingreso_id: 10,
  rut: "11.111.111-1",
  nombre: "Paciente Demo",
  tipo_derivacion: "DIEP",
  fecha_caso: "2026-06-20",
  sexo: "F",
  edad: 40,
  region: "Maule",
  comuna: null,
  rubro_empleador: null,
  razon_social: null,
  tipo_trabajador: null,
  estado_reintegro: "pendiente",
  fecha_reintegro: null,
  remitido_isl: false,
  alta_medica: false,
  fecha_alta_medica: null,
  alta_psicologica: false,
  fecha_alta_psico: null,
  tipo_alta: null,
  observaciones: null,
} as CasoReintegroRead;

function renderDialog(caso: Partial<CasoReintegroRead> = {}) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <CierreDialog caso={{ ...CASO, ...caso }} open onOpenChange={() => {}} />
    </QueryClientProvider>,
  );
}

function capturarCierre() {
  const spy = vi.fn();
  server.use(
    http.patch(`${BASE}/api/v1/reintegros/7/cierre`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      spy(body);
      return HttpResponse.json({ ...CASO, ...body });
    }),
  );
  return spy;
}

async function guardar(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /Guardar cierre/i }));
}

describe("CierreDialog — tipo de alta", () => {
  it("ofrece solo Terapéutica, Abandono y Derivación", async () => {
    renderDialog();
    const select = (await screen.findByLabelText(/Tipo de alta/i)) as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual([
      "—",
      "Terapéutica",
      "Abandono",
      "Derivación",
    ]);
  });

  it("conserva un tipo de alta antiguo («medica») y lo reenvía al guardar", async () => {
    const spy = capturarCierre();
    renderDialog({ tipo_alta: "medica", estado_reintegro: "parcial" });
    const user = userEvent.setup();

    const select = (await screen.findByLabelText(/Tipo de alta/i)) as HTMLSelectElement;
    expect(select).toHaveValue("medica");
    expect(select.selectedOptions[0].textContent).toMatch(/Médica.*antiguo/i);

    await guardar(user);
    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    expect(spy.mock.calls[0][0].tipo_alta).toBe("medica");
  });

  it("también conserva «psicologica»", async () => {
    renderDialog({ tipo_alta: "psicologica" });
    const select = (await screen.findByLabelText(/Tipo de alta/i)) as HTMLSelectElement;
    expect(select).toHaveValue("psicologica");
    expect(select.selectedOptions[0].textContent).toMatch(/Psicológica.*antiguo/i);
  });

  it("sin tipo antiguo no agrega opciones extra", async () => {
    renderDialog({ tipo_alta: "abandono" });
    const select = (await screen.findByLabelText(/Tipo de alta/i)) as HTMLSelectElement;
    expect(select.options).toHaveLength(4);
  });
});

describe("CierreDialog — validación de altas", () => {
  it("un reintegro total sin ninguna alta no se envía y explica qué falta", async () => {
    const spy = capturarCierre();
    renderDialog();
    const user = userEvent.setup();

    await user.selectOptions(await screen.findByLabelText(/Estado de reintegro/i), "total");
    await user.type(screen.getByLabelText(/Fecha reintegro/i), "2026-07-10");
    await guardar(user);

    expect(
      await screen.findByText(
        "Para un reintegro total, marca el alta médica, el alta psicológica o elige un tipo de alta.",
      ),
    ).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it("un reintegro total con solo tipo de alta se envía", async () => {
    const spy = capturarCierre();
    renderDialog();
    const user = userEvent.setup();

    await user.selectOptions(await screen.findByLabelText(/Estado de reintegro/i), "total");
    await user.type(screen.getByLabelText(/Fecha reintegro/i), "2026-07-10");
    await user.selectOptions(screen.getByLabelText(/Tipo de alta/i), "derivacion");
    await guardar(user);

    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    expect(spy.mock.calls[0][0]).toMatchObject({
      estado_reintegro: "total",
      tipo_alta: "derivacion",
      alta_medica: false,
      alta_psicologica: false,
    });
  });

  it("un reintegro total con solo alta médica y fecha se envía sin tipo de alta", async () => {
    const spy = capturarCierre();
    renderDialog();
    const user = userEvent.setup();

    await user.selectOptions(await screen.findByLabelText(/Estado de reintegro/i), "total");
    await user.type(screen.getByLabelText(/Fecha reintegro/i), "2026-07-10");
    await user.click(screen.getByLabelText(/^Alta médica/i));
    await user.type(await screen.findByLabelText(/Fecha alta médica/i), "2026-07-01");
    await guardar(user);

    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    expect(spy.mock.calls[0][0]).toMatchObject({
      alta_medica: true,
      fecha_alta_medica: "2026-07-01",
      tipo_alta: null,
    });
  });

  it("exige la fecha de cada alta marcada", async () => {
    const spy = capturarCierre();
    renderDialog();
    const user = userEvent.setup();

    await user.click(await screen.findByLabelText(/^Alta médica/i));
    await user.click(screen.getByLabelText(/^Alta psicológica/i));
    await guardar(user);

    expect(await screen.findByText("Indica la fecha del alta médica")).toBeInTheDocument();
    expect(screen.getByText("Indica la fecha del alta psicológica")).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });
});
