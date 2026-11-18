import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useCambiarEstadoIngreso } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("useCambiarEstadoIngreso (QA-011)", () => {
  it("al cerrar refresca ficha, dashboard (activos) y alertas", async () => {
    server.use(
      http.patch(`${BASE}/api/v1/ingresos/:id/estado`, () =>
        HttpResponse.json({ id: 55, estado: "cerrado", motivo_cierre: "abandono" }),
      ),
    );
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const invalidadas: unknown[] = [];
    const original = qc.invalidateQueries.bind(qc);
    qc.invalidateQueries = ((f: { queryKey?: unknown }) => {
      invalidadas.push(f?.queryKey);
      return original(f as never);
    }) as typeof qc.invalidateQueries;
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useCambiarEstadoIngreso(7), { wrapper });
    result.current.mutate({ ingresoId: 55, estado: "cerrado", motivoCierre: "abandono" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidadas).toContainEqual(["pacientes", 7, "vista360"]);
    expect(invalidadas).toContainEqual(["dashboard"]);
    expect(invalidadas).toContainEqual(["alertas"]);
  });

  it("traduce el 403 de reabrir sin perfil", async () => {
    server.use(http.patch(`${BASE}/api/v1/ingresos/:id/estado`, () => new HttpResponse(null, { status: 403 })));
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useCambiarEstadoIngreso(7), { wrapper });
    result.current.mutate({ ingresoId: 55, estado: "activo" });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toMatch(/solo de Coordinación/);
  });
});
