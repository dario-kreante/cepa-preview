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

const authMiddleware: Middleware = {
  async onRequest(options) {
    const token = tokenStore.getAccess();
    if (token) options.request.headers.set("authorization", `Bearer ${token}`);
    return options.request;
  },
  async onResponse(options) {
    const { request, response } = options;
    if (response.status !== 401) return response;
    if (request.url.endsWith("/api/v1/auth/refresh")) return response;
    refreshing ??= doRefresh().finally(() => { refreshing = null; });
    const ok = await refreshing;
    if (!ok) return response;
    const retried = new Request(request.url, {
      method: request.method,
      headers: new Headers(request.headers),
      body: request.body,
      mode: request.mode,
      credentials: request.credentials,
      cache: request.cache,
      redirect: request.redirect,
      referrer: request.referrer,
      referrerPolicy: request.referrerPolicy,
      integrity: request.integrity,
    });
    retried.headers.set("authorization", `Bearer ${tokenStore.getAccess()}`);
    return fetch(retried);
  },
};

export const api = createClient<paths>({ baseUrl });
api.use(authMiddleware);
