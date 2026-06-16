import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useLicenciasPorFolio } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useLicenciasPorFolio", () => {
  it("carga el historial del folio", async () => {
    server.use(
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({
          folio: "123",
          historial: [
            {
              id: 1,
              folio_lm: "LM-1",
              tipo_lm: "1",
              tipo_reposo: "total",
              cantidad_dias: 14,
              anulada: false,
            },
          ],
          dias_acumulados: 14,
        }),
      ),
    );
    const { result } = renderHook(() => useLicenciasPorFolio("123"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.historial.length).toBe(1);
  });
});
