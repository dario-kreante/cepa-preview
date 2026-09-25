import { describe, it, expect } from "vitest";
import { ingresoSchema } from "./ingresoSchema";

const VALIDO = {
  rut: "39.000.001-4",
  nombre: "Paciente Prueba",
  sexo: "F",
  edad: "45",
  region: "Maule",
  diagnostico: "x",
  tipo_derivacion: "DIEP",
  tipo_ingreso: "convenio",
  modelo_tratamiento: "ambulatorio",
  fecha_ingreso: "2022-06-01",
};

function mensajes(datos: Record<string, unknown>) {
  const r = ingresoSchema.safeParse(datos);
  return r.success ? {} : r.error.flatten().fieldErrors;
}

describe("ingresoSchema · mensajes en español", () => {
  it("un RUT vacío pide el dato; uno mal escrito dice que es inválido", () => {
    expect(mensajes({ ...VALIDO, rut: "" }).rut).toEqual(["Requerido"]);
    expect(mensajes({ ...VALIDO, rut: "12.345.678-0" }).rut).toEqual(["RUT inválido"]);
  });

  it("la edad explica el rango en español", () => {
    expect(mensajes({ ...VALIDO, edad: "" }).edad).toEqual(["Requerido"]);
    expect(mensajes({ ...VALIDO, edad: "0" }).edad).toEqual(["La edad debe estar entre 1 y 130"]);
    expect(mensajes({ ...VALIDO, edad: "200" }).edad).toEqual(["La edad debe estar entre 1 y 130"]);
    expect(mensajes({ ...VALIDO, edad: "4.5" }).edad).toEqual(["La edad debe ser un número entero"]);
  });

  it("un ingreso completo es válido", () => {
    expect(ingresoSchema.safeParse(VALIDO).success).toBe(true);
  });
});
