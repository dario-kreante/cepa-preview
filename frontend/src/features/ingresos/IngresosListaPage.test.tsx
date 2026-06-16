import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { IngresosListaPage } from "./IngresosListaPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

// Minimal valid JWT for role "Coordinacion" (not verified on the frontend, only decoded)
// Header: {"alg":"HS256","typ":"JWT"}
// Payload: {"sub":"1","username":"test","role":"Coordinacion","type":"access","exp":9999999999}
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function renderPage() {
  // Seed a token so AuthProvider sees role without any API call
  tokenStore.setAccess(FAKE_TOKEN);
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <IngresosListaPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const MOCK_PACIENTE = {
  id: 42,
  rut: "12.345.678-9",
  nombre: "María González",
  sexo: "F",
  edad: 35,
  region: "Metropolitana",
  comuna: "Santiago",
  telefono: "+56912345678",
  correo: "mgonzalez@example.com",
};

describe("IngresosListaPage", () => {
  it("muestra el prompt de búsqueda cuando q está vacío", async () => {
    renderPage();
    expect(
      await screen.findByText(/Escribe un RUT, folio o nombre para buscar pacientes/i)
    ).toBeInTheDocument();
  });

  it("tiene el placeholder exacto requerido", () => {
    renderPage();
    expect(
      screen.getByPlaceholderText("Buscar por RUT, folio o nombre")
    ).toBeInTheDocument();
  });

  it("muestra el botón 'Nuevo ingreso' para Coordinacion", async () => {
    renderPage();
    expect(await screen.findByRole("button", { name: /Nuevo ingreso/i })).toBeInTheDocument();
  });

  it("busca y muestra el paciente encontrado", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("q")) {
          return HttpResponse.json([MOCK_PACIENTE]);
        }
        return HttpResponse.json([]);
      })
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "María");

    await waitFor(() => {
      expect(screen.getByText("María González")).toBeInTheDocument();
    });

    // RUT rendered in mono
    expect(screen.getByText("12.345.678-9")).toBeInTheDocument();
    // Región
    expect(screen.getByText("Metropolitana")).toBeInTheDocument();
  });

  it("muestra 'Sin resultados.' cuando la búsqueda no devuelve nada", async () => {
    server.use(
      http.get(`${BASE}/api/v1/pacientes/buscar`, () => HttpResponse.json([]))
    );

    renderPage();
    const input = screen.getByPlaceholderText("Buscar por RUT, folio o nombre");
    await userEvent.type(input, "XYZ no existe");

    await waitFor(() => {
      expect(screen.getByText(/Sin resultados/i)).toBeInTheDocument();
    });
  });
});
