import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { server } from "@/test/msw/server";
import { useConfirmExtraction, useUploadPdf } from "./hooks";

const BASE = import.meta.env.VITE_API_BASE_URL;

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function pdfFile() {
  return new File([new Uint8Array([37, 80, 68, 70])], "doc.pdf", {
    type: "application/pdf",
  });
}

describe("useUploadPdf", () => {
  it("devuelve los campos extraídos en éxito", async () => {
    server.use(
      http.post(`${BASE}/api/v1/pdf-extract/upload`, () =>
        HttpResponse.json({
          success: true,
          raw_text: "RUT: 11.111.111-1",
          fields: [{ field_key: "rut", value: "11.111.111-1" }],
          error_message: null,
        }),
      ),
    );
    const { result } = renderHook(() => useUploadPdf(), { wrapper });
    result.current.mutate(pdfFile());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.success).toBe(true);
    expect(result.current.data?.fields[0].field_key).toBe("rut");
  });
});

describe("useConfirmExtraction", () => {
  it("traduce el 422 a mensaje de campos faltantes", async () => {
    server.use(
      http.post(`${BASE}/api/v1/pdf-extract/confirm`, () =>
        HttpResponse.json({ detail: { missing_required: ["sexo", "edad"] } }, { status: 422 }),
      ),
    );
    const { result } = renderHook(() => useConfirmExtraction(), { wrapper });
    result.current.mutate({ formKey: "ficha_clinica", fields: [] });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toContain("sexo");
  });
});
