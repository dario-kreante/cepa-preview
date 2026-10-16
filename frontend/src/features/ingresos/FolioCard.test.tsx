import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { FolioCard } from "./FolioCard";

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderCard(editable: boolean) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <FolioCard pacienteId={1} ingresoId={10} folio="F-2026-0063" editable={editable} />
    </QueryClientProvider>,
  );
}

describe("FolioCard", () => {
  it("sin permiso solo muestra el folio", () => {
    renderCard(false);
    expect(screen.getByText("F-2026-0063")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar folio" })).not.toBeInTheDocument();
  });

  it("la Administrativa corrige el folio y se envía sin espacios", async () => {
    let enviado: unknown;
    server.use(
      http.put(`${BASE}/api/v1/ingresos/10/folio`, async ({ request }) => {
        enviado = await request.json();
        return HttpResponse.json({ id: 10, folio: "F-2026-0999" });
      }),
    );
    renderCard(true);
    await userEvent.click(screen.getByRole("button", { name: "Editar folio" }));
    const input = screen.getByLabelText("Folio nuevo");
    await userEvent.clear(input);
    await userEvent.type(input, " F-2026-0999 ");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await vi.waitFor(() => expect(enviado).toEqual({ folio: "F-2026-0999" }));
    await vi.waitFor(() => expect(screen.queryByLabelText("Folio nuevo")).not.toBeInTheDocument());
  });

  it("si el folio ya es de otro paciente lo dice y deja corregirlo", async () => {
    server.use(
      http.put(`${BASE}/api/v1/ingresos/10/folio`, () =>
        HttpResponse.json({ detail: "x" }, { status: 409 }),
      ),
    );
    renderCard(true);
    await userEvent.click(screen.getByRole("button", { name: "Editar folio" }));
    const input = screen.getByLabelText("Folio nuevo");
    await userEvent.clear(input);
    await userEvent.type(input, "F-2026-0001");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El folio F-2026-0001 ya está emitido para otro paciente.",
    );
    expect(screen.getByLabelText("Folio nuevo")).toHaveValue("F-2026-0001");
  });
});
