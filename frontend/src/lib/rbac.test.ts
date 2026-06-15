import { describe, expect, it } from "vitest";
import { puedeEscribir } from "./rbac";

describe("rbac", () => {
  it("Administrativo y Coordinacion pueden escribir; Auditor no", () => {
    expect(puedeEscribir("Administrativo")).toBe(true);
    expect(puedeEscribir("Coordinacion")).toBe(true);
    expect(puedeEscribir("Auditor")).toBe(false);
  });
});
