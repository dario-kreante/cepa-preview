/**
 * TDD — AltaLicenciaDialog
 *
 * Red test: submitting with fecha_termino < fecha_inicio must:
 *   1. Show the date-coherence validation error.
 *   2. NOT call the POST /api/v1/licencias endpoint.
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
import { AltaLicenciaDialog } from "./AltaLicenciaDialog";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Minimal valid JWT — role "Coordinacion" (writer)
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderDialog(props: Partial<Parameters<typeof AltaLicenciaDialog>[0]> = {}) {
  tokenStore.setAccess(FAKE_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const onOpenChange = vi.fn();
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <AltaLicenciaDialog
            folio="FOLIO-001"
            ingresoId={5}
            open={true}
            onOpenChange={onOpenChange}
            {...props}
          />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe("AltaLicenciaDialog", () => {
  it("renders the dialog when open=true", async () => {
    renderDialog();
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("shows date-coherence error and does NOT call the API when fecha_termino < fecha_inicio", async () => {
    const postSpy = vi.fn();

    server.use(
      http.post(`${BASE}/api/v1/licencias`, () => {
        postSpy();
        return HttpResponse.json({ id: 99 }, { status: 201 });
      }),
    );

    renderDialog();
    const user = userEvent.setup();

    // Wait for the dialog to fully render
    await screen.findByRole("dialog");

    // Fill required fields — ingresoId is pre-filled (prop)
    // tipo_lm
    const tipoLmSelect = screen.getByLabelText(/tipo de licencia/i);
    await user.selectOptions(tipoLmSelect, "1");

    // tipo_reposo
    const tipoReposoSelect = screen.getByLabelText(/tipo de reposo/i);
    await user.selectOptions(tipoReposoSelect, "total");

    // origen
    const origenSelect = screen.getByLabelText(/origen/i);
    await user.selectOptions(origenSelect, "sistema");

    // Set fecha_inicio AFTER fecha_termino (incoherent)
    const fechaInicioInput = screen.getByLabelText(/fecha inicio/i);
    await user.clear(fechaInicioInput);
    await user.type(fechaInicioInput, "2026-06-15");

    const fechaTerminoInput = screen.getByLabelText(/fecha término/i);
    await user.clear(fechaTerminoInput);
    await user.type(fechaTerminoInput, "2026-06-10"); // BEFORE inicio → invalid

    // fecha_emision
    const fechaEmisionInput = screen.getByLabelText(/fecha emisión/i);
    await user.clear(fechaEmisionInput);
    await user.type(fechaEmisionInput, "2026-06-14");

    // inicio_reposo
    const inicioReposoInput = screen.getByLabelText(/inicio reposo/i);
    await user.clear(inicioReposoInput);
    await user.type(inicioReposoInput, "2026-06-15");

    // fin_reposo
    const finReposoInput = screen.getByLabelText(/fin reposo/i);
    await user.clear(finReposoInput);
    await user.type(finReposoInput, "2026-06-20");

    // cantidad_dias
    const cantidadDiasInput = screen.getByLabelText(/cantidad de días/i);
    await user.clear(cantidadDiasInput);
    await user.type(cantidadDiasInput, "5");

    // diagnostico
    const diagnosticoInput = screen.getByLabelText(/diagnóstico/i);
    await user.clear(diagnosticoInput);
    await user.type(diagnosticoInput, "Lumbalgia aguda");

    // Submit
    const submitBtn = screen.getByRole("button", { name: /registrar licencia/i });
    await user.click(submitBtn);

    // Should show the date-coherence error
    await waitFor(() => {
      expect(
        screen.getByText(/fecha de término debe ser igual o posterior/i),
      ).toBeInTheDocument();
    });

    // API must NOT have been called
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("calls POST /api/v1/licencias with valid data and closes dialog on success", async () => {
    const postSpy = vi.fn();

    server.use(
      http.post(`${BASE}/api/v1/licencias`, async ({ request }) => {
        const body = await request.json();
        postSpy(body);
        return HttpResponse.json(
          {
            id: 42,
            ingreso_id: 5,
            folio_lm: null,
            tipo_lm: "1",
            tipo_reposo: "total",
            fecha_inicio: "2026-06-01",
            fecha_termino: "2026-06-14",
            fecha_emision: "2026-05-31",
            inicio_reposo: "2026-06-01",
            fin_reposo: "2026-06-14",
            cantidad_dias: 14,
            diagnostico: "Lumbalgia aguda",
            origen: "sistema",
            envio_isl: "pendiente",
            fecha_envio_isl: null,
            eeag_gaf: null,
            observaciones: null,
            anulada: false,
          },
          { status: 201 },
        );
      }),
      // invalidation re-fetch
      http.get(`${BASE}/api/v1/licencias/folio/:folio`, () =>
        HttpResponse.json({ folio: "FOLIO-001", historial: [], dias_acumulados: 0 }),
      ),
    );

    const { onOpenChange } = renderDialog();
    const user = userEvent.setup();

    await screen.findByRole("dialog");

    // Fill valid coherent dates
    const tipoLmSelect = screen.getByLabelText(/tipo de licencia/i);
    await user.selectOptions(tipoLmSelect, "1");

    const tipoReposoSelect = screen.getByLabelText(/tipo de reposo/i);
    await user.selectOptions(tipoReposoSelect, "total");

    const origenSelect = screen.getByLabelText(/origen/i);
    await user.selectOptions(origenSelect, "sistema");

    const fechaInicioInput = screen.getByLabelText(/fecha inicio/i);
    await user.clear(fechaInicioInput);
    await user.type(fechaInicioInput, "2026-06-01");

    const fechaTerminoInput = screen.getByLabelText(/fecha término/i);
    await user.clear(fechaTerminoInput);
    await user.type(fechaTerminoInput, "2026-06-14");

    const fechaEmisionInput = screen.getByLabelText(/fecha emisión/i);
    await user.clear(fechaEmisionInput);
    await user.type(fechaEmisionInput, "2026-05-31");

    const inicioReposoInput = screen.getByLabelText(/inicio reposo/i);
    await user.clear(inicioReposoInput);
    await user.type(inicioReposoInput, "2026-06-01");

    const finReposoInput = screen.getByLabelText(/fin reposo/i);
    await user.clear(finReposoInput);
    await user.type(finReposoInput, "2026-06-14");

    const cantidadDiasInput = screen.getByLabelText(/cantidad de días/i);
    await user.clear(cantidadDiasInput);
    await user.type(cantidadDiasInput, "14");

    const diagnosticoInput = screen.getByLabelText(/diagnóstico/i);
    await user.clear(diagnosticoInput);
    await user.type(diagnosticoInput, "Lumbalgia aguda");

    const submitBtn = screen.getByRole("button", { name: /registrar licencia/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledOnce();
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    const sentBody = postSpy.mock.calls[0][0];
    expect(sentBody.ingreso_id).toBe(5);
    expect(sentBody.tipo_lm).toBe("1");
    expect(sentBody.tipo_reposo).toBe("total");
  });
});
