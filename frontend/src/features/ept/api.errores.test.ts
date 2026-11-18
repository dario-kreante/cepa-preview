import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { actualizarProceso, crearPlazos } from "./api";
import { registrarCierre } from "@/features/reintegro/api";

const BASE = import.meta.env.VITE_API_BASE_URL;

// QA-003 / QA-005 (16-11): el usuario veía «No se pudo actualizar…» sin saber qué corregir.
describe("errores de EPT y reintegro muestran el motivo del backend", () => {
  it("proceso EPT", async () => {
    const motivo = "Marcaste que hay testigos: indica al menos 1 en «Cantidad de testigos».";
    server.use(
      http.patch(`${BASE}/api/v1/casos-ept/:id/proceso`, () =>
        HttpResponse.json({ detail: motivo }, { status: 422 }),
      ),
    );
    await expect(actualizarProceso(1, { hay_testigos: true, testigos_cantidad: 0 })).rejects.toThrow(
      motivo,
    );
  });

  it("plazos EPT", async () => {
    const motivo = "La fecha de entrega ISL no puede ser anterior a la fecha de ingreso EPT (30-11-2026).";
    server.use(
      http.post(`${BASE}/api/v1/casos-ept/:id/plazos`, () =>
        HttpResponse.json({ detail: motivo }, { status: 422 }),
      ),
    );
    await expect(crearPlazos(1, { caso_ept_id: 1, fecha_entrega_isl: "2026-11-03" })).rejects.toThrow(motivo);
  });

  it("cierre de reintegro", async () => {
    const motivo = "Para un reintegro total, marca el alta médica, el alta psicológica o ambas.";
    server.use(
      http.patch(`${BASE}/api/v1/reintegros/:id/cierre`, () =>
        HttpResponse.json({ detail: motivo }, { status: 422 }),
      ),
    );
    const cierre = {
      estado_reintegro: "total" as const,
      fecha_reintegro: "2026-11-07",
      remitido_isl: false,
      alta_medica: false,
      alta_psicologica: false,
    };
    await expect(registrarCierre(1, cierre)).rejects.toThrow(motivo);
  });

  it("si el backend no explica, queda el mensaje genérico", async () => {
    server.use(
      http.patch(`${BASE}/api/v1/casos-ept/:id/proceso`, () =>
        HttpResponse.json({ detail: [{ msg: "Field required" }] }, { status: 422 }),
      ),
    );
    await expect(actualizarProceso(1, {})).rejects.toThrow("No se pudo actualizar el proceso EPT");
  });
});
