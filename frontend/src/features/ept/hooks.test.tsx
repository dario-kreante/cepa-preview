import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useCaso, useProceso } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCaso", () => {
  it("carga un caso EPT por id", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:caso_id`, () =>
        HttpResponse.json({
          id: 1,
          ingreso_id: 10,
          fecha_ingreso_ept: "2026-06-16",
          factor_riesgo: "carga",
          corresponde_ept: true,
          estado: "abierto",
          created_at: "2026-06-16T00:00:00Z",
          updated_at: null,
        }),
      ),
    );

    const { result } = renderHook(() => useCaso(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe(1);
  });
});

describe("useProceso", () => {
  it("resuelve a null cuando el servidor devuelve 404", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/casos-ept/:caso_id/proceso`,
        () => new HttpResponse(null, { status: 404 }),
      ),
    );

    const { result } = renderHook(() => useProceso(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });
});
