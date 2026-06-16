import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useAlertas, useTareas } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useAlertas", () => {
  it("carga la lista de alertas", async () => {
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([
          {
            id: 1,
            tipo: "vencimiento_lm",
            estado: "pendiente",
            caso_id: 10,
            caso_tipo: "lm",
            usuario_id: null,
            plazo_objetivo: "2026-07-01T00:00:00Z",
            ventana_dias: 5,
            generada_en: "2026-06-01T00:00:00Z",
            resuelta_en: null,
            email_enviado: false,
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useAlertas(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBe(1);
    expect(result.current.data?.[0].tipo).toBe("vencimiento_lm");
  });
});

describe("useTareas", () => {
  it("carga la lista de tareas", async () => {
    server.use(
      http.get(`${BASE}/api/v1/tareas`, () =>
        HttpResponse.json([
          {
            id: 1,
            titulo: "Revisar LM",
            descripcion: null,
            estado: "pendiente",
            tipo_tarea: "revision",
            usuario_id: 2,
            caso_id: 10,
            caso_tipo: "lm",
            creada_en: "2026-06-01T00:00:00Z",
            completada_en: null,
            completada_por: null,
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useTareas(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBe(1);
    expect(result.current.data?.[0].titulo).toBe("Revisar LM");
  });
});
