import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useBuscarCasos, useConsolidado } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const CASO = {
  ingreso_id: 7,
  datos_caso: {
    folio: "F-2026-0007",
    numero_siniestro: "S-1",
    fecha_denuncia: "2026-06-01",
    tipo_denuncia: "DIAT",
    fecha_derivacion: null,
    nombre_completo: "Auditoría Demo",
    rut: "11.111.111-1",
    region: "Maule",
  },
  evaluaciones: {
    fecha_eval_medica: null,
    fecha_eval_psicologica: null,
    fecha_calificacion_reca: null,
    diagnostico_inicial: "Dx A",
    diagnostico_post_reca: null,
  },
  controles: {
    fecha_primera_consulta_medica: null,
    fecha_primera_consulta_psicologica: null,
    reintegro_parcial: false,
    fecha_reintegro_parcial: null,
    reintegro_total: false,
    fecha_reintegro_total: null,
  },
  cierre: {
    alta_medica: false,
    fecha_alta_medica: null,
    alta_psicologica: false,
    fecha_alta_psicologica: null,
    alta_terapeutica: false,
    fecha_alta_terapeutica: null,
    estado_general: "en_tratamiento",
    observaciones: null,
  },
};

describe("useConsolidado", () => {
  it("carga la vista consolidada por ingreso_id", async () => {
    server.use(
      http.get(`${BASE}/api/v1/auditoria/casos/:ingreso_id`, () =>
        HttpResponse.json(CASO),
      ),
    );
    const { result } = renderHook(() => useConsolidado(7), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.datos_caso.folio).toBe("F-2026-0007");
  });
});

describe("useBuscarCasos", () => {
  it("busca casos por filtro cuando enabled", async () => {
    server.use(
      http.get(`${BASE}/api/v1/auditoria/casos`, () =>
        HttpResponse.json([CASO]),
      ),
    );
    const { result } = renderHook(
      () => useBuscarCasos({ rut: "11.111.111-1" }, true),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBe(1);
  });

  it("no consulta cuando enabled=false", async () => {
    const { result } = renderHook(() => useBuscarCasos({}, false), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
  });
});
