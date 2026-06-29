/**
 * Zod schema for the "Nuevo control" form.
 *
 * Fields sent to the backend:
 *   - fecha_control       (required, ISO date)
 *   - medico_tratante     (required, non-empty)
 *   - region_derivacion   (required, non-empty)
 *
 * NOT included:
 *   - semana_control  → auto-calculated by the backend
 *   - ingreso_id      → injected by the caller (not a form field)
 */
import { z } from "zod";

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const controlSchema = z.object({
  fecha_control: isoDate.min(1, "La fecha del control es requerida"),

  medico_tratante: z
    .string()
    .trim()
    .min(1, "El médico tratante es requerido"),

  region_derivacion: z
    .string()
    .trim()
    .min(1, "La región de derivación es requerida"),
});

export type ControlForm = z.infer<typeof controlSchema>;
