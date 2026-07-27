import { beforeEach, describe, expect, it } from "vitest";
import { delay, http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { api, ErrorDeConexion, fetchConTimeout } from "./apiClient";
import { tokenStore } from "./tokenStore";

const BASE = import.meta.env.VITE_API_BASE_URL;
let refreshCalls = 0;

beforeEach(() => {
  refreshCalls = 0;
  tokenStore.clear();
  server.use(
    http.get(`${BASE}/api/v1/ingresos`, ({ request }) => {
      const auth = request.headers.get("authorization");
      if (auth === "Bearer good") return HttpResponse.json([]);
      return new HttpResponse(null, { status: 401 });
    }),
    http.post(`${BASE}/api/v1/auth/refresh`, async () => {
      refreshCalls += 1;
      return HttpResponse.json({ access_token: "good", token_type: "bearer" });
    }),
  );
});

describe("apiClient", () => {
  it("ante 401 refresca una vez y reintenta con el nuevo token", async () => {
    tokenStore.setAccess("stale");
    tokenStore.setRefresh("r");
    const { response } = await api.GET("/api/v1/ingresos", {});
    expect(refreshCalls).toBe(1);
    expect(response.status).toBe(200);
    expect(tokenStore.getAccess()).toBe("good");
  });

  it("ante 401 en un POST, reintenta con el MISMO body y el nuevo token", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${BASE}/api/v1/ingresos`, async ({ request }) => {
        const auth = request.headers.get("authorization");
        bodies.push(await request.json());
        if (auth === "Bearer good") return HttpResponse.json({ ok: true }, { status: 201 });
        return new HttpResponse(null, { status: 401 });
      }),
    );
    tokenStore.setAccess("stale");
    tokenStore.setRefresh("r");
    const payload = { rut: "11.111.111-1", nombre: "Ana" };
    const { response } = await api.POST("/api/v1/ingresos", { body: payload as any });
    expect(response.status).toBe(201);
    // the retried (authorized) call must have received the same body
    expect(bodies.at(-1)).toEqual(payload);
  });
});

describe("apiClient — servidor caído o inalcanzable", () => {
  it("aborta la petición si el servidor no responde dentro del plazo", async () => {
    server.use(http.get(`${BASE}/api/v1/ingresos`, async () => { await delay("infinite"); }));
    await expect(fetchConTimeout(`${BASE}/api/v1/ingresos`, {}, 30)).rejects.toBeInstanceOf(
      ErrorDeConexion,
    );
  });

  it("traduce un fallo de red a ErrorDeConexion", async () => {
    server.use(http.get(`${BASE}/api/v1/ingresos`, () => HttpResponse.error()));
    await expect(fetchConTimeout(`${BASE}/api/v1/ingresos`)).rejects.toBeInstanceOf(
      ErrorDeConexion,
    );
  });

  it("el cliente tipado propaga ErrorDeConexion en vez de quedarse colgado", async () => {
    server.use(http.get(`${BASE}/api/v1/ingresos`, () => HttpResponse.error()));
    await expect(api.GET("/api/v1/ingresos", {})).rejects.toBeInstanceOf(ErrorDeConexion);
  });
});
