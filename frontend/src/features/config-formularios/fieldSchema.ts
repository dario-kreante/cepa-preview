/**
 * Zod schema del editor de campos de un formulario dinámico (CEPA-110/111).
 * `domain_values` se edita como texto separado por comas (para tipo "select").
 * field_type "" se permite en borrador; el backend lo valida al publicar.
 */
import { z } from "zod";
import { FIELD_TYPES, type FieldDefIn } from "./api";

export const fieldRowSchema = z.object({
  field_key: z
    .string()
    .trim()
    .min(1, "Requerido")
    .regex(/^[a-z0-9_]+$/, "Solo minúsculas, números y _"),
  label: z.string().trim().min(1, "Requerido"),
  field_type: z.enum(["", ...FIELD_TYPES] as [string, ...string[]]),
  required: z.boolean().default(false),
  active: z.boolean().default(true),
  system_locked: z.boolean().default(false),
  display_order: z.coerce.number().int().min(0).default(0),
  // Texto separado por comas; obligatorio (no vacío) cuando field_type === "select".
  domain_values_text: z.string().default(""),
});

export const editorSchema = z
  .object({
    fields: z.array(fieldRowSchema).min(1, "Agrega al menos un campo"),
  })
  .superRefine((val, ctx) => {
    const keys = new Set<string>();
    val.fields.forEach((f, i) => {
      if (keys.has(f.field_key)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "field_key duplicado",
          path: ["fields", i, "field_key"],
        });
      }
      keys.add(f.field_key);
      if (f.field_type === "select" && !f.domain_values_text.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Define valores para el tipo Selección",
          path: ["fields", i, "domain_values_text"],
        });
      }
    });
  });

export type FieldRow = z.infer<typeof fieldRowSchema>;
export type EditorForm = z.infer<typeof editorSchema>;

/** Convierte una fila del editor al payload de la API. */
export function rowToFieldDefIn(row: FieldRow, index: number): FieldDefIn {
  const domain =
    row.field_type === "select"
      ? row.domain_values_text
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : null;
  return {
    field_key: row.field_key,
    label: row.label,
    field_type: row.field_type,
    required: row.required,
    system_locked: row.system_locked,
    domain_values: domain,
    display_order: row.display_order || index,
    active: row.active,
  };
}

export const EMPTY_ROW: FieldRow = {
  field_key: "",
  label: "",
  field_type: "text",
  required: false,
  active: true,
  system_locked: false,
  display_order: 0,
  domain_values_text: "",
};

/**
 * Campos de sistema obligatorios que el validador del backend exige en TODA
 * versión publicada (con system_locked=true y activos). Tipos por defecto que
 * pasan la validación sin requerir domain_values.
 */
const SYSTEM_FIELD_DEFS: { key: string; label: string; type: FieldRow["field_type"] }[] = [
  { key: "sexo", label: "Sexo", type: "text" },
  { key: "edad", label: "Edad", type: "number" },
  { key: "diagnostico", label: "Diagnóstico", type: "text" },
  { key: "modelo_trat", label: "Modelo de tratamiento", type: "text" },
  { key: "tipo_alta", label: "Tipo de alta", type: "text" },
  { key: "tipo_ingreso", label: "Tipo de ingreso", type: "text" },
  { key: "tipo_convenio", label: "Tipo de convenio", type: "text" },
];

export const SYSTEM_FIELD_KEYS = SYSTEM_FIELD_DEFS.map((d) => d.key);

/** Filas de los campos de sistema que falten en `existing` (por field_key). */
export function missingSystemRows(existing: FieldRow[]): FieldRow[] {
  const present = new Set(existing.map((f) => f.field_key));
  return SYSTEM_FIELD_DEFS.filter((d) => !present.has(d.key)).map((d, i) => ({
    field_key: d.key,
    label: d.label,
    field_type: d.type,
    required: true,
    active: true,
    system_locked: true,
    display_order: existing.length + i,
    domain_values_text: "",
  }));
}
