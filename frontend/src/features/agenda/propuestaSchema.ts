/**
 * Zod schema para generar una propuesta de agenda (CEPA-080).
 * fecha_inicio debe ser día hábil (lun–vie); fecha_fin la calcula el backend.
 */
import { z } from "zod";
import type { TipoPropuesta } from "./api";

const TIPO_VALUES = ["diaria", "semanal", "mensual"] as const satisfies readonly TipoPropuesta[];

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const propuestaSchema = z.object({
  tipo: z.enum(TIPO_VALUES),
  fecha_inicio: isoDate
    .min(1, "La fecha de inicio es requerida")
    .refine(
      (v) => {
        // ISO weekday del string YYYY-MM-DD (evita timezone usando UTC).
        const day = new Date(`${v}T00:00:00Z`).getUTCDay(); // 0=dom … 6=sáb
        return day >= 1 && day <= 5;
      },
      { message: "La fecha de inicio debe ser un día hábil (lun–vie)" },
    ),
});

export type PropuestaForm = z.infer<typeof propuestaSchema>;
