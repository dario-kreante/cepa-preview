import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import type { Rol } from "@/lib/rbac";
import { AyudaPage, URL_PORTAL_INCIDENCIAS } from "./AyudaPage";
import { GUIAS, guiaDeRuta } from "./contenido";

/** JWT sin firma válida: el frontend solo decodifica el payload para leer el rol. */
function tokenDe(rol: Rol): string {
  const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, "");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub: "1", username: "test", role: rol, type: "access", exp: 9999999999 })}.firma`;
}

function renderAyuda({ rol = "Coordinacion" as Rol, ruta = "/ayuda" } = {}) {
  tokenStore.setAccess(tokenDe(rol));
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <AuthProvider>
        <AyudaPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

const guia = (titulo: string) => screen.getByRole("button", { name: new RegExp(`^${titulo}`), expanded: false });

describe("AyudaPage (COMP-2609-01)", () => {
  it("agrupa las guías como el menú y muestra la tarjeta de SALUTEM", () => {
    renderAyuda();
    expect(screen.getByRole("heading", { name: /¿En qué te ayudamos\?/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Cómo trabaja el SIGE con SALUTEM/ })).toBeInTheDocument();
    for (const seccion of ["Módulos clínicos", "Operación", "Administración"]) {
      expect(screen.getByRole("heading", { name: seccion })).toBeInTheDocument();
    }
    expect(guia("Licencias médicas")).toBeInTheDocument();
    expect(guia("Pacientes por citar")).toBeInTheDocument();
  });

  it("muestra solo las guías de las pantallas del perfil", () => {
    renderAyuda({ rol: "Auditor" });
    expect(screen.getByText("Auditor")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Pendientes de folio/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Usuarios y roles/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Completar un folio pendiente/ })).not.toBeInTheDocument();
    expect(guia("Seguimiento EPT")).toBeInTheDocument();
  });

  it("al abrir una guía muestra los pasos, las etiquetas y el enlace a la pantalla", async () => {
    renderAyuda();
    await userEvent.click(guia("Licencias médicas"));
    const tarjeta = screen.getByRole("button", { name: /^Licencias médicas/, expanded: true }).closest("[id]")!;
    expect(within(tarjeta as HTMLElement).getByText("Registrar una licencia")).toBeInTheDocument();
    expect(within(tarjeta as HTMLElement).getByText("Anulada")).toBeInTheDocument();
    expect(within(tarjeta as HTMLElement).getByText(/Llega solo desde SALUTEM/)).toBeInTheDocument();
    expect(within(tarjeta as HTMLElement).getByRole("link", { name: /Ir a Licencias médicas/ })).toHaveAttribute(
      "href",
      "/licencias",
    );
  });

  it("abre la guía pedida por el Topbar con ?guia=", () => {
    renderAyuda({ ruta: "/ayuda?guia=%2Fagenda" });
    expect(screen.getByRole("button", { name: /^Pacientes por citar/, expanded: true })).toBeInTheDocument();
    expect(screen.getByText("Trabajar la lista del día")).toBeInTheDocument();
  });

  it("un acceso rápido abre su guía", async () => {
    renderAyuda();
    await userEvent.click(screen.getByRole("button", { name: /Citar pacientes/ }));
    expect(screen.getByRole("button", { name: /^Pacientes por citar/, expanded: true })).toBeInTheDocument();
  });

  it("la búsqueda ignora tildes y recorre guías, preguntas y glosario", async () => {
    renderAyuda();
    await userEvent.type(screen.getByRole("textbox", { name: "Buscar en la ayuda" }), "farmacos");
    expect(screen.getByText(/resultados? para «farmacos»/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Gestión de fármacos/ })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Glosario" })).not.toBeInTheDocument();

    await userEvent.clear(screen.getByRole("textbox", { name: "Buscar en la ayuda" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Buscar en la ayuda" }), "xyzzy");
    expect(screen.getByText(/No encontramos nada sobre «xyzzy»/)).toBeInTheDocument();
  });

  it("las preguntas frecuentes y el glosario están en sus pestañas", async () => {
    renderAyuda();
    await userEvent.click(screen.getByRole("tab", { name: "Preguntas frecuentes" }));
    expect(screen.getByText(/¿El SIGE modifica datos en SALUTEM\?/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Glosario" }));
    expect(screen.getByText("ID SALUTEM")).toBeInTheDocument();
  });

  it("enlaza al portal de incidencias en pestaña nueva", () => {
    renderAyuda();
    const enlace = screen.getByRole("link", { name: /Reportar un problema/i });
    expect(enlace).toHaveAttribute("href", URL_PORTAL_INCIDENCIAS);
    expect(URL_PORTAL_INCIDENCIAS).toBe("https://cepa-incidencias.dramirez-gysactiva.chatgpt.site");
    expect(enlace).toHaveAttribute("target", "_blank");
    expect(enlace.getAttribute("rel")).toMatch(/noopener/);
  });
});

describe("guiaDeRuta", () => {
  it("resuelve la pantalla de la ruta actual", () => {
    expect(guiaDeRuta("/")).toBe("/");
    expect(guiaDeRuta("/licencias")).toBe("/licencias");
    expect(guiaDeRuta("/ingresos/nuevo")).toBe("/ingresos");
    expect(guiaDeRuta("/ingresosx")).toBeUndefined();
    expect(guiaDeRuta("/ayuda")).toBeUndefined();
  });

  it("cada guía corresponde a una pantalla del menú", async () => {
    const { NAV } = await import("@/app/shell/nav");
    const rutas = new Set(["/", ...NAV.flatMap((s) => s.items.map((i) => i.to))]);
    for (const g of GUIAS) expect(rutas).toContain(g.ruta);
  });
});
