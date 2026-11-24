import { describe, expect, it } from "vitest";
import { puedeEscribir, puedeEscribirEpt, puedeVerAuditoria, tieneRol } from "./rbac";

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

describe("Superadmin", () => {
  it("tiene todos los permisos", () => {
    expect(puedeEscribir("Superadmin")).toBe(true);
    expect(puedeEscribirEpt("Superadmin")).toBe(true);
    expect(tieneRol("Superadmin", "Coordinacion")).toBe(true);
    expect(tieneRol("Superadmin", "Administrativo")).toBe(true);
  });

  it("los demás roles solo pasan con su propio rol", () => {
    expect(tieneRol("Coordinacion", "Administrativo")).toBe(false);
    expect(tieneRol("Administrativo", "Administrativo")).toBe(true);
    expect(tieneRol(null, "Coordinacion")).toBe(false);
  });
});

describe("puedeVerAuditoria (CA-012)", () => {
  it("Coordinación, Auditor y Superadmin por rol", () => {
    expect(puedeVerAuditoria("Coordinacion")).toBe(true);
    expect(puedeVerAuditoria("Auditor")).toBe(true);
    expect(puedeVerAuditoria("Superadmin")).toBe(true);
  });

  it("Administrativo solo con el permiso extra", () => {
    expect(puedeVerAuditoria("Administrativo")).toBe(false);
    expect(puedeVerAuditoria("Administrativo", true)).toBe(true);
    expect(puedeVerAuditoria(null, true)).toBe(false);
  });
});
