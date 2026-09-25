/**
 * FarmacosSugeridosPanel: fármacos leídos de las recetas de SALUTEM.
 *
 * Cubre: listado con dosis y frecuencia, avisos, "Agregar al esquema" precargado
 * que envía lo sugerido, estados "ya cargado", y sin registro no hay botones.
 */
import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { FarmacosSugeridosPanel } from "./FarmacosSugeridosPanel";
import type { FarmacoSugeridoRead, RegistroFarmacologicoRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

// role "Coordinacion" (writer)
const WRITER_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

const REGISTRO: RegistroFarmacologicoRead = {
  id: 1,
  ingreso_id: 10,
  medico_tratante: "Dr. Sotomayor",
  estado_farmacologico: "activo",
  antecedentes_previos: null,
  tratamiento_previo: null,
  activo: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function sugerido(p: Partial<FarmacoSugeridoRead>): FarmacoSugeridoRead {
  return {
    ficha_clinica_id: 1,
    cita_fecha: "2024-04-05",
    profesional: "DR. JORGE SOTOMAYOR",
    texto: "Sertralina 100 mg 1 al día",
    medicamento: "Sertralina",
    dosis: "100 mg",
    frecuencia: "c/24h",
    avisos: [],
    en_esquema: false,
    receta_registrada: false,
    ...p,
  };
}

const SUGERIDOS = [
  sugerido({}),
  sugerido({
    texto: "Clotiazepam 5 mg SOS",
    medicamento: "Clotiazepam",
    dosis: "5 mg SOS",
    frecuencia: "otro",
    avisos: ["Uso SOS (según necesidad): el esquema no tiene esa frecuencia, queda como «Otro»."],
    en_esquema: true,
    receta_registrada: true,
  }),
];

function renderPanel(registro: RegistroFarmacologicoRead | null = REGISTRO) {
  tokenStore.setAccess(WRITER_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <Toaster />
          <FarmacosSugeridosPanel ingresoId={10} registro={registro} canWrite />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FarmacosSugeridosPanel", () => {
  it("lista los fármacos de SALUTEM con dosis, frecuencia y avisos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/sugeridos`, () =>
        HttpResponse.json(SUGERIDOS),
      ),
    );
    renderPanel();

    expect(await screen.findByText("Sertralina · 100 mg · Cada 24 h")).toBeInTheDocument();
    expect(screen.getByText("Clotiazepam · 5 mg SOS · Otro")).toBeInTheDocument();
    expect(screen.getByText(/Uso SOS/)).toBeInTheDocument();
    expect(screen.getByText("En el esquema")).toBeInTheDocument();
    expect(screen.getByText("Receta registrada")).toBeInTheDocument();
    // Solo el pendiente ofrece acciones.
    expect(screen.getAllByRole("button", { name: "Agregar al esquema" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Registrar receta" })).toHaveLength(1);
  });

  it("'Agregar al esquema' abre el formulario precargado y envía lo sugerido", async () => {
    const postSpy = vi.fn();
    server.use(
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/sugeridos`, () =>
        HttpResponse.json([sugerido({})]),
      ),
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, () => HttpResponse.json([])),
      http.post(`${BASE}/api/v1/registro-farmacologico/:id/esquema`, async ({ request }) => {
        postSpy(await request.json());
        return HttpResponse.json(
          {
            id: 9,
            registro_id: 1,
            medicamento: "Sertralina",
            dosis: "100 mg",
            frecuencia: "c/24h",
            extra_sistema: false,
            vigente: true,
            created_at: "2026-09-25T00:00:00Z",
          },
          { status: 201 },
        );
      }),
    );
    renderPanel();

    await userEvent.click(await screen.findByRole("button", { name: "Agregar al esquema" }));
    expect(screen.getByLabelText("Medicamento")).toHaveValue("Sertralina");
    expect(screen.getByLabelText("Dosis")).toHaveValue("100 mg");
    expect(screen.getByLabelText("Frecuencia")).toHaveValue("c/24h");
    await userEvent.click(screen.getByRole("button", { name: "Agregar indicación" }));

    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith({
        medicamento: "Sertralina",
        dosis: "100 mg",
        frecuencia: "c/24h",
        extra_sistema: false,
      }),
    );
  });

  it("'Registrar receta' precarga la fecha de la atención y el medicamento", async () => {
    server.use(
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/sugeridos`, () =>
        HttpResponse.json([sugerido({})]),
      ),
    );
    renderPanel();

    await userEvent.click(await screen.findByRole("button", { name: "Registrar receta" }));
    expect(screen.getByDisplayValue("2024-04-05")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Sertralina 100 mg")).toBeInTheDocument();
  });

  it("sin registro farmacológico muestra las sugerencias pero no permite agregarlas", async () => {
    server.use(
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/sugeridos`, () =>
        HttpResponse.json([sugerido({})]),
      ),
    );
    renderPanel(null);

    expect(await screen.findByText(/Crea el registro farmacológico/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar al esquema" })).not.toBeInTheDocument();
  });

  it("no muestra nada si SALUTEM no recetó fármacos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/registro-farmacologico/:id/sugeridos`, () => HttpResponse.json([])),
    );
    renderPanel();

    await waitFor(() =>
      expect(screen.queryByText("Fármacos recetados en SALUTEM")).not.toBeInTheDocument(),
    );
  });
});
