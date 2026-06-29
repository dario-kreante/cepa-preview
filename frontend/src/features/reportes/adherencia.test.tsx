import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useReporteAdherencia } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useReporteAdherencia", () => {
  it("obtiene la adherencia de un ingreso por folio", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/adherencia/:folio_id`, () =>
        HttpResponse.json({
          folio_id: 1,
          citas_agendadas: 4,
          citas_realizadas: 3,
          pct_adherencia: 75,
          sesiones_realizadas: 3,
          sesiones_plan: 6,
          aumentos_isl: 1,
          pct_avance: 50,
        }),
      ),
    );
    const { result } = renderHook(() => useReporteAdherencia(), { wrapper });
    result.current.mutate(1);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.pct_adherencia).toBe(75);
  });
});
