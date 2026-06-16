/**
 * Zod schema for the "Nueva receta" form.
 *
 * Business rules (RN CEPA-022):
 *   - fecha_revision >= fecha_emision  (revision must not precede emission)
 *   - fecha_envio   >= fecha_emision   (if provided; send date must not precede emission)
 */
import { z } from "zod";

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const recetaSchema = z
  .object({
    fecha_emision: isoDate.min(1, "La fecha de emisión es requerida"),

    fecha_revision: isoDate.min(1, "La fecha de revisión es requerida"),

    fecha_envio: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)")
      .optional()
      .or(z.literal("")),

    marca_medicamento: z
      .string()
      .trim()
      .min(1, "La marca del medicamento es requerida"),
  })
  .refine((d) => d.fecha_revision >= d.fecha_emision, {
    message:
      "La fecha de revisión debe ser igual o posterior a la fecha de emisión",
    path: ["fecha_revision"],
  })
  .refine(
    (d) => !d.fecha_envio || d.fecha_envio >= d.fecha_emision,
    {
      message:
        "La fecha de envío debe ser igual o posterior a la fecha de emisión",
      path: ["fecha_envio"],
    },
  );

export type RecetaForm = z.infer<typeof recetaSchema>;
