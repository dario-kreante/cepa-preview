import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./AuthContext";
import { tokenStore } from "@/lib/tokenStore";

const BASE = import.meta.env.VITE_API_BASE_URL;
const JWT_AUDITOR =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhbmEiLCJyb2xlIjoiQXVkaXRvciIsInR5cGUiOiJhY2Nlc3MifQ." +
  "x";

beforeEach(() => {
  server.use(
    http.post(`${BASE}/api/v1/auth/login`, () =>
      HttpResponse.json({ access_token: JWT_AUDITOR, refresh_token: "r", token_type: "bearer" }),
    ),
  );
});
afterEach(() => tokenStore.clear());

function Probe() {
  const { rol, cargando, errorSesion, login } = useAuth();
  return (
    <div>
      <span>rol:{rol ?? "none"}</span>
      <span>cargando:{cargando ? "si" : "no"}</span>
      <span>error:{errorSesion ?? "none"}</span>
      <button onClick={() => login("ana", "x")}>login</button>
    </div>
  );
}

describe("AuthContext", () => {
  it("tras login expone el rol decodificado del JWT", async () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    await userEvent.click(screen.getByText("login"));
    await waitFor(() => expect(screen.getByText("rol:Auditor")).toBeInTheDocument());
  });

  it("si el servidor no responde al restaurar la sesión, deja de cargar y lo informa", async () => {
    tokenStore.setRefresh("r");
    server.use(http.post(`${BASE}/api/v1/auth/refresh`, () => HttpResponse.error()));

    render(<AuthProvider><Probe /></AuthProvider>);

    await waitFor(() => expect(screen.getByText("cargando:no")).toBeInTheDocument());
    expect(screen.getByText("error:servidor")).toBeInTheDocument();
    // El servidor está caído, no es que la sesión sea inválida: conservamos el
    // refresh token para que la sesión siga viva cuando el backend vuelva.
    expect(tokenStore.getRefresh()).toBe("r");
  });

  it("si el servidor rechaza el refresh, limpia la sesión y deja de cargar", async () => {
    tokenStore.setRefresh("r");
    server.use(
      http.post(`${BASE}/api/v1/auth/refresh`, () => new HttpResponse(null, { status: 401 })),
    );

    render(<AuthProvider><Probe /></AuthProvider>);

    await waitFor(() => expect(screen.getByText("cargando:no")).toBeInTheDocument());
    expect(screen.getByText("rol:none")).toBeInTheDocument();
    expect(screen.getByText("error:sesion")).toBeInTheDocument();
    expect(tokenStore.getRefresh()).toBeNull();
  });
});
