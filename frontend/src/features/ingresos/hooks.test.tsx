import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useBuscarPacientes } from "./hooks";
import type { ReactNode } from "react";

const BASE = import.meta.env.VITE_API_BASE_URL;
const server = setupServer(
  http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
    HttpResponse.json([{ id: 1, rut: "11111111-1", nombre: "Ana", sexo: "F", edad: 30, region: "Maule", comuna: null, telefono: null, correo: null }]),
  ),
);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useBuscarPacientes", () => {
  it("devuelve pacientes para una query no vacía", async () => {
    const { result } = renderHook(() => useBuscarPacientes("Ana"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].nombre).toBe("Ana");
  });
});
