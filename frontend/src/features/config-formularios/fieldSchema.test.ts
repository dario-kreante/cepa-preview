import { describe, expect, it } from "vitest";
import {
  EMPTY_ROW,
  SYSTEM_FIELD_KEYS,
  missingSystemRows,
  rowToFieldDefIn,
  type FieldRow,
} from "./fieldSchema";

describe("missingSystemRows", () => {
  it("devuelve los 7 campos de sistema cuando no hay ninguno", () => {
    const faltantes = missingSystemRows([]);
    expect(faltantes.map((f) => f.field_key)).toEqual(SYSTEM_FIELD_KEYS);
    expect(faltantes.every((f) => f.system_locked && f.active)).toBe(true);
  });

  it("no duplica los que ya están presentes", () => {
    const existing: FieldRow[] = [
      { ...EMPTY_ROW, field_key: "edad", field_type: "number" },
    ];
    const faltantes = missingSystemRows(existing);
    expect(faltantes.some((f) => f.field_key === "edad")).toBe(false);
    expect(faltantes).toHaveLength(SYSTEM_FIELD_KEYS.length - 1);
  });
});

describe("rowToFieldDefIn", () => {
  it("convierte domain_values_text a lista solo para tipo select", () => {
    const row: FieldRow = {
      ...EMPTY_ROW,
      field_key: "nivel",
      label: "Nivel",
      field_type: "select",
      domain_values_text: "alto, medio , bajo",
    };
    expect(rowToFieldDefIn(row, 0).domain_values).toEqual([
      "alto",
      "medio",
      "bajo",
    ]);
  });

  it("domain_values es null para tipos no-select", () => {
    const row: FieldRow = {
      ...EMPTY_ROW,
      field_key: "nombre",
      label: "Nombre",
      field_type: "text",
      domain_values_text: "ignorado",
    };
    expect(rowToFieldDefIn(row, 0).domain_values).toBeNull();
  });
});
