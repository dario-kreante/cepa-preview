import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { AlertsPanel, routeForCaso, tituloAlerta } from "./AlertsPanel";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("tituloAlerta", () => {
  it("nombra las alertas de licencia y receta del control", () => {
    expect(tituloAlerta("licencia_en_control")).toBe("Licencia emitida en control");
    expect(tituloAlerta("receta_en_control")).toBe("Receta emitida en control");
  });

  it("los demás tipos conservan su título derivado", () => {
    expect(tituloAlerta("vencimiento_licencia")).toBe("Vencimiento licencia");
  });
});

describe("AlertsPanel: alertas de licencia del control", () => {
  it("al hacer clic en una alerta de licencia abre el control con sus documentos", async () => {
    tokenStore.setAccess(TOKENS.Coordinacion);
    server.use(
      http.get(`${BASE}/api/v1/alertas`, () =>
        HttpResponse.json([
          {
            id: 1,
            tipo: "licencia_en_control",
            estado: "pendiente",
            caso_id: 5,
            caso_tipo: "control_medico",
            usuario_id: null,
            plazo_objetivo: "2026-10-15T00:00:00Z",
            ventana_dias: 0,
            generada_en: "2026-10-15T19:35:00Z",
            resuelta_en: null,
            email_enviado: false,
          },
        ]),
      ),
      http.get(`${BASE}/api/v1/tareas`, () => HttpResponse.json([])),
      http.get(`${BASE}/api/v1/controles-medicos/5`, () =>
        HttpResponse.json({
          id: 5,
          ingreso_id: 10,
          fecha_control: "2026-10-15",
          medico_tratante: "DRA. PAULA ROJAS",
          tiene_licencia: true,
          resumen_termino_lm: "LM tipo 6 por 30 días",
          origen: "SALUTEM",
        }),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([
          { archivo_id: 1, nombre: "LICENCIA.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" },
        ]),
      ),
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <AlertsPanel />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByText("Licencia emitida en control"));
    const dialogo = await screen.findByRole("dialog");
    expect(await within(dialogo).findByText(/DRA\. PAULA ROJAS/)).toBeInTheDocument();
    expect(within(dialogo).getByText(/LM tipo 6 por 30 días/)).toBeInTheDocument();
    expect(await within(dialogo).findByText("LICENCIA.pdf")).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: /ir a controles/i })).toBeInTheDocument();
  });
});

describe("routeForCaso", () => {
  it("enruta EPT con deep-link por caso_id", () => {
    expect(routeForCaso("ept", 42)).toBe("/ept?caso=42");
  });

  it("EPT sin caso_id cae a la página del módulo", () => {
    expect(routeForCaso("ept", null)).toBe("/ept");
  });

  it("mapea cada caso_tipo a su módulo", () => {
    expect(routeForCaso("control_medico", 1)).toBe("/controles");
    expect(routeForCaso("receta", 1)).toBe("/farmacos");
    expect(routeForCaso("licencia", 1)).toBe("/licencias");
    expect(routeForCaso("oda", 1)).toBe("/ingresos");
    expect(routeForCaso("ingreso", 1)).toBe("/ingresos");
  });

  it("tipo desconocido o nulo cae a /ingresos", () => {
    expect(routeForCaso("otro", 1)).toBe("/ingresos");
    expect(routeForCaso(null, null)).toBe("/ingresos");
  });
});
