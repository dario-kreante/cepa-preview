/**
 * Zod schema for the "Nuevo seguimiento de tratamiento" form.
 *
 * Business rules (RN CEPA-023):
 *   - Cuando disminucion_farmacos es TRUE, plan_disminucion es REQUERIDO (no vacío).
 *   - Cuando cambio_esquema es TRUE, detalle_cambio es REQUERIDO (no vacío).
 */
import { z } from "zod";

export const seguimientoSchema = z
  .object({
    disminucion_farmacos: z.boolean().default(false),

    plan_disminucion: z.string().optional().or(z.literal("")),

    cambio_esquema: z.boolean().default(false),

    detalle_cambio: z.string().optional().or(z.literal("")),

    observaciones: z.string().optional().or(z.literal("")),
  })
  .superRefine((d, ctx) => {
    if (d.disminucion_farmacos && !d.plan_disminucion?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "El plan de disminución es requerido cuando se indica disminución de fármacos",
        path: ["plan_disminucion"],
      });
    }
    if (d.cambio_esquema && !d.detalle_cambio?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "El detalle del cambio es requerido cuando se indica cambio de esquema",
        path: ["detalle_cambio"],
      });
    }
  });

export type SeguimientoForm = z.infer<typeof seguimientoSchema>;
