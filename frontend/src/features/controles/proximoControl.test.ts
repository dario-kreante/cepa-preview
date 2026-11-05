import { describe, expect, it } from "vitest";
import { proximoAgendadoVigente } from "./proximoControl";

const HOY = "2026-11-05";

describe("proximoAgendadoVigente", () => {
  it("un próximo control agendado para hoy o más adelante sigue vigente", () => {
    expect(proximoAgendadoVigente({ proximo_agendado: true, proximo_control: HOY }, HOY)).toBe(true);
    expect(proximoAgendadoVigente({ proximo_agendado: true, proximo_control: "2026-11-06" }, HOY)).toBe(true);
  });

  it("un próximo control con fecha pasada ya no está agendado (QA-003)", () => {
    expect(proximoAgendadoVigente({ proximo_agendado: true, proximo_control: "2022-10-10" }, HOY)).toBe(false);
  });

  it("sin agenda o sin fecha no hay próximo control vigente", () => {
    expect(proximoAgendadoVigente({ proximo_agendado: false, proximo_control: "2026-12-01" }, HOY)).toBe(false);
    expect(proximoAgendadoVigente({ proximo_agendado: true, proximo_control: null }, HOY)).toBe(false);
  });
});
