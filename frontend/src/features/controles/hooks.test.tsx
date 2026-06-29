import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useControlesPorIngreso } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useControlesPorIngreso", () => {
  it("carga la lista de controles de un ingreso", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/controles-medicos/por-ingreso/:ingreso_id`,
        () =>
          HttpResponse.json([
            {
              id: 1,
              ingreso_id: 1,
              fecha_control: "2026-06-16",
              proximo_control: null,
              proximo_agendado: false,
              tiene_licencia: false,
              tipo_licencia: null,
              tipo_reposo: null,
              dias_reposo: null,
              estado_reca: null,
              observaciones: null,
              created_at: "2026-06-16T00:00:00Z",
              updated_at: null,
            },
          ]),
      ),
    );

    const { result } = renderHook(() => useControlesPorIngreso(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBe(1);
  });
});
