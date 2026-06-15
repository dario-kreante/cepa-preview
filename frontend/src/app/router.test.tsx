import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { ProtectedRoute } from "./router";

function wrap(initial: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/login" element={<div>login-page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<div>home-protegido</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("ProtectedRoute", () => {
  it("sin sesión redirige a /login", async () => {
    wrap("/");
    expect(await screen.findByText("login-page")).toBeInTheDocument();
  });
});
