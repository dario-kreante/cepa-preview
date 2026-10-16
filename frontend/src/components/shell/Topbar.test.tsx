import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { Topbar } from "./Topbar";

function Ubicacion() {
  const { pathname } = useLocation();
  return <p data-testid="ubicacion">{pathname}</p>;
}

function renderTopbar(alertasSinLeer = 0) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/"]}>
        <Topbar
          alertsVisible={false}
          onToggleAlerts={() => {}}
          alertasSinLeer={alertasSinLeer}
        />
        <Routes>
          <Route path="*" element={<Ubicacion />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Topbar · campana de alertas", () => {
  it("muestra en la campana cuántas alertas quedan sin leer, sin píldoras sueltas", () => {
    renderTopbar(3);
    expect(screen.getByRole("button", { name: "Alertas: 3 sin leer" })).toHaveTextContent("3");
    expect(screen.queryByText(/pendientes|activos/i)).not.toBeInTheDocument();
  });

  it("sin alertas por leer la campana no lleva número", () => {
    renderTopbar(0);
    expect(screen.getByRole("button", { name: "Alertas" })).not.toHaveTextContent(/\d/);
  });

  it("más de 99 se abrevia", () => {
    renderTopbar(140);
    expect(screen.getByRole("button", { name: /140 sin leer/ })).toHaveTextContent("99+");
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
