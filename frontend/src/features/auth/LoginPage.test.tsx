import { afterEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { LoginPage } from "./LoginPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

afterEach(() => tokenStore.clear());

function montar() {
  return render(
    <AuthProvider>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function ingresar() {
  await userEvent.type(screen.getByLabelText("Usuario"), "ana");
  await userEvent.type(screen.getByLabelText("Contraseña"), "secreta");
  await userEvent.click(screen.getByRole("button", { name: /^ingresar$/i }));
}

describe("LoginPage", () => {
  it("con credenciales incorrectas avisa que son inválidas", async () => {
    server.use(
      http.post(`${BASE}/api/v1/auth/login`, () => new HttpResponse(null, { status: 401 })),
    );
    montar();
    await ingresar();
    expect(await screen.findByRole("alert")).toHaveTextContent(/credenciales inválidas/i);
  });

  it("si el servidor no responde no culpa a las credenciales", async () => {
    server.use(http.post(`${BASE}/api/v1/auth/login`, () => HttpResponse.error()));
    montar();
    await ingresar();
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(/servidor/i);
    expect(alerta).not.toHaveTextContent(/credenciales/i);
  });

  it("vuelve a habilitar el botón tras un fallo de red", async () => {
    server.use(http.post(`${BASE}/api/v1/auth/login`, () => HttpResponse.error()));
    montar();
    await ingresar();
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: /^ingresar$/i })).toBeEnabled();
  });
});
