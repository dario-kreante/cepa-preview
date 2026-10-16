import { describe, expect, it } from "vitest";
import { fmtRelativo } from "./utils";

const AHORA = new Date("2026-10-16T12:00:00Z");

describe("fmtRelativo", () => {
  it("formatea minutos, horas, días y meses", () => {
    expect(fmtRelativo("2026-10-16T11:55:00Z", AHORA)).toBe("hace 5 min");
    expect(fmtRelativo("2026-10-16T09:00:00Z", AHORA)).toBe("hace 3 horas");
    expect(fmtRelativo("2026-10-15T12:00:00Z", AHORA)).toBe("hace 1 día");
    expect(fmtRelativo("2026-08-16T12:00:00Z", AHORA)).toBe("hace 2 meses");
  });
  it("asume UTC cuando no hay zona y tolera vacíos", () => {
    expect(fmtRelativo("2026-10-16T11:00:00", AHORA)).toBe("hace 1 hora");
    expect(fmtRelativo(null, AHORA)).toBe("—");
  });
});
