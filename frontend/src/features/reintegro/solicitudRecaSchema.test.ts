import { describe, expect, it } from "vitest";
import { hoyChile, validarFechaSolicitud } from "./solicitudRecaSchema";

describe("validarFechaSolicitud (QA-003)", () => {
  const caso = "2026-11-10";
  const hoy = "2026-11-18";

  it("acepta una fecha entre la del caso y hoy, ambos extremos incluidos", () => {
    expect(validarFechaSolicitud("2026-11-12", caso, hoy)).toBeNull();
    expect(validarFechaSolicitud(caso, caso, hoy)).toBeNull();
    expect(validarFechaSolicitud(hoy, caso, hoy)).toBeNull();
  });

  it("rechaza una fecha futura", () => {
    expect(validarFechaSolicitud("2026-11-19", caso, hoy)).toBe("La fecha de solicitud no puede ser futura.");
  });

  it("rechaza una fecha anterior a la del caso y la nombra en dd-mm-aaaa", () => {
    expect(validarFechaSolicitud("2026-11-09", caso, hoy)).toBe(
      "La fecha de solicitud no puede ser anterior a la fecha del caso (10-11-2026).",
    );
  });

  it("pide la fecha si viene vacía", () => {
    expect(validarFechaSolicitud("", caso, hoy)).toMatch(/Indica la fecha/);
  });
});

describe("hoyChile", () => {
  it("usa la fecha de Chile, no la UTC (de noche UTC ya es el día siguiente)", () => {
    // 2026-11-18 23:30 en Santiago (UTC-3) = 2026-11-19 02:30 UTC.
    expect(hoyChile(new Date("2026-11-19T02:30:00Z"))).toBe("2026-11-18");
  });
});
