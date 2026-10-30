import { describe, expect, it } from "vitest";
import { fechaLocalISO, fmtRelativo } from "./utils";

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

describe("fechaLocalISO", () => {
  it("usa la fecha local, no la UTC (D13)", () => {
    // 23:30 del 30-10 en hora local: en UTC ya sería 31-10 en Chile.
    expect(fechaLocalISO(new Date(2026, 9, 30, 23, 30))).toBe("2026-10-30");
    expect(fechaLocalISO(new Date(2026, 0, 5, 0, 5))).toBe("2026-01-05");
  });
});
