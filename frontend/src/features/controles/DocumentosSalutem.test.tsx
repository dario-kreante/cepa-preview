/**
 * Documentos de la biblioteca de SALUTEM unidos a un control.
 *
 * Covers:
 *  1. Lista nombre y fecha de cada documento.
 *  2. "Ver" abre la pestaña en el clic (antes de pedir nada), pide el contenido con la
 *     sesión y le asigna el blob.
 *  3. Con la lista vacía avisa que no hay documentos en la biblioteca.
 *  4. Si SALUTEM no entrega el contenido, cierra la pestaña y muestra el error.
 *  5. Si el navegador bloquea la pestaña, avisa y no pide nada.
 *  6. Un tipo fuera de la lista permitida se descarga, no se abre.
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

function renderizar(props: { controlId: number }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Toaster />
      <DocumentosSalutem {...props} />
    </QueryClientProvider>,
  );
}

describe("DocumentosSalutem", () => {
  const pestana = { location: { href: "" }, close: vi.fn(), opener: "original" as unknown, document: { title: "" } };
  const abrir = vi.fn();

  beforeEach(() => {
    pestana.location.href = "";
    pestana.opener = "original";
    pestana.close.mockReset();
    abrir.mockReset().mockReturnValue(pestana);
    vi.stubGlobal("open", abrir);
    URL.createObjectURL = vi.fn(() => "blob:documento");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lista los documentos del control", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([
          { archivo_id: 1, nombre: "LICENCIA 15 oct.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" },
        ]),
      ),
    );
    renderizar({ controlId: 5 });
    expect(await screen.findByText("LICENCIA 15 oct.pdf")).toBeInTheDocument();
    expect(screen.getByText(/15-10-2026|15\/10\/2026/)).toBeInTheDocument();
  });

  it("Ver abre la pestaña en el clic y luego le asigna el documento", async () => {
    let pedidoAlAbrir: boolean | null = null;
    let pidio = false;
    abrir.mockImplementation(() => {
      pedidoAlAbrir = pidio;
      return pestana;
    });
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "a.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () => {
        pidio = true;
        return new HttpResponse(new Blob(["%PDF-1.6"], { type: "application/pdf" }), {
          headers: { "Content-Type": "application/pdf" },
        });
      }),
    );
    renderizar({ controlId: 5 });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    await waitFor(() => expect(pestana.location.href).toBe("blob:documento"));
    expect(abrir).toHaveBeenCalledWith("", "_blank");
    expect(pedidoAlAbrir).toBe(false); // la pestaña se abrió antes de pedir el contenido
    expect(pestana.opener).toBeNull();
    expect(pestana.close).not.toHaveBeenCalled();
  });

  it("si el navegador bloquea la pestaña avisa y no pide el contenido", async () => {
    abrir.mockReturnValue(null);
    let pidio = false;
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "a.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () => {
        pidio = true;
        return new HttpResponse(new Blob(["x"], { type: "application/pdf" }));
      }),
    );
    renderizar({ controlId: 5 });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    expect(await screen.findByText(/el navegador bloqueó la pestaña nueva/i)).toBeInTheDocument();
    expect(pidio).toBe(false);
  });

  it("un tipo no permitido se descarga y no se abre en la pestaña", async () => {
    const clics: string[] = [];
    const clic = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clics.push(this.download);
    });
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "pagina.html", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () =>
        new HttpResponse(new Blob(["<script>1</script>"], { type: "text/html" }), {
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );
    renderizar({ controlId: 5 });
    await userEvent.click(await screen.findByRole("button", { name: /ver pagina\.html/i }));
    await waitFor(() => expect(clics).toEqual(["pagina.html"]));
    expect(pestana.location.href).toBe("");
    expect(pestana.close).toHaveBeenCalled();
    clic.mockRestore();
  });

  it("sin documentos avisa que la biblioteca está vacía", async () => {
    server.use(http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () => HttpResponse.json([])));
    renderizar({ controlId: 5 });
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
    renderizar({ controlId: 5 });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    expect(await screen.findByText(/no se pudo abrir el documento/i)).toBeInTheDocument();
    expect(pestana.close).toHaveBeenCalled();
    expect(pestana.location.href).toBe("");
  });
});
