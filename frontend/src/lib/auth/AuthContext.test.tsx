import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./AuthContext";
import { tokenStore } from "@/lib/tokenStore";

const BASE = import.meta.env.VITE_API_BASE_URL;
const JWT_AUDITOR =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhbmEiLCJyb2xlIjoiQXVkaXRvciIsInR5cGUiOiJhY2Nlc3MifQ." +
  "x";

const server = setupServer(
  http.post(`${BASE}/api/v1/auth/login`, () =>
    HttpResponse.json({ access_token: JWT_AUDITOR, refresh_token: "r", token_type: "bearer" }),
  ),
);
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); tokenStore.clear(); });
afterAll(() => server.close());

function Probe() {
  const { rol, login } = useAuth();
  return (
    <div>
      <span>rol:{rol ?? "none"}</span>
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
});
