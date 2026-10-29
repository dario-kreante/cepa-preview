/**
 * Biblioteca de SALUTEM del paciente (QA-001): Licencias, Fármacos y Controles.
 *
 * Covers:
 *  1. Con relación pide ?relacion= y explica que SALUTEM no informa la carpeta.
 *  2. Sin relación lista todo y marca Licencia / Receta y la atención de origen.
 *  3. Estado vacío por relación.
 *  4. «Ver» pide el contenido por el endpoint del paciente.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { DocumentosSalutemPaciente } from "./DocumentosSalutem";

const BASE = import.meta.env.VITE_API_BASE_URL;
const URL_DOCS = `${BASE}/api/v1/pacientes/9/documentos-salutem`;

const DOC = {
  archivo_id: 1,
  nombre: "LM 15 oct.pdf",
  tipo: "documento",
  fecha_creacion: "2026-10-15T16:29:00",
  licencia: true,
  receta: false,
  fecha_atencion: "2026-10-15",
};

function renderizar(props: Parameters<typeof DocumentosSalutemPaciente>[0]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <DocumentosSalutemPaciente {...props} />
    </QueryClientProvider>,
  );
}

describe("DocumentosSalutemPaciente", () => {
  const pestana = { location: { href: "" }, close: vi.fn(), opener: "original" as unknown, document: { title: "" } };

  beforeEach(() => {
    vi.stubGlobal("open", vi.fn(() => pestana));
    URL.createObjectURL = vi.fn(() => "blob:documento");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("con relación pide solo esos documentos y aclara que no es la carpeta", async () => {
    let relacion: string | null = null;
    server.use(
      http.get(URL_DOCS, ({ request }) => {
        relacion = new URL(request.url).searchParams.get("relacion");
        return HttpResponse.json([DOC]);
      }),
    );
    renderizar({ pacienteId: 9, relacion: "licencia", titulo: "Documentos de licencias en SALUTEM" });
    expect(await screen.findByText("LM 15 oct.pdf")).toBeInTheDocument();
    expect(relacion).toBe("licencia");
    expect(screen.getByRole("heading", { name: "Documentos de licencias en SALUTEM" })).toBeInTheDocument();
    expect(screen.getByText(/no informa en qué carpeta/)).toBeInTheDocument();
    // En el módulo no se repite la marca: todos son de licencia.
    expect(screen.queryByText("Licencia")).not.toBeInTheDocument();
  });

  it("sin relación lista toda la biblioteca con la relación deducida", async () => {
    let relacion: string | null = "sin pedir";
    server.use(
      http.get(URL_DOCS, ({ request }) => {
        relacion = new URL(request.url).searchParams.get("relacion");
        return HttpResponse.json([
          DOC,
          { ...DOC, archivo_id: 2, nombre: "receta.jpg", tipo: "imagen", licencia: false, receta: true },
          { ...DOC, archivo_id: 3, nombre: "otro.pdf", licencia: false, fecha_atencion: null },
        ]);
      }),
    );
    renderizar({ pacienteId: 9, titulo: "Documentos del paciente en SALUTEM" });
    expect(await screen.findByText("otro.pdf")).toBeInTheDocument();
    expect(relacion).toBeNull();
    expect(screen.getByText("Licencia")).toBeInTheDocument();
    expect(screen.getByText("Receta")).toBeInTheDocument();
    expect(screen.getAllByText("atención 15-10-2026")).toHaveLength(2);
    expect(screen.getByText(/no son documentos de un control/)).toBeInTheDocument();
  });

  it("avisa cuando no hay recetas", async () => {
    server.use(http.get(URL_DOCS, () => HttpResponse.json([])));
    renderizar({ pacienteId: 9, relacion: "receta", titulo: "Recetas en SALUTEM" });
    expect(await screen.findByText("Sin recetas en SALUTEM para este paciente.")).toBeInTheDocument();
  });

  it("Ver pide el documento por el endpoint del paciente", async () => {
    let pidio = false;
    server.use(
      http.get(URL_DOCS, () => HttpResponse.json([DOC])),
      http.get(`${URL_DOCS}/1/contenido`, () => {
        pidio = true;
        return new HttpResponse("%PDF-1.6", { headers: { "Content-Type": "application/pdf" } });
      }),
    );
    renderizar({ pacienteId: 9, relacion: "licencia", titulo: "Documentos de licencias en SALUTEM" });
    await userEvent.click(await screen.findByRole("button", { name: "Ver LM 15 oct.pdf" }));
    await waitFor(() => expect(pidio).toBe(true));
    await waitFor(() => expect(pestana.location.href).toBe("blob:documento"));
  });
});
