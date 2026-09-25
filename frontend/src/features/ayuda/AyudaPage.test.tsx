import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AyudaPage, URL_PORTAL_INCIDENCIAS } from "./AyudaPage";

describe("AyudaPage (COMP-2609-01)", () => {
  it("muestra las secciones del manual de uso", () => {
    render(
      <MemoryRouter>
        <AyudaPage />
      </MemoryRouter>,
    );
    for (const titulo of [
      /Buscar un paciente/i,
      /Crear un ingreso/i,
      /Registrar una licencia/i,
      /Controles médicos/i,
      /Gestión de fármacos/i,
      /alertas/i,
    ]) {
      expect(screen.getByRole("heading", { name: titulo })).toBeInTheDocument();
    }
    expect(screen.getAllByText(/ID SALUTEM/i).length).toBeGreaterThan(0);
  });

  it("enlaza al portal de incidencias en pestaña nueva", () => {
    render(
      <MemoryRouter>
        <AyudaPage />
      </MemoryRouter>,
    );
    const enlace = screen.getByRole("link", { name: /Reportar un problema/i });
    expect(enlace).toHaveAttribute("href", URL_PORTAL_INCIDENCIAS);
    expect(URL_PORTAL_INCIDENCIAS).toBe("https://cepa-incidencias.dramirez-gysactiva.chatgpt.site");
    expect(enlace).toHaveAttribute("target", "_blank");
    expect(enlace.getAttribute("rel")).toMatch(/noopener/);
  });
});
