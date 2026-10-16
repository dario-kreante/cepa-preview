import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { FarmacosPage } from "./FarmacosPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("FarmacosPage · ?paciente=", () => {
  it("abre directo el paciente que viene de una alerta de receta", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/pacientes/82`, () =>
        HttpResponse.json({
          id: 82, rut: "390000065", nombre: "Humberto Escobar", sexo: "M", edad: 50, region: "Maule",
          comuna: null, telefono: null, correo: null, estado_registro: "completo", origen: "SIGE",
        }),
      ),
      http.get(`${BASE}/api/v1/pacientes/82/vista-360`, () =>
        HttpResponse.json({ paciente: { id: 82 }, ingresos: [] }),
      ),
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/farmacos?paciente=82"]}>
          <AuthProvider>
            <FarmacosPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Sigue seleccionado después del debounce de 300 ms del buscador.
    await new Promise((r) => setTimeout(r, 500));
    expect(await screen.findByText("Este paciente no tiene ingresos registrados.")).toBeInTheDocument();
  });
});
