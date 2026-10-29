import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { EptPage } from "./EptPage";

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

// ── Render helper ────────────────────────────────────────────────────────────

function renderPage(token = ADMIN_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <EptPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_PACIENTE = {
  id: 7,
  rut: "15.123.456-7",
  nombre: "Juan Pérez",
  sexo: "M",
  edad: 52,
  region: "Metropolitana",
  comuna: "Providencia",
  telefono: "+56911223344",
  correo: "jperez@example.com",
};

const MOCK_VISTA_360 = {
  paciente: MOCK_PACIENTE,
  ingresos: [
    {
      id: 10,
      paciente_id: 7,
      fecha_ingreso: "2026-01-15",
      diagnostico_ingreso: "Fractura de cadera",
      estado: "activo",
    },
  ],
};

const MOCK_CASO: import("./api").CasoEptRead = {
  id: 55,
  ingreso_id: 10,
  mes: "Enero 2026",
  fecha_ingreso_ept: "2026-01-20",
  nombre_trabajador: "María González",
  rut_trabajador: "12.345.678-9",
  region_trabajador: "Metropolitana",
  eista: "EISTA-001",
  factor_riesgo: "sobrecarga",
  corresponde_ept: true,
  estado: "abierto",
  razon_social: "Empresa S.A.",
  unidad_cargo_horario: "Bodega · Operario",
  created_at: "2026-01-20T10:00:00Z",
  updated_at: "2026-01-20T10:00:00Z",
};

// ── Helper: set up paciente search + vista360 + POST mocks ───────────────────

function setupPacienteHandlers(
  captureBody?: (b: unknown) => void,
  casosPaciente: import("./api").CasoEptRead[] = [],
) {
  server.use(
    http.get(`${BASE}/api/v1/casos-ept`, () => HttpResponse.json(casosPaciente)),
    http.get(`${BASE}/api/v1/pacientes/buscar`, ({ request }) => {
      const url = new URL(request.url);
      if (url.searchParams.get("q")) return HttpResponse.json([MOCK_PACIENTE]);
      return HttpResponse.json([]);
    }),
    http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
      HttpResponse.json(MOCK_VISTA_360)
    ),
    http.post(`${BASE}/api/v1/casos-ept`, async ({ request }) => {
      const body = await request.json();
      captureBody?.(body);
      return HttpResponse.json(MOCK_CASO, { status: 201 });
    }),
    // Also handle useCaso after creation
    http.get(`${BASE}/api/v1/casos-ept/:casoId`, () =>
      HttpResponse.json(MOCK_CASO)
    )
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("EptPage", () => {
  // ── Basic render ───────────────────────────────────────────────────────────

  it("muestra el título y subtítulo correctos", async () => {
    renderPage();
    expect(
      await screen.findByText("Seguimiento EPT")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Evaluaciones de Puesto de Trabajo/i)
    ).toBeInTheDocument();
  });

  it("tiene el placeholder exacto requerido", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Buscar por RUT, folio, nombre o ID SALUTEM")
    ).toBeInTheDocument();
  });

  it("muestra input de carga por caso_id", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Cargar caso N°")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Cargar/i })
    ).toBeInTheDocument();
  });

  // ── RBAC: "Nueva EPT" button ───────────────────────────────────────────────

  it("muestra 'Nueva EPT' para Administrativo (puedeEscribirEpt)", async () => {
    renderPage(ADMIN_TOKEN);
    expect(
      await screen.findByTestId("btn-nueva-ept")
    ).toBeInTheDocument();
  });

  it("NO muestra 'Nueva EPT' para Coordinacion (RBAC EPT más estricto)", async () => {
    renderPage(COORD_TOKEN);
    await screen.findByText("Seguimiento EPT");
    expect(screen.queryByTestId("btn-nueva-ept")).not.toBeInTheDocument();
  });

  // ── (a) Alta paciente-driven ───────────────────────────────────────────────

  it("(a) busca paciente, selecciona, abre dialog, envía POST con ingreso_id:10, renderiza detalle del caso", async () => {
    let capturedBody: unknown;
    setupPacienteHandlers((b) => {
      capturedBody = b;
    });

    renderPage(ADMIN_TOKEN);

    // Search for paciente
    const searchInput = screen.getByPlaceholderText("Buscar por RUT, folio, nombre o ID SALUTEM");
    await userEvent.type(searchInput, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Select paciente
    await userEvent.click(screen.getByText("Juan Pérez"));

    // Wait for ingreso to resolve and Nueva EPT button to become enabled
    await waitFor(
      () => {
        const btn = screen.getByTestId("btn-nueva-ept");
        expect(btn).not.toBeDisabled();
      },
      { timeout: 8000 }
    );

    // Click Nueva EPT
    await userEvent.click(screen.getByTestId("btn-nueva-ept"));

    // Dialog should be open
    await waitFor(
      () => expect(screen.getByRole("dialog")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Fill required fields
    await userEvent.type(screen.getByLabelText(/Mes/i), "Enero 2026");
    await userEvent.type(
      screen.getByLabelText(/Fecha de ingreso EPT/i),
      "2026-01-20"
    );
    await userEvent.type(
      screen.getByLabelText(/Nombre del trabajador/i),
      "María González"
    );
    await userEvent.type(
      screen.getByLabelText(/RUT del trabajador/i),
      "12.345.678-9"
    );
    await userEvent.type(
      screen.getByLabelText(/Región del trabajador/i),
      "Metropolitana"
    );
    await userEvent.type(screen.getByLabelText(/EISTA/i), "EISTA-001");

    // Sin factor elegido no se envía (el selector parte vacío: QA-003)
    await userEvent.click(screen.getByRole("button", { name: /Crear caso EPT/i }));
    expect(
      await screen.findByText("Selecciona un factor de riesgo")
    ).toBeInTheDocument();
    expect(capturedBody).toBeUndefined();

    await userEvent.selectOptions(
      screen.getByLabelText(/Factor de riesgo/i),
      "Hostilidad de la jefatura"
    );

    // Submit
    await userEvent.click(screen.getByRole("button", { name: /Crear caso EPT/i }));

    // POST body must contain ingreso_id: 10
    await waitFor(
      () => {
        expect(capturedBody).toBeDefined();
        expect((capturedBody as Record<string, unknown>).ingreso_id).toBe(10);
        expect((capturedBody as Record<string, unknown>).factor_riesgo).toBe(
          "hostilidad_jefatura"
        );
      },
      { timeout: 8000 }
    );

    // Caso detail renders — nombre_trabajador
    await waitFor(
      () => expect(screen.getByText("María González")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    // Estado badge "Abierto"
    expect(screen.getByText("Abierto")).toBeInTheDocument();
  });

  // ── (b) Cargar por caso_id ─────────────────────────────────────────────────

  it("(b) carga caso por id → GET /api/v1/casos-ept/{id} → renderiza detalle", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, ({ params }) => {
        if (String(params.casoId) === "55") {
          return HttpResponse.json(MOCK_CASO);
        }
        return new HttpResponse(null, { status: 404 });
      })
    );

    renderPage(ADMIN_TOKEN);

    const casoInput = screen.getByTestId("input-caso-id");
    await userEvent.type(casoInput, "55");

    await userEvent.click(screen.getByTestId("btn-cargar-caso"));

    // Detail renders
    await waitFor(
      () => expect(screen.getByText("María González")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    expect(screen.getByText("Abierto")).toBeInTheDocument();
    expect(screen.getByText("EISTA-001")).toBeInTheDocument();
  });

  // ── Empty / error states ───────────────────────────────────────────────────

  it("muestra empty state cuando el paciente no tiene ingresos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () =>
        HttpResponse.json([MOCK_PACIENTE])
      ),
      http.get(`${BASE}/api/v1/pacientes/:pacienteId/vista-360`, () =>
        HttpResponse.json({ paciente: MOCK_PACIENTE, ingresos: [] })
      ),
      http.get(`${BASE}/api/v1/casos-ept`, () => HttpResponse.json([]))
    );

    renderPage(ADMIN_TOKEN);

    const searchInput = screen.getByPlaceholderText("Buscar por RUT, folio, nombre o ID SALUTEM");
    await userEvent.type(searchInput, "Juan");

    await waitFor(
      () => expect(screen.getByText("Juan Pérez")).toBeInTheDocument(),
      { timeout: 8000 }
    );

    await userEvent.click(screen.getByText("Juan Pérez"));

    await waitFor(
      () =>
        expect(
          screen.getByText(/Este paciente no tiene ingresos registrados/i)
        ).toBeInTheDocument(),
      { timeout: 8000 }
    );
  });

  // ── QA Pilar 22-10 QA-003: casos del paciente y borrado ───────────────────

  it("al seleccionar un paciente lista sus casos EPT y permite abrir uno", async () => {
    const otro = { ...MOCK_CASO, id: 56, fecha_ingreso_ept: "2026-02-01" };
    setupPacienteHandlers(undefined, [otro, MOCK_CASO]);
    renderPage(ADMIN_TOKEN);

    await userEvent.type(
      screen.getByPlaceholderText("Buscar por RUT, folio, nombre o ID SALUTEM"),
      "Juan"
    );
    await userEvent.click(await screen.findByText("Juan Pérez", {}, { timeout: 8000 }));

    const tabla = await screen.findByTestId("casos-ept-paciente", {}, { timeout: 8000 });
    expect(tabla).toHaveTextContent("Casos EPT de Juan Pérez (2)");

    await userEvent.click(screen.getByRole("button", { name: "Abrir caso 55" }));
    expect(await screen.findByText("Caso N° 55", {}, { timeout: 8000 })).toBeInTheDocument();
  });

  it("Administrativo elimina un caso tras confirmar y el detalle se cierra", async () => {
    const deleteSpy = vi.fn();
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, () => HttpResponse.json(MOCK_CASO)),
      http.delete(`${BASE}/api/v1/casos-ept/:casoId`, ({ params }) => {
        deleteSpy(params.casoId);
        return new HttpResponse(null, { status: 204 });
      })
    );
    renderPage(ADMIN_TOKEN);

    await userEvent.type(screen.getByPlaceholderText("Cargar caso N°"), "55");
    await userEvent.click(screen.getByTestId("btn-cargar-caso"));
    await userEvent.click(await screen.findByTestId("btn-eliminar-caso", {}, { timeout: 8000 }));
    await userEvent.click(await screen.findByTestId("btn-confirmar-eliminar"));

    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith("55"));
    await waitFor(() => expect(screen.queryByText("Caso N° 55")).not.toBeInTheDocument());
  });

  it("Coordinacion NO ve el botón Eliminar", async () => {
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, () => HttpResponse.json(MOCK_CASO))
    );
    renderPage(COORD_TOKEN);

    await userEvent.type(screen.getByPlaceholderText("Cargar caso N°"), "55");
    await userEvent.click(screen.getByTestId("btn-cargar-caso"));
    await screen.findByText("Caso N° 55", {}, { timeout: 8000 });
    expect(screen.queryByTestId("btn-eliminar-caso")).not.toBeInTheDocument();
  });

  // ── QA UTalca 22-10 QA-003: factores de riesgo del área ────────────────────

  it("el selector ofrece los 24 factores del área en orden", async () => {
    setupPacienteHandlers();
    renderPage(ADMIN_TOKEN);

    await userEvent.type(
      screen.getByPlaceholderText("Buscar por RUT, folio, nombre o ID SALUTEM"),
      "Juan"
    );
    await userEvent.click(await screen.findByText("Juan Pérez", {}, { timeout: 8000 }));
    await waitFor(() => expect(screen.getByTestId("btn-nueva-ept")).not.toBeDisabled(), {
      timeout: 8000,
    });
    await userEvent.click(screen.getByTestId("btn-nueva-ept"));

    const select = (await screen.findByLabelText(/Factor de riesgo/i)) as HTMLSelectElement;
    const opciones = Array.from(select.options).map((o) => o.textContent);
    expect(opciones).toHaveLength(25); // placeholder + 24
    expect(select.value).toBe("");
    expect(opciones[1]).toBe("Sobrecarga");
    expect(opciones[24]).toBe("No aplica (no se evidencia exposición a riesgo laboral)");
    expect(opciones).not.toContain("Carga");
  });

  it("un caso con factor legado se muestra como «(anterior)» y al editarlo exige uno nuevo", async () => {
    const legado = { ...MOCK_CASO, factor_riesgo: "carga" as const };
    let patchBody: unknown;
    server.use(
      http.get(`${BASE}/api/v1/casos-ept/:casoId`, () => HttpResponse.json(legado)),
      http.patch(`${BASE}/api/v1/casos-ept/:casoId`, async ({ request }) => {
        patchBody = await request.json();
        return HttpResponse.json({ ...legado, factor_riesgo: "subcarga" });
      })
    );
    renderPage(ADMIN_TOKEN);

    await userEvent.type(screen.getByPlaceholderText("Cargar caso N°"), "55");
    await userEvent.click(screen.getByTestId("btn-cargar-caso"));
    expect(
      await screen.findByText("(anterior) Carga", {}, { timeout: 8000 })
    ).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("btn-editar-caso"));
    const select = (await screen.findByLabelText(/Factor de riesgo/i)) as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(screen.getByTestId("factor-riesgo-anterior")).toHaveTextContent(
      "(anterior) Carga"
    );

    await userEvent.click(screen.getByRole("button", { name: /Actualizar caso/i }));
    expect(
      await screen.findByText("Selecciona un factor de riesgo")
    ).toBeInTheDocument();
    expect(patchBody).toBeUndefined();

    await userEvent.selectOptions(select, "subcarga");
    await userEvent.click(screen.getByRole("button", { name: /Actualizar caso/i }));
    await waitFor(() =>
      expect((patchBody as Record<string, unknown>).factor_riesgo).toBe("subcarga")
    );
  });
});
