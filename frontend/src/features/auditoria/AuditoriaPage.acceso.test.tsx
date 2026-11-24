/** CA-012 (QA 23-11-2026): un Administrativo con «Acceso a Auditoría» ve el menú y la página. */
import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { Sidebar } from "@/components/shell/Sidebar";
import { TOKENS } from "@/test/tokens";
import { AuditoriaPage } from "./AuditoriaPage";

function renderCon(token: string, ui: React.ReactNode) {
  tokenStore.setAccess(token);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const sidebar = <Sidebar collapsed={false} onToggleCollapse={() => {}} />;

afterEach(() => tokenStore.clear());

describe("Acceso a Auditoría (CA-012)", () => {
  it("Administrativo sin el permiso no ve Auditoría en el menú", () => {
    renderCon(TOKENS.Administrativo, sidebar);
    expect(screen.queryByRole("link", { name: /^Auditoría$/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Seguimiento reintegro/ })).toBeInTheDocument();
  });

  it("Administrativo con el permiso ve Auditoría en el menú", () => {
    renderCon(TOKENS.AdministrativoConAuditoria, sidebar);
    expect(screen.getByRole("link", { name: /^Auditoría$/ })).toBeInTheDocument();
  });

  it("Auditor sigue viendo Auditoría en el menú", () => {
    renderCon(TOKENS.Auditor, sidebar);
    expect(screen.getByRole("link", { name: /^Auditoría$/ })).toBeInTheDocument();
  });

  it("la página bloquea al Administrativo sin el permiso", () => {
    renderCon(TOKENS.Administrativo, <AuditoriaPage />);
    expect(screen.getByText(/restringido a perfiles Coordinación y/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Auditoría" })).not.toBeInTheDocument();
  });

  it("la página se abre para el Administrativo con el permiso", () => {
    renderCon(TOKENS.AdministrativoConAuditoria, <AuditoriaPage />);
    expect(screen.getByRole("heading", { name: "Auditoría" })).toBeInTheDocument();
    expect(screen.queryByText(/restringido a perfiles/)).not.toBeInTheDocument();
  });
});
