import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useVentanas } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useVentanas", () => {
  it("lista las ventanas de proceso configuradas", async () => {
    server.use(
      http.get(`${BASE}/api/v1/ventanas-proceso`, () =>
        HttpResponse.json([
          {
            id: 1,
            proceso: "licencias",
            columnas_visibles: ["folio", "estado"],
            orden_por_defecto: "fecha",
            creado_por: "admin",
            created_at: "2026-06-25T00:00:00Z",
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useVentanas(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].proceso).toBe("licencias");
    expect(result.current.data?.[0].columnas_visibles).toEqual(["folio", "estado"]);
  });
});
