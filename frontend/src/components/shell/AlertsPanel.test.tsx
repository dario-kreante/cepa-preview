import { describe, expect, it } from "vitest";
import { routeForCaso } from "./AlertsPanel";

describe("routeForCaso", () => {
  it("enruta EPT con deep-link por caso_id", () => {
    expect(routeForCaso("ept", 42)).toBe("/ept?caso=42");
  });

  it("EPT sin caso_id cae a la página del módulo", () => {
    expect(routeForCaso("ept", null)).toBe("/ept");
  });

  it("mapea cada caso_tipo a su módulo", () => {
    expect(routeForCaso("control_medico", 1)).toBe("/controles");
    expect(routeForCaso("receta", 1)).toBe("/farmacos");
    expect(routeForCaso("licencia", 1)).toBe("/licencias");
    expect(routeForCaso("oda", 1)).toBe("/ingresos");
    expect(routeForCaso("ingreso", 1)).toBe("/ingresos");
  });

  it("tipo desconocido o nulo cae a /ingresos", () => {
    expect(routeForCaso("otro", 1)).toBe("/ingresos");
    expect(routeForCaso(null, null)).toBe("/ingresos");
  });
});
