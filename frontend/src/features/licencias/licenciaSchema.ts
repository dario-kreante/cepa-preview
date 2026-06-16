/**
 * Zod schema for the "Alta de licencia" form.
 *
 * Contract: `LicenciaCreate` (backend) requires `ingreso_id` (integer), NOT folio.
 * The form therefore includes an ingreso_id field that is:
 *   - pre-populated (hidden / read-only) when the page already knows it from the
 *     fetched historial (first row's full detail ingreso_id); or
 *   - visible and user-entered when no prior licencias exist for the folio.
 *
 * Enum values (backend exact literals):
 *   tipo_lm:  "1" | "5" | "6"            (app__domain__enums_licencia__TipoLicencia)
 *   tipo_reposo: "total" | "parcial"     (app__domain__enums_licencia__TipoReposo)
 *   origen:   "sistema" | "extra_sistema" (OrigenLicencia)
 */
import { z } from "zod";

export const TIPO_LM_VALUES = ["1", "5", "6"] as const;
export const TIPO_REPOSO_VALUES = ["total", "parcial"] as const;
export const ORIGEN_VALUES = ["sistema", "extra_sistema"] as const;

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const licenciaSchema = z
  .object({
    ingreso_id: z
      .number({ required_error: "Ingreso ID requerido", invalid_type_error: "Debe ser un número" })
      .int("Debe ser entero")
      .positive("Debe ser positivo"),

    folio_lm: z.string().trim().optional().or(z.literal("")),

    tipo_lm: z.enum(TIPO_LM_VALUES, {
      required_error: "Tipo de licencia requerido",
    }),

    tipo_reposo: z.enum(TIPO_REPOSO_VALUES, {
      required_error: "Tipo de reposo requerido",
    }),

    fecha_inicio: isoDate,
    fecha_termino: isoDate,
    fecha_emision: isoDate,
    inicio_reposo: isoDate,
    fin_reposo: isoDate,

    cantidad_dias: z
      .number({ required_error: "Cantidad de días requerida", invalid_type_error: "Debe ser un número" })
      .int("Debe ser entero")
      .min(1, "Mínimo 1 día"),

    indicacion_reposo: z.string().trim().optional().or(z.literal("")),

    diagnostico: z
      .string()
      .trim()
      .min(3, "Diagnóstico requerido (mínimo 3 caracteres)"),

    origen: z.enum(ORIGEN_VALUES).default("sistema"),
  })
  .refine(
    (d) => d.fecha_termino >= d.fecha_inicio,
    {
      message: "La fecha de término debe ser igual o posterior a la fecha de inicio",
      path: ["fecha_termino"],
    },
  )
  .refine(
    (d) => d.fin_reposo >= d.inicio_reposo,
    {
      message: "El fin de reposo debe ser igual o posterior al inicio de reposo",
      path: ["fin_reposo"],
    },
  );

export type LicenciaForm = z.infer<typeof licenciaSchema>;
