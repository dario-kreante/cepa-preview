import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import {
  useActividadProfesional,
  useCrearProfesional,
  useImportarDesdeSalutem,
  useProfesionales,
} from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const PROF = {
  id: 7,
  nombre: "Dra. Ana Rojas",
  especialidad: null,
  origen: "SALUTEM",
  activo: true,
  created_at: "2026-10-16T00:00:00Z",
};

describe("useProfesionales", () => {
  it("pide solo activos cuando se indica", async () => {
    let query = "";
    server.use(
      http.get(`${BASE}/api/v1/profesionales`, ({ request }) => {
        query = new URL(request.url).search;
        return HttpResponse.json([PROF]);
      }),
    );
    const { result } = renderHook(() => useProfesionales(true), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].nombre).toBe("Dra. Ana Rojas");
    expect(query).toContain("solo_activos=true");
  });
});

describe("useCrearProfesional", () => {
  it("traduce el 409 a un mensaje claro", async () => {
    server.use(
      http.post(
        `${BASE}/api/v1/profesionales`,
        () => new HttpResponse(JSON.stringify({ detail: "dup" }), { status: 409 }),
      ),
    );
    const { result } = renderHook(() => useCrearProfesional(), { wrapper });
    await expect(
      result.current.mutateAsync({ nombre: "Dra. Ana Rojas" }),
    ).rejects.toThrow("Ya existe un profesional con ese nombre.");
  });
});

describe("useActividadProfesional", () => {
  it("carga la actividad del profesional indicado y no consulta sin id", async () => {
    server.use(
      http.get(`${BASE}/api/v1/profesionales/7/actividad`, () =>
        HttpResponse.json({
          profesional_id: 7,
          total_atenciones: 3,
          atenciones_por_especialidad: [],
          total_controles: 1,
          pacientes_distintos: 2,
          primera_atencion: null,
          ultima_atencion: null,
          ultimas_atenciones: [],
        }),
      ),
    );
    const { result } = renderHook(() => useActividadProfesional(7), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total_atenciones).toBe(3);

    const { result: inactivo } = renderHook(() => useActividadProfesional(null), { wrapper });
    expect(inactivo.current.fetchStatus).toBe("idle");
  });
});

describe("useImportarDesdeSalutem", () => {
  it("devuelve el resultado completo de la importación", async () => {
    server.use(
      http.post(`${BASE}/api/v1/profesionales/importar-salutem`, () =>
        HttpResponse.json({
          creados: 1,
          actualizados: 2,
          adoptados: 3,
          vinculados: 4,
          errores: [],
        }),
      ),
    );
    const { result } = renderHook(() => useImportarDesdeSalutem(), { wrapper });
    const r = await result.current.mutateAsync();
    expect(r).toEqual({ creados: 1, actualizados: 2, adoptados: 3, vinculados: 4, errores: [] });
  });
});
