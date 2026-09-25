import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { server } from "@/test/msw/server";
import { Topbar } from "./Topbar";

const BASE = import.meta.env.VITE_API_BASE_URL;

function Ubicacion() {
  const { pathname } = useLocation();
  return <p data-testid="ubicacion">{pathname}</p>;
}

function renderTopbar(alertasPendientes = 0) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/"]}>
        <Topbar
          alertsVisible={false}
          onToggleAlerts={() => {}}
          alertasPendientes={alertasPendientes}
        />
        <Routes>
          <Route path="*" element={<Ubicacion />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Topbar · píldora de ingresos activos (COMP-2609-03)", () => {
  it("muestra el conteo real de activos y lleva a Ingresos", async () => {
    server.use(
      http.get(`${BASE}/api/v1/dashboard/activos`, () => HttpResponse.json({ total: 42 })),
    );
    renderTopbar();

    const pildora = await screen.findByRole("link", { name: /42 activos/i });
    expect(screen.queryByText(/— activos/)).not.toBeInTheDocument();

    await userEvent.click(pildora);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/ingresos$/);
  });

  it("mientras carga muestra un estado de carga, no un guion", async () => {
    server.use(
      http.get(`${BASE}/api/v1/dashboard/activos`, async () => {
        await delay("infinite");
        return HttpResponse.json({ total: 1 });
      }),
    );
    renderTopbar();
    expect(screen.getByText(/Cargando activos/i)).toBeInTheDocument();
    expect(screen.queryByText(/— activos/)).not.toBeInTheDocument();
  });

  it("si la consulta falla, oculta la píldora", async () => {
    let llamado = false;
    server.use(
      http.get(`${BASE}/api/v1/dashboard/activos`, () => {
        llamado = true;
        return new HttpResponse(null, { status: 500 });
      }),
    );
    renderTopbar();
    await vi.waitFor(() => expect(llamado).toBe(true));
    await vi.waitFor(() =>
      expect(screen.queryByText(/activos/i)).not.toBeInTheDocument(),
    );
  });
});

describe("Topbar · alertas pendientes", () => {
  it("rotula el conteo como 'pendientes'", () => {
    renderTopbar(3);
    expect(screen.getByText("3 pendientes")).toBeInTheDocument();
    expect(screen.queryByText(/críticas/i)).not.toBeInTheDocument();
  });

  it("sin alertas muestra 'sin pendientes'", () => {
    renderTopbar(0);
    expect(screen.getByText("sin pendientes")).toBeInTheDocument();
  });
});

describe("Topbar · ayuda (COMP-2609-01)", () => {
  it("el ícono (?) tiene rótulo accesible y lleva a /ayuda", async () => {
    renderTopbar();
    const ayuda = screen.getByRole("link", { name: "Ayuda" });
    expect(ayuda).toHaveAttribute("title", "Ayuda");
    await userEvent.click(ayuda);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/ayuda$/);
  });
});
