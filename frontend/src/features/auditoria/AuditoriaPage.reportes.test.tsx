/** QA-004 (23-11-2026): filtros del reporte de auditoría con listas desplegables. */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { AuditoriaPage } from "./AuditoriaPage";

const BASE = import.meta.env.VITE_API_BASE_URL;
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage() {
  tokenStore.setAccess(AUDITOR_TOKEN);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <AuditoriaPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const opciones = (id: string) =>
  Array.from((screen.getByLabelText(new RegExp(id)) as HTMLSelectElement).options).map((o) => o.textContent);

describe("AuditoriaPage — filtros del reporte (QA-004)", () => {
  it("usa listas desplegables, sin diagnóstico, y envía los filtros elegidos", async () => {
    let cuerpo: Record<string, unknown> | null = null;
    server.use(
      http.get(`${BASE}/api/v1/convenios/para-reportes`, () =>
        HttpResponse.json(["Convenio Colegio Inglés", "Convenio ISL MAULE"]),
      ),
      http.post(`${BASE}/api/v1/auditoria/reportes`, async ({ request }) => {
        cuerpo = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ filtros_aplicados: cuerpo, total: 0, filas: [] });
      }),
    );
    renderPage();
    fireEvent.click(screen.getByTestId("tab-reportes"));

    expect(screen.queryByLabelText(/Diagnóstico/)).not.toBeInTheDocument();
    expect(opciones("Estado")).toEqual(["Todos", "Activo", "Cerrado", "En encuadre", "Derivado"]);
    expect(opciones("Región")).toContain("Biobío");
    expect(opciones("Programa")).toContain("Tratamiento ISL");
    expect(opciones("Tipo de ingreso")).toContain("Consulta espontánea");
    await waitFor(() => expect(opciones("Convenio")).toContain("Convenio ISL MAULE"));
    expect(screen.getByTestId("btn-descargar")).toHaveTextContent("Excel");

    fireEvent.change(screen.getByLabelText(/Desde/), { target: { value: "2026-07-01" } });
    fireEvent.change(screen.getByLabelText(/Hasta/), { target: { value: "2026-07-31" } });
    fireEvent.change(screen.getByLabelText(/Región/), { target: { value: "Biobío" } });
    fireEvent.change(screen.getByLabelText(/Convenio/), { target: { value: "Convenio ISL MAULE" } });
    fireEvent.click(screen.getByTestId("btn-generar"));

    await waitFor(() => expect(cuerpo).not.toBeNull());
    expect(cuerpo).toMatchObject({ region: "Biobío", convenio: "Convenio ISL MAULE", estado_caso: null });
  });
});
