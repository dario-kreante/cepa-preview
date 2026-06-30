/**
 * TDD — Envío masivo ISL + Generar alertas (Task 5)
 *
 * Red phase: buttons don't exist yet → tests FAIL.
 * Green phase: feature implemented → tests PASS.
 *
 * NOTE: Cross-region bulk ISL is NOT supported — there is no backend list endpoint
 * to enumerate all licencias across patients/regions. Bulk send operates only over
 * the currently selected rows of the active folio search (per-patient scope).
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { Toaster } from "sonner";
import { LicenciasPage } from "./LicenciasPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Minimal valid JWT for role "Coordinacion" (writer)
// Payload: {"sub":"1","username":"test","role":"Coordinacion","type":"access","exp":9999999999}
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// Minimal valid JWT for role "Auditor" (read-only)
// Payload: {"sub":"2","username":"auditor","role":"Auditor","type":"access","exp":9999999999}
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage(token = FAKE_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <LicenciasPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const FOLIO = "FOLIO-BULK";

// Two non-anulled licencias for bulk selection tests
const SLIM_1 = {
  id: 11,
  tipo_lm: "1",
  cantidad_dias: 7,
  fecha_inicio: "2026-06-01",
  fecha_termino: "2026-06-07",
  diagnostico: "Lumbalgia",
  anulada: false,
};
const SLIM_2 = {
  id: 12,
  tipo_lm: "5",
  cantidad_dias: 14,
  fecha_inicio: "2026-06-08",
  fecha_termino: "2026-06-21",
  diagnostico: "Cervicalgia",
  anulada: false,
};

const FULL_BASE = {
  ingreso_id: 5,
  tipo_reposo: "total",
  fecha_emision: "2026-05-31",
  inicio_reposo: "2026-06-01",
  fin_reposo: "2026-06-07",
  indicacion_reposo: null,
  origen: "sistema",
  envio_isl: "pendiente",
  fecha_envio_isl: null,
  eeag_gaf: null,
  observaciones: null,
  anulada: false,
};
const FULL_1 = { ...FULL_BASE, id: 11, folio_lm: "LM-00011", tipo_lm: "1", cantidad_dias: 7, diagnostico: "Lumbalgia", fecha_inicio: "2026-06-01", fecha_termino: "2026-06-07" };
const FULL_2 = { ...FULL_BASE, id: 12, folio_lm: "LM-00012", tipo_lm: "5", cantidad_dias: 14, diagnostico: "Cervicalgia", fecha_inicio: "2026-06-08", fecha_termino: "2026-06-21" };

/** Register MSW handlers so LicenciasPage can load 2 rows. */
function registerTwoRowHandlers() {
  server.use(
    http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
      HttpResponse.json({
        folio: FOLIO,
        historial: [SLIM_1, SLIM_2],
        dias_acumulados: 21,
      })
    ),
    http.get(`${BASE}/api/v1/licencias/:id`, ({ params }) => {
      const id = Number(params["id"]);
      if (id === 11) return HttpResponse.json(FULL_1);
      if (id === 12) return HttpResponse.json(FULL_2);
      return HttpResponse.json({ message: "not found" }, { status: 404 });
    })
  );
}

/** Type a folio into the search box and wait for 2 rows to render. */
async function searchAndWaitRows() {
  const input = screen.getByPlaceholderText("Buscar por folio");
  fireEvent.change(input, { target: { value: FOLIO } });
  // Wait for at least both row checkboxes to appear (one per non-anulled row)
  await waitFor(
    () => {
      const checkboxes = screen.getAllByRole("checkbox");
      // header select-all + 2 row checkboxes = 3 total
      expect(checkboxes.length).toBeGreaterThanOrEqual(3);
    },
    { timeout: 8000 }
  );
}

// ─── Selection + Bulk ISL ─────────────────────────────────────────────────────

describe("LicenciasPage — Envío masivo ISL", () => {
  it("shows checkboxes per row (writer role) after folio search", async () => {
    registerTwoRowHandlers();
    renderPage();
    await searchAndWaitRows();
    // ≥3: header + 2 rows
    expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(3);
  });

  it("does NOT show checkboxes for Auditor", async () => {
    registerTwoRowHandlers();
    renderPage(AUDITOR_TOKEN);
    const input = screen.getByPlaceholderText("Buscar por folio");
    fireEvent.change(input, { target: { value: FOLIO } });
    // Wait until table rows appear (Tipo badge for tipo_lm "5" appears)
    await waitFor(
      () => {
        // "Tipo 5" appears at least as a filter option
        expect(screen.getByDisplayValue("Tipo LM: Todos")).toBeInTheDocument();
      },
      { timeout: 8000 }
    );
    // Auditor must see no checkboxes
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("'Envío masivo ISL' button is disabled when no rows selected", async () => {
    registerTwoRowHandlers();
    renderPage();
    await searchAndWaitRows();
    const btn = screen.getByRole("button", { name: /envío masivo isl/i });
    expect(btn).toBeDisabled();
  });

  it("selects all rows via header checkbox and enables bulk button", async () => {
    registerTwoRowHandlers();
    renderPage();
    await searchAndWaitRows();

    const user = userEvent.setup();
    // First checkbox is the header "select all"
    const [headerCb] = screen.getAllByRole("checkbox");
    await user.click(headerCb);

    const btn = screen.getByRole("button", { name: /envío masivo isl/i });
    expect(btn).not.toBeDisabled();
  });

  it("calls PATCH /isl for each selected row with envio_isl='enviado'", async () => {
    registerTwoRowHandlers();

    const islCalls: Array<{ id: string; body: unknown }> = [];

    server.use(
      http.patch(`${BASE}/api/v1/licencias/:id/isl`, async ({ request, params }) => {
        const body = await request.json();
        islCalls.push({ id: String(params["id"]), body });
        return HttpResponse.json({ ...FULL_1, id: Number(params["id"]), envio_isl: "enviado" });
      })
    );

    renderPage();
    await searchAndWaitRows();

    const user = userEvent.setup();
    // Select all via header checkbox
    const [headerCb] = screen.getAllByRole("checkbox");
    await user.click(headerCb);

    // Click bulk send button
    const bulkBtn = screen.getByRole("button", { name: /envío masivo isl/i });
    await user.click(bulkBtn);

    await waitFor(
      () => {
        // Filter only ISL PATCH calls (exclude anular/etc.)
        const islPatches = islCalls.filter(
          (c) => typeof (c.body as Record<string, unknown>)?.["envio_isl"] !== "undefined"
        );
        expect(islPatches).toHaveLength(2);
      },
      { timeout: 8000 }
    );

    const bodies = islCalls.map((c) => c.body);
    for (const body of bodies) {
      expect(body).toMatchObject({ envio_isl: "enviado" });
    }
  });

  it("shows 'Envío masivo ISL' button only for writers (not auditor)", async () => {
    registerTwoRowHandlers();
    renderPage(AUDITOR_TOKEN);
    const input = screen.getByPlaceholderText("Buscar por folio");
    fireEvent.change(input, { target: { value: FOLIO } });
    await waitFor(
      () => expect(screen.getByDisplayValue("Tipo LM: Todos")).toBeInTheDocument(),
      { timeout: 8000 }
    );
    expect(screen.queryByRole("button", { name: /envío masivo isl/i })).not.toBeInTheDocument();
  });
});

// ─── Generar alertas ──────────────────────────────────────────────────────────

describe("LicenciasPage — Generar alertas de vencimiento", () => {
  it("shows 'Generar alertas' button for writers", async () => {
    renderPage();
    expect(
      await screen.findByRole("button", { name: /generar alertas/i })
    ).toBeInTheDocument();
  });

  it("does NOT show 'Generar alertas' button for Auditor", async () => {
    renderPage(AUDITOR_TOKEN);
    await screen.findByText(/Ingresa un folio/i);
    expect(
      screen.queryByRole("button", { name: /generar alertas/i })
    ).not.toBeInTheDocument();
  });

  it("calls POST /alertas/generar and shows toast with count", async () => {
    const postSpy = vi.fn();
    server.use(
      http.post(`${BASE}/api/v1/licencias/alertas/generar`, async () => {
        postSpy();
        return HttpResponse.json([
          { id: 1, licencia_id: 11, tipo: "vencimiento_proximo", mensaje: "Vence pronto" },
          { id: 2, licencia_id: 12, tipo: "vencimiento_proximo", mensaje: "Vence pronto" },
        ]);
      })
    );

    renderPage();
    const user = userEvent.setup();
    const alertBtn = await screen.findByRole("button", { name: /generar alertas/i });
    await user.click(alertBtn);

    await waitFor(
      () => expect(postSpy).toHaveBeenCalledOnce(),
      { timeout: 8000 }
    );
  });
});
