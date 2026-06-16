/**
 * TDD — Anular + Actualizar ISL actions (Task 4)
 *
 * Red phase: dialogs don't exist yet → tests FAIL.
 * Green phase: dialogs are implemented → tests PASS.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { Toaster } from "sonner";
import { AnularLicenciaDialog } from "./AnularLicenciaDialog";
import { IslLicenciaDialog } from "./IslLicenciaDialog";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Minimal valid JWT — role "Coordinacion" (writer)
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function makeWrapper() {
  tokenStore.setAccess(FAKE_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <Toaster />
            {children}
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  }
  return Wrapper;
}

// ─── Anular ──────────────────────────────────────────────────────────────────

describe("AnularLicenciaDialog", () => {
  it("renders the dialog when open=true", async () => {
    const Wrapper = makeWrapper();
    render(
      <AnularLicenciaDialog
        licenciaId={1}
        folio="FOLIO-001"
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: Wrapper },
    );
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("disables confirm button when observaciones is empty", async () => {
    const Wrapper = makeWrapper();
    render(
      <AnularLicenciaDialog
        licenciaId={1}
        folio="FOLIO-001"
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: Wrapper },
    );
    await screen.findByRole("dialog");
    const confirmBtn = screen.getByRole("button", { name: /anular/i });
    // The confirm button (not cancel) should be disabled when textarea is empty
    expect(confirmBtn).toBeDisabled();
  });

  it("sends PATCH /api/v1/licencias/:id/anular with observaciones in the body", async () => {
    const patchSpy = vi.fn();

    server.use(
      http.patch(`${BASE}/api/v1/licencias/:id/anular`, async ({ request, params }) => {
        const body = await request.json();
        patchSpy({ id: params["id"], body });
        return HttpResponse.json({
          id: 1,
          ingreso_id: 5,
          folio_lm: "LM-001",
          tipo_lm: "1",
          tipo_reposo: "total",
          fecha_inicio: "2026-06-01",
          fecha_termino: "2026-06-14",
          fecha_emision: "2026-05-31",
          inicio_reposo: "2026-06-01",
          fin_reposo: "2026-06-14",
          cantidad_dias: 14,
          diagnostico: "Test",
          origen: "sistema",
          envio_isl: "pendiente",
          fecha_envio_isl: null,
          eeag_gaf: null,
          observaciones: "Error en datos",
          anulada: true,
        });
      }),
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({ folio: "FOLIO-001", historial: [], dias_acumulados: 0 }),
      ),
    );

    const onOpenChange = vi.fn();
    const Wrapper = makeWrapper();
    render(
      <AnularLicenciaDialog
        licenciaId={1}
        folio="FOLIO-001"
        open={true}
        onOpenChange={onOpenChange}
      />,
      { wrapper: Wrapper },
    );

    await screen.findByRole("dialog");
    const user = userEvent.setup();

    // Type observaciones
    const textarea = screen.getByRole("textbox", { name: /observaciones/i });
    await user.type(textarea, "Error en datos");

    // Confirm
    const confirmBtn = screen.getByRole("button", { name: /anular/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledOnce();
    });

    const call = patchSpy.mock.calls[0][0];
    expect(call.body).toMatchObject({ observaciones: "Error en datos" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

// ─── ISL ─────────────────────────────────────────────────────────────────────

describe("IslLicenciaDialog", () => {
  it("renders the dialog when open=true", async () => {
    const Wrapper = makeWrapper();
    render(
      <IslLicenciaDialog
        licenciaId={2}
        folio="FOLIO-002"
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: Wrapper },
    );
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("sends PATCH /api/v1/licencias/:id/isl with envio_isl and eeag_gaf", async () => {
    const patchSpy = vi.fn();

    server.use(
      http.patch(`${BASE}/api/v1/licencias/:id/isl`, async ({ request, params }) => {
        const body = await request.json();
        patchSpy({ id: params["id"], body });
        return HttpResponse.json({
          id: 2,
          ingreso_id: 5,
          folio_lm: "LM-002",
          tipo_lm: "1",
          tipo_reposo: "total",
          fecha_inicio: "2026-06-01",
          fecha_termino: "2026-06-14",
          fecha_emision: "2026-05-31",
          inicio_reposo: "2026-06-01",
          fin_reposo: "2026-06-14",
          cantidad_dias: 14,
          diagnostico: "Test",
          origen: "sistema",
          envio_isl: "enviado",
          fecha_envio_isl: null,
          eeag_gaf: 75,
          observaciones: null,
          anulada: false,
        });
      }),
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({ folio: "FOLIO-002", historial: [], dias_acumulados: 0 }),
      ),
    );

    const onOpenChange = vi.fn();
    const Wrapper = makeWrapper();
    render(
      <IslLicenciaDialog
        licenciaId={2}
        folio="FOLIO-002"
        open={true}
        onOpenChange={onOpenChange}
      />,
      { wrapper: Wrapper },
    );

    await screen.findByRole("dialog");
    const user = userEvent.setup();

    // Pick envio_isl (native <select> → query by label)
    const envioSelect = screen.getByLabelText(/estado de envío isl/i);
    await user.selectOptions(envioSelect, "enviado");

    // Fill eeag_gaf
    const eeagInput = screen.getByRole("spinbutton", { name: /gaf\/eeag/i });
    await user.clear(eeagInput);
    await user.type(eeagInput, "75");

    // Submit
    const submitBtn = screen.getByRole("button", { name: /guardar/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledOnce();
    });

    const call = patchSpy.mock.calls[0][0];
    expect(call.body).toMatchObject({ envio_isl: "enviado", eeag_gaf: 75 });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows a validation error when eeag_gaf is out of range", async () => {
    const Wrapper = makeWrapper();
    render(
      <IslLicenciaDialog
        licenciaId={2}
        folio="FOLIO-002"
        open={true}
        onOpenChange={vi.fn()}
      />,
      { wrapper: Wrapper },
    );

    await screen.findByRole("dialog");
    const user = userEvent.setup();

    // Use label-based query since native <select> doesn't get role="combobox"
    const envioSelect = screen.getByLabelText(/estado de envío isl/i);
    await user.selectOptions(envioSelect, "enviado");

    const eeagInput = screen.getByRole("spinbutton", { name: /gaf\/eeag/i });
    await user.clear(eeagInput);
    await user.type(eeagInput, "150"); // Out of range

    const submitBtn = screen.getByRole("button", { name: /guardar/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/entre 1 y 100/i)).toBeInTheDocument();
    });
  });
});
