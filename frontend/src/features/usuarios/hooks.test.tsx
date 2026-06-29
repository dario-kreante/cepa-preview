import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useUsuarios } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useUsuarios", () => {
  it("lista los usuarios", async () => {
    server.use(
      http.get(`${BASE}/api/v1/usuarios`, () =>
        HttpResponse.json([
          {
            id: 1,
            username: "admin",
            nombre: "Coordinación",
            rol: "Coordinacion",
            activo: true,
            email: null,
            created_at: "2026-06-20T00:00:00Z",
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useUsuarios(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].username).toBe("admin");
  });

  it("propaga error 403 con mensaje claro", async () => {
    server.use(
      http.get(
        `${BASE}/api/v1/usuarios`,
        () => new HttpResponse(null, { status: 403 }),
      ),
    );
    const { result } = renderHook(() => useUsuarios(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
    expect((result.current.error as Error).message).toContain("Coordinación");
  });
});
