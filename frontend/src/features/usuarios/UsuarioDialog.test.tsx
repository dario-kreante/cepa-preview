/** CA-012 (QA 23-11-2026): casilla «Acceso a Auditoría» en el diálogo de usuario. */
import { afterEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { TOKENS } from "@/test/tokens";
import { UsuarioDialog } from "./UsuarioDialog";
import type { UsuarioRead } from "./api";

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderDialog(usuario?: UsuarioRead) {
  tokenStore.setAccess(TOKENS.Coordinacion);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <UsuarioDialog open onOpenChange={() => {}} usuario={usuario} />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const ISIDORA: UsuarioRead = {
  id: 9,
  username: "isidora",
  nombre: "Isidora",
  rol: "Administrativo",
  activo: true,
  email: null,
  acceso_auditoria: true,
  created_at: "2026-11-23T00:00:00Z",
};

afterEach(() => tokenStore.clear());

describe("UsuarioDialog — Acceso a Auditoría", () => {
  it("muestra la casilla solo cuando el rol es Administrativo", async () => {
    renderDialog();
    expect(screen.getByLabelText("Acceso a Auditoría")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Rol"), "Auditor");
    expect(screen.queryByLabelText("Acceso a Auditoría")).not.toBeInTheDocument();
  });

  it("al crear envía acceso_auditoria marcado", async () => {
    let cuerpo: Record<string, unknown> | null = null;
    server.use(
      http.post(`${BASE}/api/v1/usuarios`, async ({ request }) => {
        cuerpo = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...ISIDORA, id: 10 }, { status: 201 });
      }),
    );
    renderDialog();
    await userEvent.type(screen.getByLabelText("Usuario"), "isidora");
    await userEvent.type(screen.getByLabelText("Nombre completo"), "Isidora");
    await userEvent.type(screen.getByLabelText("Contraseña"), "Clave123!");
    await userEvent.click(screen.getByLabelText("Acceso a Auditoría"));
    await userEvent.click(screen.getByRole("button", { name: "Crear usuario" }));

    await waitFor(() => expect(cuerpo).not.toBeNull());
    expect(cuerpo).toMatchObject({ rol: "Administrativo", acceso_auditoria: true });
  });

  it("en edición precarga la casilla y la envía en false si se cambia a otro rol", async () => {
    let cuerpo: Record<string, unknown> | null = null;
    server.use(
      http.put(`${BASE}/api/v1/usuarios/9`, async ({ request }) => {
        cuerpo = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...ISIDORA, rol: "Auditor", acceso_auditoria: false });
      }),
    );
    renderDialog(ISIDORA);
    await waitFor(() => expect(screen.getByLabelText("Acceso a Auditoría")).toBeChecked());

    await userEvent.selectOptions(screen.getByLabelText("Rol"), "Auditor");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(cuerpo).not.toBeNull());
    expect(cuerpo).toMatchObject({ rol: "Auditor", acceso_auditoria: false });
  });
});
