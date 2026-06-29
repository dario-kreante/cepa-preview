/**
 * Zod schema for the "Licencia + GAF + RECA" form.
 *
 * Business rules (RN CEPA-062):
 *   - Cuando tiene_licencia es TRUE, los cuatro campos son REQUERIDOS:
 *       resumen_termino_lm, total_dias_lm, tipo_licencia, tipo_reposo.
 *   - gaf: opcional; si se informa, debe estar en rango 0..100.
 *   - total_dias_lm: si se informa, entero ≥ 1.
 *   - estado_reca y observaciones: siempre opcionales.
 */
import { z } from "zod";
import type { TipoLicencia, TipoReposo, EstadoReca } from "./api";

const TIPO_LICENCIA_VALUES: [TipoLicencia, ...TipoLicencia[]] = [
  "1",
  "5",
  "6",
  "3",
  "4",
  "extra_sistema",
];

const TIPO_REPOSO_VALUES: [TipoReposo, ...TipoReposo[]] = ["total", "parcial"];

const ESTADO_RECA_VALUES: [EstadoReca, ...EstadoReca[]] = [
  "pendiente",
  "aprobado",
  "rechazado",
  "en_proceso",
  "no_aplica",
];

export const licenciaControlSchema = z
  .object({
    tiene_licencia: z.boolean().default(false),

    resumen_termino_lm: z.string().optional().or(z.literal("")),

    total_dias_lm: z
      .number({ invalid_type_error: "Debe ser un número" })
      .int("Debe ser un número entero")
      .min(1, "Debe ser al menos 1")
      .optional()
      .nullable(),

    tipo_licencia: z
      .enum(TIPO_LICENCIA_VALUES, {
        invalid_type_error: "Tipo de licencia inválido",
      })
      .optional()
      .nullable(),

    tipo_reposo: z
      .enum(TIPO_REPOSO_VALUES, {
        invalid_type_error: "Tipo de reposo inválido",
      })
      .optional()
      .nullable(),

    gaf: z
      .number({ invalid_type_error: "Debe ser un número" })
      .optional()
      .nullable(),

    estado_reca: z
      .enum(ESTADO_RECA_VALUES, {
        invalid_type_error: "Estado RECA inválido",
      })
      .optional()
      .nullable(),

    observaciones: z.string().optional().or(z.literal("")),
  })
  .superRefine((d, ctx) => {
    if (d.tiene_licencia) {
      if (!d.resumen_termino_lm?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "El resumen del término de licencia médica es requerido",
          path: ["resumen_termino_lm"],
        });
      }
      if (d.total_dias_lm == null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "El total de días de licencia médica es requerido",
          path: ["total_dias_lm"],
        });
      }
      if (!d.tipo_licencia) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "El tipo de licencia es requerido",
          path: ["tipo_licencia"],
        });
      }
      if (!d.tipo_reposo) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "El tipo de reposo es requerido",
          path: ["tipo_reposo"],
        });
      }
    }
    if (d.gaf != null && (d.gaf < 0 || d.gaf > 100)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "GAF debe estar entre 0 y 100",
        path: ["gaf"],
      });
    }
  });

export type LicenciaControlForm = z.infer<typeof licenciaControlSchema>;
