import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/lib/auth/AuthContext";
import { LoginPage } from "./LoginPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderLogin() {
  return render(
    <AuthProvider>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("LoginPage — acceso institucional", () => {
  beforeEach(() => {
    // El botón navega fuera de la SPA; en jsdom se intercepta la asignación.
    vi.stubGlobal("location", { ...window.location, assign: vi.fn(), href: "" });
  });

  it("ofrece iniciar sesión con la cuenta UTalca", () => {
    renderLogin();

    expect(
      screen.getByRole("button", { name: /cuenta utalca/i }),
    ).toBeInTheDocument();
  });

  it("envía al usuario al inicio de sesión institucional del backend", async () => {
    renderLogin();

    await userEvent.click(screen.getByRole("button", { name: /cuenta utalca/i }));

    // El backend decide el método (SAML o huemul) según la configuración del entorno.
    expect(window.location.href).toBe(`${BASE}/api/v1/auth/sso/login`);
  });
});
