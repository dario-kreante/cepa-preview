import { expect, test } from "@playwright/test";

test("login muestra credenciales inválidas y luego entra", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Usuario").fill(process.env.E2E_USER ?? "coordinador");
  await page.getByLabel("Contraseña").fill(process.env.E2E_PASS ?? "cambiar");
  await page.getByRole("button", { name: /ingresar/i }).click();
  await expect(page.getByText(/Búsqueda 360/i)).toBeVisible();
});
