/**
 * Zod schema for the "Nuevo control" form.
 *
 * Fields sent to the backend:
 *   - fecha_control       (required, ISO date)
 *   - profesional_id      (id del catálogo, o "otro" para escribir un nombre libre)
 *   - medico_tratante     (nombre libre; solo obligatorio cuando profesional_id === "otro")
 *   - region_derivacion   (required, non-empty)
 *   - observaciones       (optional free-text comment, e.g. "próximo a alta médica")
 *
 * NOT included:
 *   - semana_control  → auto-calculated by the backend
 *   - ingreso_id      → injected by the caller (not a form field)
 */
import { z } from "zod";

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const PROFESIONAL_OTRO = "otro";

export const controlSchema = z
  .object({
    fecha_control: isoDate.min(1, "La fecha del control es requerida"),

    profesional_id: z.string(),

    medico_tratante: z.string().trim(),

    region_derivacion: z
      .string()
      .trim()
      .min(1, "La región de derivación es requerida"),

    observaciones: z.string().trim().optional(),
  })
  .superRefine((v, ctx) => {
    const sinSeleccion = v.profesional_id === "";
    const otroSinNombre = v.profesional_id === PROFESIONAL_OTRO && v.medico_tratante === "";
    if (sinSeleccion || otroSinNombre) {
      ctx.addIssue({
        code: "custom",
        path: [sinSeleccion ? "profesional_id" : "medico_tratante"],
        message: "El médico tratante es requerido",
      });
    }
  });

export type ControlForm = z.infer<typeof controlSchema>;
