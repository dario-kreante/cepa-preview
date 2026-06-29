import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useDashboard } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useDashboard", () => {
  it("carga los indicadores del dashboard", async () => {
    server.use(
      http.get(`${BASE}/api/v1/dashboard`, () =>
        HttpResponse.json({
          total_ingresos: 12,
          total_atenciones: 8,
          total_inasistencias: 2,
          total_anulaciones: 1,
          total_citas_agendadas: 5,
          carga_por_profesional: [{ profesional_id: 1, total_ingresos: 12 }],
          cumplimiento_convenios: [
            { tipo_convenio: "FONASA", total_realizadas: 8 },
          ],
          filtros_aplicados: {},
        }),
      ),
    );
    const { result } = renderHook(() => useDashboard({}), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total_ingresos).toBe(12);
    expect(result.current.data?.carga_por_profesional.length).toBe(1);
  });
});
