import { expect, test } from "@playwright/test";

test("crea un ingreso y lo ve en la vista 360", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Usuario").fill(process.env.E2E_USER ?? "coordinador");
  await page.getByLabel("Contraseña").fill(process.env.E2E_PASS ?? "cambiar");
  await page.getByRole("button", { name: /ingresar/i }).click();
  await page.getByRole("link", { name: /nuevo ingreso/i }).click();
  await page.getByLabel("RUT").fill("7.876.543-7");
  await page.getByLabel("Nombre").fill("Paciente E2E");
  await page.getByLabel("Edad").fill("40");
  await page.getByLabel("Región").fill("Maule");
  await page.getByLabel("Diagnóstico").fill("Prueba E2E");
  await page.getByLabel("Modelo de tratamiento").fill("ambulatorio");
  await page.getByLabel("Fecha de ingreso").fill("2026-06-01");
  await page.getByRole("button", { name: /crear ingreso/i }).click();
  // Tras el alta exitosa, la app navega a la vista 360 del paciente.
  // Verificamos el destino (no el toast transitorio, que compite con el redirect).
  await expect(page).toHaveURL(/\/pacientes\/\d+$/);
  await expect(page.getByRole("heading", { name: /Paciente E2E/i })).toBeVisible();
});
