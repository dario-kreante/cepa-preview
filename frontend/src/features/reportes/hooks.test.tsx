import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useReporteOdasVencidas, useReporteOperativo } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useReporteOperativo", () => {
  it("genera el reporte operativo con el rango dado", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/operativo`, () =>
        HttpResponse.json({
          items: [
            {
              fecha: "2026-06-22",
              programa: "PRAIS",
              profesional_id: 1,
              total_citas: 4,
              realizadas: 3,
              inasistencias: 1,
              anuladas: 0,
              agendadas: 0,
            },
          ],
          totales: { total_citas: 4, realizadas: 3 },
        }),
      ),
    );
    const { result } = renderHook(() => useReporteOperativo(), { wrapper });
    result.current.mutate({ fecha_desde: "2026-06-01", fecha_hasta: "2026-06-30" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].realizadas).toBe(3);
  });
});

describe("useReporteOdasVencidas", () => {
  it("consulta ODAS vencidas sin filtros", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reportes/odas-vencidas`, () =>
        HttpResponse.json({ fecha_consulta: "2026-06-29", items: [] }),
      ),
    );
    const { result } = renderHook(() => useReporteOdasVencidas(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items.length).toBe(0);
  });
});
