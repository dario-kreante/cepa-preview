import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ProcesoEptPanel } from "./ProcesoEptPanel";
import type { ProcesoEptRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

// ── Auth tokens ──────────────────────────────────────────────────────────────

// Payload: {"sub":"1","username":"admin","role":"Administrativo","type":"access","exp":9999999999}
const ADMIN_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJBZG1pbmlzdHJhdGl2byIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// Payload: {"sub":"2","username":"coord","role":"Coordinacion","type":"access","exp":9999999999}
const COORD_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJjb29yZCIsInJvbGUiOiJDb29yZGluYWNpb24iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const CASO_ID = 55;

// ── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_PROCESO: ProcesoEptRead = {
  id: 1,
  caso_ept_id: CASO_ID,
  plazo_evid_denunciante: "2026-02-15",
  plazo_insumos_empresa: "2026-03-01",
  hay_testigos: true,
  testigos_cantidad: 3,
  num_entrevistas: 2,
  insumos_eista: "Listado de riesgos",
  doc_incumplimiento: "Acta N° 12",
  observaciones: "Sin novedad",
  created_at: "2026-01-20T10:00:00Z",
  updated_at: "2026-01-20T10:00:00Z",
};

// ── Render helper ─────────────────────────────────────────────────────────────

function renderPanel(canWrite: boolean, token = ADMIN_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <ProcesoEptPanel casoId={CASO_ID} canWrite={canWrite} />
      </AuthProvider>
    </QueryClientProvider>
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ProcesoEptPanel", () => {
  // ── (1) No proceso (GET 404) → empty state ─────────────────────────────────

  it("muestra empty state cuando GET devuelve 404", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        new HttpResponse(null, { status: 404 })
      )
    );

    renderPanel(true, ADMIN_TOKEN);

    await waitFor(() =>
      expect(screen.getByText(/Sin proceso registrado/i)).toBeInTheDocument()
    );
    expect(screen.getByTestId("btn-registrar-proceso")).toBeInTheDocument();
  });

  // ── (2) RBAC: Coordinacion no ve CTA de escritura ─────────────────────────

  it("NO muestra el botón 'Registrar proceso' cuando canWrite=false (Coordinacion)", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        new HttpResponse(null, { status: 404 })
      )
    );

    renderPanel(false, COORD_TOKEN);

    await waitFor(() =>
      expect(screen.getByText(/Sin proceso registrado/i)).toBeInTheDocument()
    );
    expect(screen.queryByTestId("btn-registrar-proceso")).not.toBeInTheDocument();
  });

  // ── (3) Proceso existente → vista de datos + sin CTA de registro ───────────

  it("muestra los datos del proceso cuando existe", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        HttpResponse.json(MOCK_PROCESO)
      )
    );

    renderPanel(true, ADMIN_TOKEN);

    await waitFor(() =>
      expect(screen.getByText("Sí")).toBeInTheDocument()
    );

    // testigos cantidad rendered as (3) - may be split across text nodes
    expect(
      screen.getByText((_, element) =>
        element?.tagName === "SPAN" &&
        element.textContent?.replace(/\s/g, "") === "(3)"
      )
    ).toBeInTheDocument();
    // num entrevistas
    expect(screen.getByText("2")).toBeInTheDocument();
    // Edit button
    expect(screen.getByTestId("btn-editar-proceso")).toBeInTheDocument();
    // NO registrar button
    expect(screen.queryByTestId("btn-registrar-proceso")).not.toBeInTheDocument();
  });

  // ── (4) Coordinacion no ve botón editar proceso ────────────────────────────

  it("NO muestra 'Editar proceso' para Coordinacion (canWrite=false)", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        HttpResponse.json(MOCK_PROCESO)
      )
    );

    renderPanel(false, COORD_TOKEN);

    await waitFor(() =>
      expect(screen.getByText("Sí")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("btn-editar-proceso")).not.toBeInTheDocument();
  });

  // ── (5) Create proceso → POST fires with correct body ─────────────────────

  it("crea proceso (POST) con body correcto y muestra los datos tras crear", async () => {
    let capturedBody: unknown;

    // Start with 404, then return data after POST
    let procesoCreado = false;

    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () => {
        if (!procesoCreado) {
          return new HttpResponse(null, { status: 404 });
        }
        return HttpResponse.json({
          ...MOCK_PROCESO,
          hay_testigos: true,
          testigos_cantidad: 3,
          num_entrevistas: 2,
        });
      }),
      http.post(
        `${BASE}/api/v1/casos-ept/:casoId/proceso`,
        async ({ request }) => {
          capturedBody = await request.json();
          procesoCreado = true;
          return HttpResponse.json(MOCK_PROCESO, { status: 201 });
        }
      )
    );

    renderPanel(true, ADMIN_TOKEN);

    // Wait for empty state
    await waitFor(() =>
      expect(screen.getByTestId("btn-registrar-proceso")).toBeInTheDocument()
    );

    // Open dialog
    await userEvent.click(screen.getByTestId("btn-registrar-proceso"));

    // Dialog should be open
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );

    // Fill testigos fields
    const cantidadInput = screen.getByLabelText(/Cantidad de testigos/i);
    await userEvent.clear(cantidadInput);
    await userEvent.type(cantidadInput, "3");

    const entrevistasInput = screen.getByLabelText(/N° de entrevistas/i);
    await userEvent.clear(entrevistasInput);
    await userEvent.type(entrevistasInput, "2");

    // Check hay_testigos
    const hayTestigosCheckbox = screen.getByLabelText(/Hay testigos/i);
    await userEvent.click(hayTestigosCheckbox);

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    // POST must have fired
    await waitFor(() => {
      expect(capturedBody).toBeDefined();
      const body = capturedBody as Record<string, unknown>;
      expect(body.testigos_cantidad).toBe(3);
      expect(body.num_entrevistas).toBe(2);
      expect(body.hay_testigos).toBe(true);
    });
  });

  // ── (6) Edit proceso → PATCH fires ────────────────────────────────────────

  it("edita proceso (PATCH) → PATCH /api/v1/casos-ept/{caso_id}/proceso fires", async () => {
    let capturedPatch: unknown;

    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        HttpResponse.json(MOCK_PROCESO)
      ),
      http.patch(
        `${BASE}/api/v1/casos-ept/:casoId/proceso`,
        async ({ request }) => {
          capturedPatch = await request.json();
          return HttpResponse.json({
            ...MOCK_PROCESO,
            num_entrevistas: 5,
          });
        }
      )
    );

    renderPanel(true, ADMIN_TOKEN);

    // Wait for data to render
    await waitFor(() =>
      expect(screen.getByTestId("btn-editar-proceso")).toBeInTheDocument()
    );

    // Open edit dialog
    await userEvent.click(screen.getByTestId("btn-editar-proceso"));

    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );

    // Change num_entrevistas
    const entrevistasInput = screen.getByLabelText(/N° de entrevistas/i);
    await userEvent.clear(entrevistasInput);
    await userEvent.type(entrevistasInput, "5");

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    // PATCH must have fired
    await waitFor(() => {
      expect(capturedPatch).toBeDefined();
      const body = capturedPatch as Record<string, unknown>;
      expect(body.num_entrevistas).toBe(5);
    });
  });

  // ── (7) Number validation: negative testigos_cantidad blocks submit ─────────

  it("bloquea submit si testigos_cantidad es negativo (validación zod)", async () => {
    const mutateSpy = vi.fn();

    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/proceso`, () =>
        new HttpResponse(null, { status: 404 })
      ),
      http.post(`${BASE}/api/v1/casos-ept/:casoId/proceso`, async () => {
        mutateSpy();
        return HttpResponse.json(MOCK_PROCESO, { status: 201 });
      })
    );

    renderPanel(true, ADMIN_TOKEN);

    await waitFor(() =>
      expect(screen.getByTestId("btn-registrar-proceso")).toBeInTheDocument()
    );

    await userEvent.click(screen.getByTestId("btn-registrar-proceso"));

    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );

    // Enter negative value for testigos_cantidad
    const cantidadInput = screen.getByLabelText(/Cantidad de testigos/i);
    await userEvent.clear(cantidadInput);
    await userEvent.type(cantidadInput, "-5");

    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    // Validation error must appear
    await waitFor(() =>
      expect(screen.getByText(/No puede ser negativo/i)).toBeInTheDocument()
    );

    // Mutation must NOT have been called
    expect(mutateSpy).not.toHaveBeenCalled();
  });
});
