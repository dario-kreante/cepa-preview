import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "@/lib/auth/AuthContext";
import { LoginPage } from "./LoginPage";

function renderLogin(search = "") {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[`/login${search}`]}>
        <LoginPage />
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("LoginPage — avisos del SSO", () => {
  it("explica que el acceso institucional no está habilitado", () => {
    renderLogin("?sso_error=no_configurado");

    const aviso = screen.getByRole("alert");
    expect(aviso).toHaveTextContent(/no está habilitado/i);
  });

  it("avisa cuando la autenticación institucional falla", () => {
    renderLogin("?sso_error=autenticacion_fallida");

    const aviso = screen.getByRole("alert");
    expect(aviso).toHaveTextContent(/no pudimos validar/i);
  });

  it("avisa cuando no se pudo completar el canje de la sesión institucional", () => {
    renderLogin("?sso_error=canje_fallido");

    const aviso = screen.getByRole("alert");
    expect(aviso).toHaveTextContent(/no pudimos completar el inicio de sesión/i);
  });

  it("no muestra ningún aviso en una entrada normal", () => {
    renderLogin();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
