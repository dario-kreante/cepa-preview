/**
 * Zod schema for the "Próximo control" form.
 *
 * Fields:
 *   - proximo_control  (required, ISO date YYYY-MM-DD)
 *   - proximo_agendado (boolean, default false)
 */
import { z } from "zod";

export const proximoControlSchema = z.object({
  proximo_control: z
    .string()
    .min(1, "La fecha del próximo control es requerida")
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)"),

  proximo_agendado: z.boolean().default(false),
});

export type ProximoControlForm = z.infer<typeof proximoControlSchema>;
