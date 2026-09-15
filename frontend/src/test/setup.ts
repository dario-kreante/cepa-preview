import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { configure } from "@testing-library/dom";
import { server } from "./msw/server";

// `waitFor` defaults to a 1s timeout. When the full suite runs serially under
// resource contention, async UI settles slower and that 1s budget is easily
// exhausted, surfacing as intermittent timeouts. Give async utilities more
// headroom; tests still resolve as soon as the expectation passes.
configure({ asyncUtilTimeout: 5000 });

// ResizeObserver is used by Radix UI components (Select, Dialog, etc.) but is
// not available in jsdom. Provide a no-op mock so component tests don't crash.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// Node 26 expone un `localStorage` propio que queda `undefined` salvo que se arranque con
// `--localstorage-file`, y que tiene precedencia sobre el que provee jsdom. El resultado es que
// `tokenStore` revienta con "Cannot read properties of undefined (reading 'removeItem')" en
// tests que en el navegador funcionan sin problema. Se instala un reemplazo en memoria cuando
// el global no sirve.
if (typeof globalThis.localStorage === "undefined" || globalThis.localStorage === null) {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
      key: (i: number) => [...store.keys()][i] ?? null,
      get length() {
        return store.size;
      },
    },
  });
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
