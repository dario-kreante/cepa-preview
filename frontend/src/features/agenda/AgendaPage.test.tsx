import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { toast } from "sonner";
import { AgendaPage } from "./AgendaPage";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderPage(token: string = TOKENS.Coordinacion) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <AgendaPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const PACIENTE_BASE = {
  folio: null,
  prioridad: "control_vencido",
  razon: "Control vencido hace 5 días",
  fecha_objetivo: "2026-10-10",
  dia_sugerido: "2026-10-19",
  reposo_hasta: null,
  sin_vinculo_salutem: false,
  dijo_agendada_sin_hora: false,
  ultima_gestion: null,
};

const LISTA = {
  profesional_id: 5,
  desde: "2026-10-14",
  hasta: "2026-10-23",
  por_dia: [
    { fecha: "2026-10-14", cupo: 4, asignados: 3 },
    { fecha: "2026-10-15", cupo: 4, asignados: 0 },
  ],
  pacientes: [
    {
      ...PACIENTE_BASE,
      paciente_id: 11,
      nombre: "Ana Soto",
      folio: "F-100",
      seccion: "por_citar",
      sin_vinculo_salutem: true,
      ultima_gestion: {
        fecha: "2026-10-15T14:00:00Z",
        resultado: "no_contesta",
        usuario: "cvidal",
        nota: null,
      },
    },
    {
      ...PACIENTE_BASE,
      paciente_id: 12,
      nombre: "Beto Rojas",
      seccion: "por_citar",
      dijo_agendada_sin_hora: true,
    },
    {
      ...PACIENTE_BASE,
      paciente_id: 13,
      nombre: "Carla Díaz",
      dia_sugerido: null,
      seccion: "sin_cupo",
    },
  ],
};

const DISPO = [
  {
    id: 7,
    profesional_id: 5,
    dia_semana: 1,
    cupo_diario: 4,
    activo: true,
    created_at: "2026-06-20T00:00:00Z",
  },
];

beforeEach(() => {
  server.use(
    http.get(`${BASE}/api/v1/profesionales`, () =>
      HttpResponse.json([
        { id: 5, nombre: "Dra. Pérez", especialidad: "Psiquiatría", activo: true },
      ]),
    ),
    http.get(`${BASE}/api/v1/pacientes-por-citar`, () => HttpResponse.json(LISTA)),
    http.get(`${BASE}/api/v1/disponibilidad-profesional/:id`, () =>
      HttpResponse.json(DISPO),
    ),
  );
});

async function elegirProfesional() {
  const user = userEvent.setup();
  const select = await screen.findByLabelText("Profesional");
  await waitFor(() => expect(screen.getByText(/Dra\. Pérez/)).toBeInTheDocument());
  await user.selectOptions(select, "5");
  return user;
}

describe("AgendaPage", () => {
  it("al elegir un profesional muestra las filas por citar y el contador de sin cupo", async () => {
    renderPage();
    await elegirProfesional();
    expect(await screen.findByText("Ana Soto")).toBeInTheDocument();
    expect(screen.getByText("Beto Rojas")).toBeInTheDocument();
    expect(screen.getByText("Sin cupo en el período (1)")).toBeInTheDocument();
    expect(screen.getByText("En reposo (0)")).toBeInTheDocument();
    expect(screen.getByText("Sin vínculo SALUTEM")).toBeInTheDocument();
    expect(
      screen.getByText("Dijo agendada, sin hora en SALUTEM"),
    ).toBeInTheDocument();
    expect(screen.getByText("No contesta · 15-10 · cvidal")).toBeInTheDocument();
    expect(screen.getByText("Mié 14 · 3/4")).toBeInTheDocument();
  });

  it("avisa cuando el profesional no tiene disponibilidad", async () => {
    server.use(
      http.get(`${BASE}/api/v1/disponibilidad-profesional/:id`, () =>
        HttpResponse.json([]),
      ),
    );
    renderPage();
    await elegirProfesional();
    expect(
      await screen.findByText(
        "Este profesional no tiene disponibilidad cargada: todos sus pacientes aparecen como sin cupo.",
      ),
    ).toBeInTheDocument();
  });

  it("registrar un contacto hace POST con el resultado y la nota", async () => {
    let body: unknown = null;
    server.use(
      http.post(
        `${BASE}/api/v1/pacientes-por-citar/:id/gestiones`,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(
            {
              id: 1,
              paciente_id: 11,
              profesional_id: 5,
              resultado: "no_contesta",
              nota: "Llamé dos veces",
              usuario: "test",
              created_at: "2026-10-16T12:00:00Z",
            },
            { status: 201 },
          );
        },
      ),
    );
    renderPage();
    const user = await elegirProfesional();
    await screen.findByText("Ana Soto");
    await user.click(
      screen.getAllByRole("button", { name: "Registrar contacto" })[0],
    );
    await user.selectOptions(await screen.findByLabelText("Resultado"), "no_contesta");
    await user.type(screen.getByLabelText("Nota (opcional)"), "Llamé dos veces");
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(body).toEqual({
        profesional_id: 5,
        resultado: "no_contesta",
        nota: "Llamé dos veces",
      }),
    );
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Contacto registrado"),
    );
  });

  it("quitar disponibilidad hace DELETE del día", async () => {
    let borrado: string | null = null;
    server.use(
      http.delete(`${BASE}/api/v1/disponibilidad-profesional/:id`, ({ params }) => {
        borrado = String(params.id);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderPage();
    const user = await elegirProfesional();
    await user.click(await screen.findByRole("button", { name: /Quitar Lunes/ }));
    await waitFor(() => expect(borrado).toBe("7"));
  });

  it("como Auditor no aparece Registrar contacto", async () => {
    renderPage(TOKENS.Auditor);
    await elegirProfesional();
    await screen.findByText("Ana Soto");
    expect(
      screen.queryByRole("button", { name: "Registrar contacto" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Quitar/ })).not.toBeInTheDocument();
  });
});
