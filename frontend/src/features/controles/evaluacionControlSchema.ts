/**
 * Zod schema for the "Evaluación clínica" form.
 *
 * Los tres campos vienen de la ficha del CEPA en SALUTEM y son texto libre opcional.
 * Los largos máximos coinciden con las columnas de control_medico (migración 1310).
 */
import { z } from "zod";

export const evaluacionControlSchema = z.object({
  tiempo_estimado_tratamiento: z.string().max(80, "Máximo 80 caracteres"),
  proyeccion_reintegro: z.string().max(80, "Máximo 80 caracteres"),
  factores_riesgo: z.string().max(500, "Máximo 500 caracteres"),
});

export type EvaluacionControlForm = z.infer<typeof evaluacionControlSchema>;

/** Etiquetas de los campos: las mismas que usa la ficha del CEPA en SALUTEM. */
export const EVALUACION_LABELS = {
  tiempo_estimado_tratamiento: "Tiempo estimado de tratamiento",
  proyeccion_reintegro: "Proyección de reintegro laboral",
  factores_riesgo: "Factores de riesgo acogidos",
} as const;
