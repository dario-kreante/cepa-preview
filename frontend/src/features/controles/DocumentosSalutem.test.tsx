/**
 * Documentos de la biblioteca de SALUTEM unidos a un control.
 *
 * Covers:
 *  1. Lista nombre y fecha de cada documento.
 *  2. "Ver" pide el contenido con la sesión y lo abre en una pestaña nueva.
 *  3. Sin documentos y con licencia: avisa que no hay documentos en la biblioteca.
 *  4. Si SALUTEM no entrega el contenido, muestra el error.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { DocumentosSalutem } from "./DocumentosSalutem";

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderizar(props: { controlId: number; tieneLicencia: boolean }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Toaster />
      <DocumentosSalutem {...props} />
    </QueryClientProvider>,
  );
}

describe("DocumentosSalutem", () => {
  const abrir = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("open", abrir);
    URL.createObjectURL = vi.fn(() => "blob:documento");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    abrir.mockReset();
  });

  it("lista los documentos del control", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([
          { archivo_id: 1, nombre: "LICENCIA 15 oct.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" },
        ]),
      ),
    );
    renderizar({ controlId: 5, tieneLicencia: true });
    expect(await screen.findByText("LICENCIA 15 oct.pdf")).toBeInTheDocument();
    expect(screen.getByText(/15-10-2026|15\/10\/2026/)).toBeInTheDocument();
  });

  it("Ver abre el documento en una pestaña nueva", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "a.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () =>
        new HttpResponse(new Blob(["%PDF-1.6"], { type: "application/pdf" }), {
          headers: { "Content-Type": "application/pdf" },
        }),
      ),
    );
    renderizar({ controlId: 5, tieneLicencia: false });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    await waitFor(() => expect(abrir).toHaveBeenCalledWith("blob:documento", "_blank", "noopener"));
  });

  it("sin documentos y con licencia avisa que la biblioteca está vacía", async () => {
    server.use(http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () => HttpResponse.json([])));
    renderizar({ controlId: 5, tieneLicencia: true });
    expect(await screen.findByText(/sin documentos en la biblioteca de salutem/i)).toBeInTheDocument();
  });

  it("si SALUTEM no entrega el contenido muestra el error", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "a.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () =>
        HttpResponse.json({ detail: "SALUTEM no entregó el contenido del archivo" }, { status: 404 }),
      ),
    );
    renderizar({ controlId: 5, tieneLicencia: false });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    expect(await screen.findByText(/no se pudo abrir el documento/i)).toBeInTheDocument();
    expect(abrir).not.toHaveBeenCalled();
  });
});
