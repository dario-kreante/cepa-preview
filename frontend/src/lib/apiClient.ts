import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "@/types/api";
import { tokenStore } from "./tokenStore";

const baseUrl = import.meta.env.VITE_API_BASE_URL;

/**
 * El backend de staging vive en un plan que se duerme por inactividad: el primer
 * request tras un rato tarda ~50s en despertarlo. Damos margen suficiente para el
 * arranque en frío, pero nunca esperamos indefinidamente — sin este tope, un
 * backend caído deja la UI colgada para siempre (no responde ni falla).
 */
export const TIEMPO_MAXIMO_MS = 60_000;

/** El servidor no se pudo contactar (caído, sin red, DNS, CORS o timeout). */
export class ErrorDeConexion extends Error {
  constructor(causa?: unknown) {
    super("No se pudo contactar con el servidor");
    this.name = "ErrorDeConexion";
    this.cause = causa;
  }
}

/**
 * `fetch` que siempre termina: falla pasado `tiempoMaximoMs` y normaliza
 * cualquier fallo de transporte a `ErrorDeConexion`, para que la UI pueda
 * distinguir "el servidor no contesta" de "el servidor contestó que no".
 *
 * El plazo se implementa con una carrera en vez de un `AbortSignal` propio: así
 * respetamos el `signal` que ya trae `init` (React Query cancela sus consultas
 * por ahí) y evitamos mezclar realms de `AbortController`. Contrapartida: la
 * petición vencida sigue viva en segundo plano; su respuesta tardía se descarta.
 */
export async function fetchConTimeout(
  input: RequestInfo | URL,
  init?: RequestInit,
  tiempoMaximoMs: number = TIEMPO_MAXIMO_MS,
): Promise<Response> {
  let temporizador: ReturnType<typeof setTimeout> | undefined;
  const plazo = new Promise<never>((_, rechazar) => {
    temporizador = setTimeout(
      () => rechazar(new ErrorDeConexion(new Error(`sin respuesta en ${tiempoMaximoMs} ms`))),
      tiempoMaximoMs,
    );
  });
  try {
    return await Promise.race([
      globalThis.fetch(input, init).catch((causa) => { throw new ErrorDeConexion(causa); }),
      plazo,
    ]);
  } finally {
    clearTimeout(temporizador);
  }
}

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  const res = await fetchConTimeout(`${baseUrl}/api/v1/auth/refresh`, {
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
    return fetchConTimeout(retried);
  },
};

export const api = createClient<paths>({
  baseUrl,
  // `fetchConTimeout` re-resuelve `globalThis.fetch` en cada llamada (necesario
  // para que MSW intercepte en tests) y garantiza que ninguna petición quede
  // pendiente para siempre si el backend no responde.
  fetch: (...args) => fetchConTimeout(...args),
});
api.use(authMiddleware);
