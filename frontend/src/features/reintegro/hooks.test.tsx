import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import {
  useCaso,
  useCasosPorIngreso,
  useCrearReca,
  useReca,
  useRegistrarCierre,
  useRegistrarSolicitudReca,
} from "./hooks";

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
  razon_social: null,
  tipo_trabajador: null,
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

describe("useRegistrarCierre", () => {
  it("invalida el caso, los casos activos del paciente, los duplicados y los del ingreso", async () => {
    server.use(
      http.patch(`${BASE}/api/v1/reintegros/1/cierre`, () =>
        HttpResponse.json({ ...CASO, estado_reintegro: "total" }),
      ),
    );
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const spy = vi.spyOn(qc, "invalidateQueries");
    const w = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useRegistrarCierre(), { wrapper: w });
    result.current.mutate({ casoId: 1, body: { estado_reintegro: "total", remitido_isl: false, alta_medica: false, alta_psicologica: false } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const keys = spy.mock.calls.map((c) => JSON.stringify((c[0] as { queryKey: unknown }).queryKey));
    expect(keys).toContain(JSON.stringify(["reintegro", 1]));
    expect(keys).toContain(JSON.stringify(["reintegro", "paciente"]));
    expect(keys).toContain(JSON.stringify(["reintegro", "duplicados"]));
    expect(keys).toContain(JSON.stringify(["reintegro", "ingreso", 10]));
  });
});

describe("invalidaciones que refrescan el estado de RECA y las alertas (QA-003)", () => {
  function conCliente() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const spy = vi.spyOn(qc, "invalidateQueries");
    const claves = () => spy.mock.calls.map((c) => (c[0] as { queryKey: unknown[] }).queryKey);
    const w = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    return { claves, w };
  }

  it("registrar la RECA invalida el caso y las alertas", async () => {
    server.use(http.post(`${BASE}/api/v1/reintegros/1/reca`, () => HttpResponse.json({ id: 1 }, { status: 201 })));
    const { claves, w } = conCliente();
    const { result } = renderHook(() => useCrearReca(), { wrapper: w });
    await act(async () => {
      await result.current.mutateAsync({ casoId: 1, body: {} as never });
    });
    expect(claves()).toContainEqual(["reintegro", 1]);
    expect(claves()).toContainEqual(["alertas"]);
  });

  it("registrar el cierre invalida las alertas", async () => {
    server.use(http.patch(`${BASE}/api/v1/reintegros/1/cierre`, () => HttpResponse.json(CASO)));
    const { claves, w } = conCliente();
    const { result } = renderHook(() => useRegistrarCierre(), { wrapper: w });
    await act(async () => {
      await result.current.mutateAsync({ casoId: 1, body: {} as never });
    });
    expect(claves()).toContainEqual(["alertas"]);
  });

  it("registrar la solicitud invalida el caso y las alertas", async () => {
    server.use(http.patch(`${BASE}/api/v1/reintegros/1/solicitud-reca`, () => HttpResponse.json(CASO)));
    const { claves, w } = conCliente();
    const { result } = renderHook(() => useRegistrarSolicitudReca(), { wrapper: w });
    await act(async () => {
      await result.current.mutateAsync({ casoId: 1, fecha: "2026-06-25" });
    });
    expect(claves()).toContainEqual(["reintegro", 1]);
    expect(claves()).toContainEqual(["alertas"]);
  });
});
