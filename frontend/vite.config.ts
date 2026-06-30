import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import type { InlineConfig } from "vitest/node";

interface VitestConfigExport {
  test?: InlineConfig;
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  ...(
    {
      test: {
        environment: "jsdom",
        globals: true,
        setupFiles: ["./src/test/setup.ts"],
        css: true,
        exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
        // Component tests drive Radix dialogs through userEvent (key-by-key
        // typing) over MSW. Running the whole suite serially (~41 files) under
        // resource contention can push a single test past the 5s default, even
        // though each passes comfortably in isolation. Raise the ceiling so
        // these are not flagged as flaky timeouts.
        testTimeout: 20000,
        hookTimeout: 20000,
      },
    } satisfies VitestConfigExport
  ),
});
