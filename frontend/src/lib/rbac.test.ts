import { describe, expect, it } from "vitest";
import { puedeEscribir, puedeEscribirEpt } from "./rbac";

describe("rbac", () => {
  it("Administrativo y Coordinacion pueden escribir; Auditor no", () => {
    expect(puedeEscribir("Administrativo")).toBe(true);
    expect(puedeEscribir("Coordinacion")).toBe(true);
    expect(puedeEscribir("Auditor")).toBe(false);
  });
});

describe("puedeEscribirEpt", () => {
  it("solo Administrativo puede escribir EPT", () => {
    expect(puedeEscribirEpt("Administrativo")).toBe(true);
    expect(puedeEscribirEpt("Coordinacion")).toBe(false);
    expect(puedeEscribirEpt("Auditor")).toBe(false);
    expect(puedeEscribirEpt(null)).toBe(false);
    expect(puedeEscribirEpt(undefined)).toBe(false);
  });
});
