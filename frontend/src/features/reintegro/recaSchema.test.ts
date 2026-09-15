import { describe, it, expect } from "vitest";
import { TIPO_RECA_LABELS, TIPO_RECA_VALUES } from "./recaSchema";

// Decisiones v5 D20: catálogo de calificación RECA.
describe("catálogo de tipo de RECA", () => {
  it("ofrece EP · EC · AT · AC · NPE · No aplica", () => {
    expect([...TIPO_RECA_VALUES].sort()).toEqual(
      ["AC", "AT", "EC", "EP", "NPE", "no_aplica"].sort(),
    );
  });

  it("rotula cada valor en el lenguaje del CEPA", () => {
    expect(TIPO_RECA_LABELS.EC).toBe("Enfermedad común (EC)");
    expect(TIPO_RECA_LABELS.AC).toBe("Accidente común (AC)");
    expect(TIPO_RECA_LABELS.no_aplica).toBe("No aplica");
  });
});
