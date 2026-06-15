import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "@/types/api";
import { tokenStore } from "./tokenStore";

const baseUrl = import.meta.env.VITE_API_BASE_URL;

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) { tokenStore.clear(); return false; }
  const data = (await res.json()) as { access_token: string };
  tokenStore.setAccess(data.access_token);
  return true;
}

const pending = new Map<string, Request>();

const authMiddleware: Middleware = {
  async onRequest(options) {
    const token = tokenStore.getAccess();
    if (token) options.request.headers.set("authorization", `Bearer ${token}`);
    // Clone BEFORE openapi-fetch consumes the body so we can replay it on retry.
    pending.set(options.id, options.request.clone());
    return options.request;
  },
  async onResponse(options) {
    const original = pending.get(options.id);
    pending.delete(options.id); // delete on ALL paths to avoid Map leak
    if (options.response.status !== 401) return options.response;
    if (options.request.url.endsWith("/api/v1/auth/refresh")) return options.response;
    refreshing ??= doRefresh().finally(() => { refreshing = null; });
    const ok = await refreshing;
    if (!ok || !original) return options.response;
    // Build a fresh Request from the pre-consume clone with the updated token.
    const retried = new Request(original, { headers: new Headers(original.headers) });
    retried.headers.set("authorization", `Bearer ${tokenStore.getAccess()}`);
    return fetch(retried);
  },
};

export const api = createClient<paths>({
  baseUrl,
  fetch: (...args) => globalThis.fetch(...args),
});
api.use(authMiddleware);
