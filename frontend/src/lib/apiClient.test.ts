import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { api } from "./apiClient";
import { tokenStore } from "./tokenStore";

const BASE = import.meta.env.VITE_API_BASE_URL;
let refreshCalls = 0;

const server = setupServer(
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

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => { refreshCalls = 0; tokenStore.clear(); });

describe("apiClient", () => {
  it("ante 401 refresca una vez y reintenta con el nuevo token", async () => {
    tokenStore.setAccess("stale");
    tokenStore.setRefresh("r");
    const { response } = await api.GET("/api/v1/ingresos", {});
    expect(refreshCalls).toBe(1);
    expect(response.status).toBe(200);
    expect(tokenStore.getAccess()).toBe("good");
  });
});
