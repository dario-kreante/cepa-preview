/**
 * Zod schema for the "Licencia + GAF + RECA" form.
 *
 * Business rules (RN CEPA-062):
 *   - Cuando tiene_licencia es TRUE, los cuatro campos son REQUERIDOS:
 *       resumen_termino_lm, total_dias_lm, tipo_licencia, tipo_reposo.
 *   - gaf_tramo: opcional; tramo del catálogo /gaf-tramos (v5 D18). El entero ``gaf``
 *     anterior a D18 ya no se edita aquí; el backend lo conserva.
 *   - total_dias_lm: si se informa, entero ≥ 1.
 *   - estado_reca y observaciones: siempre opcionales.
 */
import { z } from "zod";
import type { TipoLicencia, TipoReposo } from "./api";
import { TIPO_RECA_VALUES } from "@/features/reintegro/recaSchema";

const TIPO_LICENCIA_VALUES: [TipoLicencia, ...TipoLicencia[]] = [
  "1",
  "5",
  "6",
  "3",
  "4",
  "extra_sistema",
];

const TIPO_REPOSO_VALUES: [TipoReposo, ...TipoReposo[]] = ["total", "parcial"];

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

    gaf_tramo: z.string().optional().nullable(),

    estado_reca: z
      .enum(TIPO_RECA_VALUES, {
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
  });

export type LicenciaControlForm = z.infer<typeof licenciaControlSchema>;
