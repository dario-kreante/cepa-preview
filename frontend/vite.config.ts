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
      },
    } satisfies VitestConfigExport
  ),
});
