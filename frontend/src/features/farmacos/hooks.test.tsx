import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useCrearRegistro, useIndicaciones, useRegistro, useRecetas } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useRecetas", () => {
  it("carga la lista de recetas de un ingreso", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/registro-farmacologico/:ingreso_id/recetas`,
        () =>
          HttpResponse.json([
            {
              id: 1,
              registro_id: 10,
              fecha_emision: "2026-06-01",
              medicamentos: [],
              estado: "emitida",
              created_at: "2026-06-01T00:00:00Z",
            },
          ]),
      ),
    );

    const { result } = renderHook(() => useRecetas(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBe(1);
  });
});

describe("useRegistro", () => {
  it("resuelve null cuando el backend devuelve 404", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/registro-farmacologico/:ingreso_id`,
        () => new HttpResponse(null, { status: 404 }),
      ),
    );

    const { result } = renderHook(() => useRegistro(1), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });
});

describe("useCrearRegistro", () => {
  it("al crear el registro vuelve a pedir las listas del ingreso (esquema, seguimiento…)", async () => {
    let pedidosEsquema = 0;
    server.use(
      http.get(`${BASE}/api/v1/registro-farmacologico/:ingreso_id/esquema`, () => {
        pedidosEsquema += 1;
        return HttpResponse.json([]);
      }),
      http.post(`${BASE}/api/v1/registro-farmacologico`, () =>
        HttpResponse.json(
          {
            id: 1,
            ingreso_id: 7,
            medico_tratante: "Dr. X",
            estado_farmacologico: "activo",
            antecedentes_previos: null,
            tratamiento_previo: null,
            activo: true,
            created_at: "2026-09-25T00:00:00Z",
            updated_at: "2026-09-25T00:00:00Z",
          },
          { status: 201 },
        ),
      ),
    );

    const { result } = renderHook(
      () => ({ esquema: useIndicaciones(7), crear: useCrearRegistro() }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.esquema.isSuccess).toBe(true));
    expect(pedidosEsquema).toBe(1);

    await result.current.crear.mutateAsync({
      ingreso_id: 7,
      medico_tratante: "Dr. X",
      estado_farmacologico: "activo",
    });

    await waitFor(() => expect(pedidosEsquema).toBe(2));
  });
});
