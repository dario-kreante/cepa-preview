import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { usePublicada } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("usePublicada", () => {
  it("carga la versión publicada de un formulario", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/form-definitions/:form_key/published`,
        () =>
          HttpResponse.json({
            id: 3,
            form_def_id: 1,
            version_num: 2,
            status: "published",
            published_at: "2026-06-25T00:00:00Z",
            created_by: "admin",
            created_at: "2026-06-25T00:00:00Z",
            fields: [
              {
                id: 1,
                field_key: "rut",
                label: "RUT",
                field_type: "text",
                required: true,
                system_locked: true,
                domain_values: null,
                display_order: 0,
                active: true,
              },
            ],
          }),
      ),
    );
    const { result } = renderHook(() => usePublicada("ficha_clinica"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.version_num).toBe(2);
    expect(result.current.data?.fields[0].field_key).toBe("rut");
  });

  it("resuelve a null cuando no hay versión publicada (404)", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/form-definitions/:form_key/published`,
        () => new HttpResponse(null, { status: 404 }),
      ),
    );
    const { result } = renderHook(() => usePublicada("nuevo_form"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });
});
