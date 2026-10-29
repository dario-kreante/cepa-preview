/**
 * Tests for NuevoCasoReintegroDialog — QA Pilar 22-10 QA-008.
 *
 * Covers:
 *  1. `prefill` loads the selected paciente's data into the form.
 *  2. A paciente without RUT can still create the case: RUT is optional and the
 *     POST sends `rut: null`.
 *  3. The form no longer asks for edad/sexo; it asks for the company's razón social
 *     (prefilled from the ingreso) and the tipo de trabajador (required on create).
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { NuevoCasoReintegroDialog } from "./NuevoCasoReintegroDialog";
import type { CasoReintegroForm } from "./casoReintegroSchema";

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderDialog(prefill: Partial<CasoReintegroForm>) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const onSaved = vi.fn();
  render(
    <QueryClientProvider client={qc}>
      <NuevoCasoReintegroDialog
        ingresoId={10}
        open
        onOpenChange={() => {}}
        onSaved={onSaved}
        prefill={prefill}
      />
    </QueryClientProvider>,
  );
  return onSaved;
}

describe("NuevoCasoReintegroDialog — precarga", () => {
  it("precarga RUT, nombre, región, razón social y tipo de derivación", async () => {
    renderDialog({
      rut: "12.345.678-5",
      nombre: "Juan Pérez",
      region: "Maule",
      razon_social: "Forestal Maule SpA",
      tipo_derivacion: "Reingreso ISL",
    });

    expect(await screen.findByLabelText(/RUT/i)).toHaveValue("12.345.678-5");
    expect(screen.getByLabelText(/Nombre/i)).toHaveValue("Juan Pérez");
    expect(screen.getByLabelText(/Región/i)).toHaveValue("Maule");
    expect(screen.getByLabelText(/Razón social/i)).toHaveValue("Forestal Maule SpA");
    expect(screen.getByLabelText(/Tipo de derivación/i)).toHaveValue("Reingreso ISL");
  });

  it("no pide edad ni sexo y pide el tipo de trabajador", async () => {
    renderDialog({ nombre: "Juan Pérez" });

    const tipo = await screen.findByLabelText(/Tipo de trabajador/i);
    expect(screen.queryByLabelText(/^Edad/i)).toBeNull();
    expect(screen.queryByLabelText(/^Sexo/i)).toBeNull();
    expect(
      Array.from((tipo as HTMLSelectElement).options).map((o) => o.textContent),
    ).toEqual(["Selecciona…", "Dependiente", "Independiente"]);
  });
});

describe("NuevoCasoReintegroDialog — paciente sin RUT", () => {
  it("permite crear el caso y envía rut null", async () => {
    const postSpy = vi.fn();
    server.use(
      http.post(`${BASE}/api/v1/reintegros`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        postSpy(body);
        return HttpResponse.json(
          { id: 1, ...body, estado_reintegro: "pendiente" },
          { status: 201 },
        );
      }),
    );
    const onSaved = renderDialog({
      rut: "",
      nombre: "Paciente Sin Rut",
      region: "Maule",
    });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText(/Fecha del caso/i), "2026-10-20");
    await user.selectOptions(screen.getByLabelText(/Tipo de trabajador/i), "dependiente");
    const dialog = screen.getByRole("dialog");
    await user.click(dialog.querySelector('button[type="submit"]') as HTMLElement);

    await waitFor(() => expect(postSpy).toHaveBeenCalledOnce());
    const sent = postSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(sent.rut).toBeNull();
    expect(sent.ingreso_id).toBe(10);
    expect(sent.nombre).toBe("Paciente Sin Rut");
    expect(sent.tipo_trabajador).toBe("dependiente");
    expect(sent.razon_social).toBeNull();
    expect(sent).not.toHaveProperty("sexo");
    expect(sent).not.toHaveProperty("edad");
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  });
});

describe("NuevoCasoReintegroDialog — tipo de trabajador obligatorio en el alta", () => {
  it("no envía el alta sin tipo de trabajador", async () => {
    const postSpy = vi.fn();
    server.use(
      http.post(`${BASE}/api/v1/reintegros`, async ({ request }) => {
        postSpy(await request.json());
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderDialog({ nombre: "Juan Pérez", region: "Maule" });
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText(/Fecha del caso/i), "2026-10-20");
    const dialog = screen.getByRole("dialog");
    await user.click(dialog.querySelector('button[type="submit"]') as HTMLElement);

    expect(await screen.findByText("El tipo de trabajador es requerido")).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });
});
