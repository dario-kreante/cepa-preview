import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { PlazosEptPanel } from "./PlazosEptPanel";
import { ContactosEptPanel } from "./ContactosEptPanel";
import type { PlazoEptRead, ContactoEptRead } from "./api";

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

const CASO_ID = 77;

// ── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_PLAZOS: PlazoEptRead = {
  id: 1,
  caso_ept_id: CASO_ID,
  plazo_informe_ept: "2026-03-15",
  plazo_portal_isl: "2026-04-01",
  fecha_entrega_isl: "2026-04-10",
  fecha_envio: "2026-04-05",
  estado_informe: "en_plazo",
  estado_entrega_isl: "vencido",
  created_at: "2026-01-20T10:00:00Z",
  updated_at: "2026-01-20T10:00:00Z",
};

const MOCK_CONTACTO: ContactoEptRead = {
  id: 1,
  caso_ept_id: CASO_ID,
  correo: "contacto@empresa.cl",
  created_at: "2026-01-20T10:00:00Z",
};

// ── Render helpers ────────────────────────────────────────────────────────────

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderPlazos(canWrite: boolean, token = ADMIN_TOKEN) {
  tokenStore.setAccess(token);
  const qc = makeQC();
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <PlazosEptPanel casoId={CASO_ID} canWrite={canWrite} />
      </AuthProvider>
    </QueryClientProvider>
  );
}

function renderContactos(canWrite: boolean, token = ADMIN_TOKEN) {
  tokenStore.setAccess(token);
  const qc = makeQC();
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <ContactosEptPanel casoId={CASO_ID} canWrite={canWrite} />
      </AuthProvider>
    </QueryClientProvider>
  );
}

// ── Tests: PlazosEptPanel ─────────────────────────────────────────────────────

describe("PlazosEptPanel", () => {
  // ── (1) No plazos (GET 404) → empty state + CTA (Administrativo) ─────────

  it("muestra empty state con CTA cuando GET devuelve 404 (Administrativo)", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () =>
        new HttpResponse(null, { status: 404 })
      )
    );

    renderPlazos(true, ADMIN_TOKEN);

    await waitFor(() =>
      expect(screen.getByText(/Sin plazos registrados/i)).toBeInTheDocument()
    );
    expect(screen.getByTestId("btn-registrar-plazos")).toBeInTheDocument();
  });

  // ── (2) Create plazos → POST fires + refetch shows dates + badges ─────────

  it("crea plazos (POST) y tras refetch muestra fechas y badges de cumplimiento", async () => {
    let capturedBody: unknown;
    let plazosCreados = false;

    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () => {
        if (!plazosCreados) {
          return new HttpResponse(null, { status: 404 });
        }
        return HttpResponse.json(MOCK_PLAZOS);
      }),
      http.post(
        `${BASE}/api/v1/casos-ept/:casoId/plazos`,
        async ({ request }) => {
          capturedBody = await request.json();
          plazosCreados = true;
          return HttpResponse.json(MOCK_PLAZOS, { status: 201 });
        }
      )
    );

    renderPlazos(true, ADMIN_TOKEN);

    // Wait for empty state
    await waitFor(() =>
      expect(screen.getByTestId("btn-registrar-plazos")).toBeInTheDocument()
    );

    // Open dialog
    await userEvent.click(screen.getByTestId("btn-registrar-plazos"));

    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );

    // Fill plazo_informe_ept
    const plazoInformeInput = screen.getByLabelText(/Plazo informe EPT/i);
    await userEvent.type(plazoInformeInput, "2026-03-15");

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    // POST must have fired
    await waitFor(() => {
      expect(capturedBody).toBeDefined();
      const body = capturedBody as Record<string, unknown>;
      expect(body.caso_ept_id).toBe(CASO_ID);
    });

    // After refetch, dates and badges should appear
    await waitFor(() => {
      // estado_informe: "en_plazo" → "En plazo"
      expect(screen.getByText("En plazo")).toBeInTheDocument();
      // estado_entrega_isl: "vencido" → "Vencido"
      expect(screen.getByText("Vencido")).toBeInTheDocument();
    });
  });

  // ── (3) Edit plazos → PATCH fires ────────────────────────────────────────

  it("edita plazos (PATCH) → PATCH /api/v1/casos-ept/{caso_id}/plazos fires", async () => {
    let capturedPatch: unknown;

    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () =>
        HttpResponse.json(MOCK_PLAZOS)
      ),
      http.patch(
        `${BASE}/api/v1/casos-ept/:casoId/plazos`,
        async ({ request }) => {
          capturedPatch = await request.json();
          return HttpResponse.json({
            ...MOCK_PLAZOS,
            plazo_portal_isl: "2026-05-01",
          });
        }
      )
    );

    renderPlazos(true, ADMIN_TOKEN);

    // Wait for data to render
    await waitFor(() =>
      expect(screen.getByTestId("btn-editar-plazos")).toBeInTheDocument()
    );

    // Open edit dialog
    await userEvent.click(screen.getByTestId("btn-editar-plazos"));

    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );

    // Change plazo_portal_isl
    const plazoPortalInput = screen.getByLabelText(/Plazo portal ISL/i);
    await userEvent.clear(plazoPortalInput);
    await userEvent.type(plazoPortalInput, "2026-05-01");

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    // PATCH must have fired
    await waitFor(() => {
      expect(capturedPatch).toBeDefined();
    });
  });

  // ── (4) Cumplimiento badges render correctly ───────────────────────────────

  it("muestra ambos badges de cumplimiento correctamente", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () =>
        HttpResponse.json({
          ...MOCK_PLAZOS,
          estado_informe: "en_plazo",
          estado_entrega_isl: "vencido",
        })
      )
    );

    renderPlazos(true, ADMIN_TOKEN);

    await waitFor(() => {
      expect(screen.getByText("En plazo")).toBeInTheDocument();
      expect(screen.getByText("Vencido")).toBeInTheDocument();
    });
  });

  // ── (5) RBAC: Coordinacion no ve CTAs de escritura ───────────────────────

  it("Coordinacion NO ve 'Registrar plazos' ni 'Editar plazos'", async () => {
    // First test: null data (404)
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () =>
        new HttpResponse(null, { status: 404 })
      )
    );

    renderPlazos(false, COORD_TOKEN);

    await waitFor(() =>
      expect(screen.getByText(/Sin plazos registrados/i)).toBeInTheDocument()
    );
    expect(screen.queryByTestId("btn-registrar-plazos")).not.toBeInTheDocument();
  });

  it("Coordinacion NO ve 'Editar plazos' cuando hay datos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId/plazos`, () =>
        HttpResponse.json(MOCK_PLAZOS)
      )
    );

    renderPlazos(false, COORD_TOKEN);

    await waitFor(() =>
      expect(screen.getByText("En plazo")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("btn-editar-plazos")).not.toBeInTheDocument();
  });
});

// ── Tests: ContactosEptPanel ──────────────────────────────────────────────────

describe("ContactosEptPanel", () => {
  // ── (6) Agregar contacto válido → POST fires + aparece en sesión ─────────

  it("agrega contacto válido → POST fires con {correo} y aparece en la lista", async () => {
    let capturedBody: unknown;

    server.use(
      http.post(
        `${BASE}/api/v1/casos-ept/:casoId/contactos`,
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(MOCK_CONTACTO, { status: 201 });
        }
      )
    );

    renderContactos(true, ADMIN_TOKEN);

    const emailInput = screen.getByTestId("input-contacto-correo");
    await userEvent.type(emailInput, "contacto@empresa.cl");

    await userEvent.click(screen.getByTestId("btn-agregar-contacto"));

    // POST must have fired with {correo}
    await waitFor(() => {
      expect(capturedBody).toBeDefined();
      const body = capturedBody as Record<string, unknown>;
      expect(body.correo).toBe("contacto@empresa.cl");
    });

    // Email appears in the session list
    await waitFor(() =>
      expect(screen.getByText("contacto@empresa.cl")).toBeInTheDocument()
    );
  });

  // ── (7) Email inválido → error inline, POST NOT called ───────────────────

  it("email inválido → muestra error inline y NO llama al POST", async () => {
    const postSpy = vi.fn();

    server.use(
      http.post(`${BASE}/api/v1/casos-ept/:casoId/contactos`, () => {
        postSpy();
        return HttpResponse.json(MOCK_CONTACTO, { status: 201 });
      })
    );

    renderContactos(true, ADMIN_TOKEN);

    const emailInput = screen.getByTestId("input-contacto-correo");
    await userEvent.type(emailInput, "no-es-un-email");

    await userEvent.click(screen.getByTestId("btn-agregar-contacto"));

    // Error inline must appear
    await waitFor(() =>
      expect(screen.getByTestId("error-correo")).toBeInTheDocument()
    );

    // POST must NOT have been called
    expect(postSpy).not.toHaveBeenCalled();
  });

  // ── (8) RBAC: Coordinacion no ve input ni botón de agregar ───────────────

  it("Coordinacion NO ve input ni botón 'Agregar contacto'", () => {
    renderContactos(false, COORD_TOKEN);

    expect(
      screen.queryByTestId("input-contacto-correo")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("btn-agregar-contacto")
    ).not.toBeInTheDocument();
  });
});
