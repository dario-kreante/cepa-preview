import { describe, expect, it } from "vitest";
import { mensajeDelBackend } from "./apiError";

describe("mensajeDelBackend", () => {
  it("usa el detail en texto que manda el backend", () => {
    const error = { detail: "Para un reintegro total, elige el tipo de alta." };
    expect(mensajeDelBackend(error, "genérico")).toBe(
      "Para un reintegro total, elige el tipo de alta.",
    );
  });

  it("usa el respaldo si el detail es la lista de errores de esquema", () => {
    const error = { detail: [{ loc: ["body", "x"], msg: "Field required" }] };
    expect(mensajeDelBackend(error, "genérico")).toBe("genérico");
  });

  it("usa el respaldo si no hay error o viene vacío", () => {
    expect(mensajeDelBackend(undefined, "genérico")).toBe("genérico");
    expect(mensajeDelBackend({ detail: "  " }, "genérico")).toBe("genérico");
  });
});
