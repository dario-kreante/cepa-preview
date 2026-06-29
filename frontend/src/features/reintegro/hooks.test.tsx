import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useCaso, useCasosPorIngreso, useReca } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const CASO = {
  id: 1,
  ingreso_id: 10,
  rut: "11.111.111-1",
  nombre: "Paciente Demo",
  tipo_derivacion: "DIEP",
  fecha_caso: "2026-06-20",
  sexo: "F",
  edad: 40,
  region: "Maule",
  comuna: null,
  rubro_empleador: null,
  estado_reintegro: "pendiente",
  fecha_reintegro: null,
  remitido_isl: false,
  alta_medica: false,
  fecha_alta_medica: null,
  alta_psicologica: false,
  fecha_alta_psico: null,
  tipo_alta: null,
  observaciones: null,
};

describe("useCasosPorIngreso", () => {
  it("lista los casos de un ingreso", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reintegros`, () => HttpResponse.json([CASO])),
    );
    const { result } = renderHook(() => useCasosPorIngreso(10), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBe(1);
    expect(result.current.data?.[0].id).toBe(1);
  });
});

describe("useCaso", () => {
  it("carga un caso por id", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reintegros/:caso_id`, () =>
        HttpResponse.json(CASO),
      ),
    );
    const { result } = renderHook(() => useCaso(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.nombre).toBe("Paciente Demo");
  });
});

describe("useReca", () => {
  it("resuelve a null cuando el servidor devuelve 404", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/reintegros/:caso_id/reca`,
        () => new HttpResponse(null, { status: 404 }),
      ),
    );
    const { result } = renderHook(() => useReca(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });
});
