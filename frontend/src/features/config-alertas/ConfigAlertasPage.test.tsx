import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { ConfigAlertasPage } from "./ConfigAlertasPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

const CONFIG = [
  { tipo: "vencimiento_licencia", dias: 3, habiles: true, activo: true, actualizado_por: "migracion" },
  { tipo: "oda_por_vencer", dias: 7, habiles: false, activo: true, actualizado_por: "migracion" },
];
const FESTIVOS = [{ id: 1, fecha: "2026-09-18", descripcion: "Independencia Nacional" }];

let putBody: unknown = null;
let postBody: unknown = null;
let borrado: string | null = null;

beforeEach(() => {
  putBody = null;
  postBody = null;
  borrado = null;
  server.use(
    http.get(`${BASE}/api/v1/config-alertas`, () => HttpResponse.json(CONFIG)),
    http.put(`${BASE}/api/v1/config-alertas`, async ({ request }) => {
      putBody = await request.json();
      return HttpResponse.json(CONFIG);
    }),
    http.get(`${BASE}/api/v1/config-alertas/festivos`, () => HttpResponse.json(FESTIVOS)),
    http.post(`${BASE}/api/v1/config-alertas/festivos`, async ({ request }) => {
      postBody = await request.json();
      return HttpResponse.json({ id: 2, ...(postBody as object) }, { status: 201 });
    }),
    http.delete(`${BASE}/api/v1/config-alertas/festivos/:id`, ({ params }) => {
      borrado = String(params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
});

function renderComo(rol: keyof typeof TOKENS) {
  tokenStore.setAccess(TOKENS[rol]);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <ConfigAlertasPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ConfigAlertasPage (COMP-2609-07)", () => {
  it.each(["Administrativo", "Auditor"] as const)("%s no puede entrar", (rol) => {
    renderComo(rol);
    expect(screen.getByText(/restringida al perfil Coordinación/i)).toBeInTheDocument();
  });

  it("Coordinación edita días, hábiles y activo de un tipo y guarda", async () => {
    const user = userEvent.setup();
    renderComo("Coordinacion");
    const fila = await screen.findByTestId("fila-vencimiento_licencia");
    const dias = within(fila).getByLabelText(/Días/i);
    await user.clear(dias);
    await user.type(dias, "5");
    await user.click(within(fila).getByLabelText(/Activo/i));
    await user.click(screen.getByRole("button", { name: /Guardar umbrales/i }));
    await waitFor(() => expect(putBody).not.toBeNull());
    expect(putBody).toEqual(
      expect.arrayContaining([
        { tipo: "vencimiento_licencia", dias: 5, habiles: true, activo: false },
      ]),
    );
  });

  it("lista festivos, agrega uno y elimina otro", async () => {
    const user = userEvent.setup();
    renderComo("Coordinacion");
    expect(await screen.findByText("Independencia Nacional")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Fecha/i), "2026-12-31");
    await user.type(screen.getByLabelText(/Descripción/i), "Feriado bancario");
    await user.click(screen.getByRole("button", { name: /Agregar festivo/i }));
    await waitFor(() =>
      expect(postBody).toEqual({ fecha: "2026-12-31", descripcion: "Feriado bancario" }),
    );

    await user.click(screen.getByRole("button", { name: /Eliminar festivo 2026-09-18/i }));
    await waitFor(() => expect(borrado).toBe("1"));
  });
});
