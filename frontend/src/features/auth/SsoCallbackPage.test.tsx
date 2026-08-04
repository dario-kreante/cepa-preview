import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "@/test/msw/server";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { tokenStore } from "@/lib/tokenStore";
import { SsoCallbackPage } from "./SsoCallbackPage";

const BASE = import.meta.env.VITE_API_BASE_URL;

/** JWT de juguete: solo necesita claims decodificables por jwt-decode. */
function jwtFalso(payload: Record<string, unknown>) {
  const b64 = (o: unknown) => btoa(JSON.stringify(o)).replace(/=/g, "");
  return `${b64({ alg: "HS256" })}.${b64(payload)}.firma`;
}

function renderEnCallback(search: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[`/auth/callback${search}`]}>
        <Routes>
          <Route path="/auth/callback" element={<SsoCallbackPage />} />
          <Route path="/" element={<p>Inicio</p>} />
          <Route path="/login" element={<p>Pantalla de login</p>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("SsoCallbackPage", () => {
  it("canjea el código y deja la sesión iniciada", async () => {
    server.use(
      http.post(`${BASE}/api/v1/auth/saml/canjear`, async ({ request }) => {
        const body = (await request.json()) as { code: string };
        expect(body.code).toBe("codigo-abc");
        return HttpResponse.json({
          access_token: jwtFalso({
            sub: "8", username: "dramirezr", role: "Coordinacion",
            type: "access", exp: Math.floor(Date.now() / 1000) + 900,
          }),
          refresh_token: "refresh-xyz",
          token_type: "bearer",
        });
      }),
    );

    renderEnCallback("?code=codigo-abc");

    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());
    expect(tokenStore.getRefresh()).toBe("refresh-xyz");
  });

  it("vuelve al login si el código es inválido", async () => {
    server.use(
      http.post(`${BASE}/api/v1/auth/saml/canjear`, () =>
        HttpResponse.json({ detail: "Código inválido o expirado" }, { status: 401 }),
      ),
    );

    renderEnCallback("?code=vencido");

    await waitFor(() => expect(screen.getByText("Pantalla de login")).toBeInTheDocument());
  });

  it("no llama al backend si no viene código", async () => {
    renderEnCallback("");

    await waitFor(() => expect(screen.getByText("Pantalla de login")).toBeInTheDocument());
  });
});
