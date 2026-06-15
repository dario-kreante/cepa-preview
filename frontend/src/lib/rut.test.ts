import { describe, expect, it } from "vitest";
import { rutValido } from "./rut";

describe("rutValido", () => {
  it("acepta RUT con DV correcto", () => {
    expect(rutValido("11.111.111-1")).toBe(true);
    expect(rutValido("7.876.543-7")).toBe(true);
  });
  it("rechaza DV incorrecto", () => {
    expect(rutValido("11.111.111-2")).toBe(false);
    expect(rutValido("abc")).toBe(false);
  });
});
