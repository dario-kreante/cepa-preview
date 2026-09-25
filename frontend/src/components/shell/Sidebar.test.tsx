import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { Sidebar } from "./Sidebar";

// Payload: {"sub":"1","username":"test","role":"Coordinacion","type":"access","exp":9999999999}
const FAKE_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0Iiwicm9sZSI6IkNvb3JkaW5hY2lvbiIsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjk5OTk5OTk5OTl9." +
  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{pathname + search}</p>;
}

function renderSidebar(collapsed = false) {
  tokenStore.setAccess(FAKE_TOKEN);
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <AuthProvider>
        <Sidebar collapsed={collapsed} onToggleCollapse={() => {}} />
        <Routes>
          <Route path="*" element={<Ubicacion />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("Sidebar · buscador", () => {
  it("con Enter lleva a Ingresos con el término", async () => {
    renderSidebar();
    const input = screen.getByRole("searchbox", { name: /buscar pacientes/i });

    await userEvent.type(input, "sin_id_1216018{Enter}");

    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/ingresos?q=sin_id_1216018");
    expect(input).toHaveValue("");
  });

  it("no navega con el término vacío", async () => {
    renderSidebar();
    const input = screen.getByRole("searchbox", { name: /buscar pacientes/i });

    await userEvent.type(input, "   {Enter}");

    expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/$/);
  });
});

describe("Sidebar · ayuda y configuración", () => {
  it.each([false, true])(
    "'Ayuda y soporte' lleva a /ayuda (colapsado: %s)",
    async (collapsed) => {
      renderSidebar(collapsed);
      await userEvent.click(screen.getByRole("link", { name: /Ayuda y soporte/i }));
      expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/ayuda$/);
    },
  );

  it.each([false, true])(
    "'Configuración' lleva a /configuracion (colapsado: %s)",
    async (collapsed) => {
      renderSidebar(collapsed);
      await userEvent.click(screen.getByRole("link", { name: /Configuración/i }));
      expect(screen.getByTestId("ubicacion")).toHaveTextContent(/^\/configuracion$/);
    },
  );

  it("con el menú colapsado los botones tienen tooltip", () => {
    renderSidebar(true);
    expect(screen.getByRole("link", { name: /Ayuda y soporte/i })).toHaveAttribute(
      "title",
      "Ayuda y soporte",
    );
    expect(screen.getByRole("link", { name: /Configuración/i })).toHaveAttribute(
      "title",
      "Configuración",
    );
  });
});
