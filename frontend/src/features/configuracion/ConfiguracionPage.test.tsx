import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { ConfiguracionPage } from "./ConfiguracionPage";

function renderComo(rol: keyof typeof TOKENS) {
  tokenStore.setAccess(TOKENS[rol]);
  return render(
    <MemoryRouter initialEntries={["/configuracion"]}>
      <AuthProvider>
        <ConfiguracionPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ConfiguracionPage (COMP-2609-02)", () => {
  it("Coordinación ve usuarios, formularios y ventanas de proceso", () => {
    renderComo("Coordinacion");
    expect(screen.getByRole("link", { name: /Usuarios y roles/i })).toHaveAttribute("href", "/usuarios");
    expect(screen.getByRole("link", { name: /Formularios dinámicos/i })).toHaveAttribute(
      "href",
      "/config-formularios",
    );
    expect(screen.getByRole("link", { name: /Ventanas de proceso/i })).toHaveAttribute(
      "href",
      "/ventanas-proceso",
    );
  });

  it.each(["Administrativo", "Auditor"] as const)(
    "%s solo ve ventanas de proceso",
    (rol) => {
      renderComo(rol);
      expect(screen.getByRole("link", { name: /Ventanas de proceso/i })).toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Usuarios y roles/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Formularios dinámicos/i })).not.toBeInTheDocument();
    },
  );
});
