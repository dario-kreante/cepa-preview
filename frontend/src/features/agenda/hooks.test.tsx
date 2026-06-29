import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useCitas, useDisponibilidad, usePropuestas } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useDisponibilidad", () => {
  it("lista la disponibilidad de un profesional", async () => {
    server.use(
      http.get(`${BASE}/api/v1/disponibilidad-profesional/:id`, () =>
        HttpResponse.json([
          {
            id: 1,
            profesional_id: 5,
            dia_semana: 1,
            cupo_diario: 4,
            activo: true,
            created_at: "2026-06-20T00:00:00Z",
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useDisponibilidad(5), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].cupo_diario).toBe(4);
  });
});

describe("usePropuestas", () => {
  it("lista propuestas del profesional", async () => {
    server.use(
      http.get(`${BASE}/api/v1/propuestas-agenda`, () =>
        HttpResponse.json([
          {
            id: 9,
            profesional_id: 5,
            tipo: "semanal",
            fecha_inicio: "2026-06-22",
            fecha_fin: "2026-06-26",
            estado: "borrador",
            generado_por: "admin",
            created_at: "2026-06-22T00:00:00Z",
          },
        ]),
      ),
    );
    const { result } = renderHook(() => usePropuestas(5), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].id).toBe(9);
  });
});

describe("useCitas", () => {
  it("no consulta cuando propuestaId es null", () => {
    const { result } = renderHook(() => useCitas(null), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
  });
});
