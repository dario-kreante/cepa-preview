import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { Topbar } from "./Topbar";

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{pathname + search}</p>;
}

function renderTopbar(alertasSinLeer = 0, ruta = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[ruta]}>
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
  it("el ícono (?) abre la guía de la pantalla actual", async () => {
    renderTopbar(0, "/licencias");
    const ayuda = screen.getByRole("link", { name: "Ayuda sobre esta pantalla" });
    expect(ayuda).toHaveAttribute("title", "Ayuda sobre esta pantalla");
    await userEvent.click(ayuda);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/ayuda\?guia=%2Flicencias$/);
  });

  it("en una subruta usa la guía de su pantalla", () => {
    renderTopbar(0, "/ingresos/nuevo");
    expect(screen.getByRole("link", { name: "Ayuda sobre esta pantalla" })).toHaveAttribute(
      "href",
      "/ayuda?guia=%2Fingresos",
    );
  });

  it("dentro de la ayuda el ícono lleva a la portada", () => {
    renderTopbar(0, "/ayuda");
    expect(screen.getByRole("link", { name: "Ayuda" })).toHaveAttribute("href", "/ayuda");
  });
});
