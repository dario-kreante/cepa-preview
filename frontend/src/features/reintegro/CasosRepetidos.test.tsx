/**
 * QA-003 — casos de reintegro repetidos:
 *  - Aviso al crear un caso para un paciente que ya tiene casos activos (no bloquea).
 *  - Listado de pacientes con más de un caso activo (solo lectura, con acceso al caso).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { ReintegroPage } from "./ReintegroPage";
import { CasosRepetidosPanel } from "./CasosRepetidosPanel";

const BASE = import.meta.env.VITE_API_BASE_URL;

// JWT mínimo con rol Coordinacion / Auditor (firma irrelevante en el front).
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
const AUDITOR_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhdWRpdG9yIiwicm9sZSI6IkF1ZGl0b3IiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjo5OTk5OTk5OTk5fQ." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const PACIENTE = {
  id: 5,
  rut: "11.111.111-1",
  nombre: "Paciente Demo",
  sexo: "F",
  edad: 40,
  region: "Maule",
};

function casoBase(id: number, over: Record<string, unknown> = {}) {
  return {
    id,
    ingreso_id: 10,
    rut: "11.111.111-1",
    nombre: "Paciente Demo",
    tipo_derivacion: "DIEP",
    fecha_caso: "2026-06-20",
    sexo: "F",
    edad: 40,
    region: "Maule",
    comuna: null,
    rubro_empleador: null,
    razon_social: "Forestal Maule SpA",
    tipo_trabajador: "dependiente",
    estado_reintegro: "pendiente",
    fecha_reintegro: null,
    remitido_isl: false,
    alta_medica: false,
    fecha_alta_medica: null,
    alta_psicologica: false,
    fecha_alta_psico: null,
    tipo_alta: null,
    observaciones: null,
    ...over,
  };
}

function renderWith(ui: React.ReactElement, token = WRITER_TOKEN) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockPaciente(activos: unknown[]) {
  server.use(
    http.get(`${BASE}/api/v1/pacientes/buscar`, () => HttpResponse.json([PACIENTE])),
    http.get(`${BASE}/api/v1/pacientes/5/vista-360`, () =>
      HttpResponse.json({
        paciente: PACIENTE,
        ingresos: [
          {
            id: 10,
            folio: "F-1",
            tipo_derivacion: "DIEP",
            razon_social: "Forestal Maule SpA",
            estado: "activo",
          },
        ],
      }),
    ),
    http.get(`${BASE}/api/v1/reintegros`, ({ request }) => {
      const u = new URL(request.url);
      if (u.searchParams.get("paciente_id") === "5") return HttpResponse.json(activos);
      return HttpResponse.json([]);
    }),
  );
}

async function seleccionarPaciente(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Buscar pacientes"), "Demo");
  await user.click(await screen.findByText("Paciente Demo"));
  await waitFor(() => expect(screen.getByTestId("btn-nuevo-caso")).toBeEnabled());
}

beforeEach(() => {
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  tokenStore.clear();
});

describe("Aviso al crear un caso repetido", () => {
  it("muestra los casos activos y permite continuar de todos modos", async () => {
    mockPaciente([casoBase(21), casoBase(22, { estado_reintegro: "parcial" })]);
    renderWith(<ReintegroPage />);
    const user = userEvent.setup();

    await seleccionarPaciente(user);
    await user.click(screen.getByTestId("btn-nuevo-caso"));

    const aviso = await screen.findByRole("dialog", { name: /ya tiene casos activos/i });
    expect(within(aviso).getByText(/Caso N° 21/)).toBeInTheDocument();
    expect(within(aviso).getByText(/Caso N° 22/)).toBeInTheDocument();

    await user.click(within(aviso).getByRole("button", { name: /Continuar de todos modos/i }));

    expect(await screen.findByRole("dialog", { name: /Nuevo caso de reintegro/i })).toBeInTheDocument();
  });

  it("permite abrir uno de los casos existentes en lugar de crear otro", async () => {
    mockPaciente([casoBase(21)]);
    server.use(
      http.get(`${BASE}/api/v1/reintegros/21`, () => HttpResponse.json(casoBase(21))),
      http.get(`${BASE}/api/v1/reintegros/21/reca`, () =>
        HttpResponse.json({ detail: "sin RECA" }, { status: 404 }),
      ),
    );
    renderWith(<ReintegroPage />);
    const user = userEvent.setup();

    await seleccionarPaciente(user);
    await user.click(screen.getByTestId("btn-nuevo-caso"));
    const aviso = await screen.findByRole("dialog", { name: /ya tiene casos activos/i });
    await user.click(within(aviso).getByRole("button", { name: /Abrir caso N° 21/i }));

    expect(await screen.findByText("Caso N° 21")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: /ya tiene casos activos/i })).toBeNull();
    expect(screen.queryByRole("dialog", { name: /Nuevo caso de reintegro/i })).toBeNull();
  });

  it("sin casos activos abre directo el formulario, sin aviso", async () => {
    mockPaciente([]);
    renderWith(<ReintegroPage />);
    const user = userEvent.setup();

    await seleccionarPaciente(user);
    await user.click(screen.getByTestId("btn-nuevo-caso"));

    expect(await screen.findByRole("dialog", { name: /Nuevo caso de reintegro/i })).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: /ya tiene casos activos/i })).toBeNull();
  });
});

describe("Listado de pacientes con casos repetidos", () => {
  const DUPLICADOS = [
    {
      paciente_id: 5,
      rut: "11.111.111-1",
      nombre: "Paciente Demo",
      casos: [
        {
          id: 21,
          ingreso_id: 10,
          region: "Maule",
          razon_social: "Forestal Maule SpA",
          fecha_caso: "2026-06-20",
          estado_reintegro: "pendiente",
        },
        {
          id: 22,
          ingreso_id: 11,
          region: "Biobío",
          razon_social: null,
          fecha_caso: "2026-08-02",
          estado_reintegro: "parcial",
        },
      ],
    },
  ];

  it("muestra paciente, RUT y por cada caso número, región, razón social, fecha y estado", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reintegros/duplicados`, () => HttpResponse.json(DUPLICADOS)),
    );
    renderWith(<CasosRepetidosPanel onAbrirCaso={() => {}} />, AUDITOR_TOKEN);

    expect(await screen.findByText("Paciente Demo")).toBeInTheDocument();
    expect(screen.getByText("11.111.111-1")).toBeInTheDocument();
    const fila21 = screen.getByTestId("fila-caso-21");
    expect(within(fila21).getByText("N° 21")).toBeInTheDocument();
    expect(within(fila21).getByText("Maule")).toBeInTheDocument();
    expect(within(fila21).getByText("Forestal Maule SpA")).toBeInTheDocument();
    expect(within(fila21).getByText("20/06/2026")).toBeInTheDocument();
    expect(within(fila21).getByText("Pendiente")).toBeInTheDocument();
    const fila22 = screen.getByTestId("fila-caso-22");
    expect(within(fila22).getByText("Biobío")).toBeInTheDocument();
    expect(within(fila22).getByText("—")).toBeInTheDocument();
    expect(within(fila22).getByText("Parcial")).toBeInTheDocument();
  });

  it("abre el caso elegido y no ofrece fusionar, cerrar ni borrar", async () => {
    server.use(
      http.get(`${BASE}/api/v1/reintegros/duplicados`, () => HttpResponse.json(DUPLICADOS)),
    );
    const onAbrir = vi.fn();
    renderWith(<CasosRepetidosPanel onAbrirCaso={onAbrir} />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /Abrir caso N° 22/i }));
    expect(onAbrir).toHaveBeenCalledWith(22);
    expect(screen.queryByRole("button", { name: /fusionar|cerrar|eliminar|borrar/i })).toBeNull();
  });

  it("avisa cuando no hay pacientes con casos repetidos", async () => {
    server.use(http.get(`${BASE}/api/v1/reintegros/duplicados`, () => HttpResponse.json([])));
    renderWith(<CasosRepetidosPanel onAbrirCaso={() => {}} />);
    expect(await screen.findByText(/No hay pacientes con más de un caso activo/i)).toBeInTheDocument();
  });
});
