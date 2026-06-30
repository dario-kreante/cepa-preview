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

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
