import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import {
  rangoFechas,
  useDisponibilidad,
  useGestiones,
  usePacientesPorCitar,
} from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const RESPUESTA = {
  profesional_id: 5,
  desde: "2026-10-14",
  hasta: "2026-10-23",
  por_dia: [],
  feriados: [],
  pacientes: [],
};

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

describe("usePacientesPorCitar", () => {
  it("envía profesional_id y, en dos semanas, no manda fechas", async () => {
    let url: URL | null = null;
    server.use(
      http.get(`${BASE}/api/v1/pacientes-por-citar`, ({ request }) => {
        url = new URL(request.url);
        return HttpResponse.json(RESPUESTA);
      }),
    );
    const { result } = renderHook(() => usePacientesPorCitar(5, "dos_semanas"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(url!.searchParams.get("profesional_id")).toBe("5");
    expect(url!.searchParams.has("desde")).toBe(false);
    expect(url!.searchParams.has("hasta")).toBe(false);
  });

  it("manda desde/hasta cuando el rango es una semana", async () => {
    let url: URL | null = null;
    server.use(
      http.get(`${BASE}/api/v1/pacientes-por-citar`, ({ request }) => {
        url = new URL(request.url);
        return HttpResponse.json(RESPUESTA);
      }),
    );
    const { result } = renderHook(() => usePacientesPorCitar(5, "semana"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(url!.searchParams.get("desde")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(url!.searchParams.get("hasta")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("no consulta cuando el profesional es null", () => {
    const { result } = renderHook(() => usePacientesPorCitar(null, "semana"), {
      wrapper,
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useGestiones", () => {
  it("no consulta cuando pacienteId es null", () => {
    const { result } = renderHook(() => useGestiones(null), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("rangoFechas", () => {
  it("semana: de hoy al viernes de esta semana", () => {
    expect(rangoFechas("semana", new Date(2026, 9, 14))).toEqual({
      desde: "2026-10-14",
      hasta: "2026-10-16",
    });
  });

  it("semana en fin de semana: al viernes siguiente", () => {
    expect(rangoFechas("semana", new Date(2026, 9, 17))).toEqual({
      desde: "2026-10-17",
      hasta: "2026-10-23",
    });
  });

  it("mes: hasta el último día del mes", () => {
    expect(rangoFechas("mes", new Date(2026, 9, 14))).toEqual({
      desde: "2026-10-14",
      hasta: "2026-10-31",
    });
  });

  it("dos semanas: sin fechas (default del backend)", () => {
    expect(rangoFechas("dos_semanas", new Date(2026, 9, 14))).toEqual({});
  });
});
