/**
 * Zod schema para el cierre / actualización del estado de reintegro (CEPA-042).
 * Coherencia temporal (fecha_reintegro >= fecha_reca, cierre requiere alta) la
 * valida el backend. Aquí se piden las fechas asociadas a cada flag activo.
 */
import { z } from "zod";
import type { EstadoReintegro, TipoAlta } from "./api";

export const ESTADO_REINTEGRO_VALUES = [
  "pendiente",
  "parcial",
  "total",
] as const satisfies readonly EstadoReintegro[];

export const ESTADO_REINTEGRO_LABELS: Record<EstadoReintegro, string> = {
  pendiente: "Pendiente",
  parcial: "Parcial",
  total: "Total",
};

/**
 * Tipos de alta que se pueden elegir. Médica y psicológica ya no están: se registran con
 * sus casillas (QA-003). El backend sigue aceptando «medica» y «psicologica» porque hay casos
 * guardados con ellos.
 */
export const TIPO_ALTA_VALUES = [
  "terapeutica",
  "abandono",
  "derivacion",
] as const satisfies readonly TipoAlta[];

/** Valores antiguos: se muestran en casos ya guardados y no se pierden al editar. */
export const TIPO_ALTA_ANTIGUOS = [
  "medica",
  "psicologica",
] as const satisfies readonly TipoAlta[];

export const TIPO_ALTA_LABELS: Record<TipoAlta, string> = {
  terapeutica: "Terapéutica",
  medica: "Médica",
  psicologica: "Psicológica",
  abandono: "Abandono",
  derivacion: "Derivación",
};

export const MENSAJE_TOTAL_SIN_ALTA =
  "Para un reintegro total, marca el alta médica, el alta psicológica o elige un tipo de alta.";

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");
const optionalDate = z.union([isoDate, z.literal("")]).optional();

export const cierreSchema = z.object({
  estado_reintegro: z.enum(ESTADO_REINTEGRO_VALUES, {
    required_error: "El estado de reintegro es requerido",
  }),
  fecha_reintegro: optionalDate,
  remitido_isl: z.boolean().default(false),
  alta_medica: z.boolean().default(false),
  fecha_alta_medica: optionalDate,
  alta_psicologica: z.boolean().default(false),
  fecha_alta_psico: optionalDate,
  tipo_alta: z
    .union([
      z.enum(TIPO_ALTA_VALUES),
      z.enum(TIPO_ALTA_ANTIGUOS),
      z.literal(""),
    ])
    .optional(),
  observaciones: z.string().trim().optional(),
}).superRefine((v, ctx) => {
  if (v.alta_medica && !v.fecha_alta_medica) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["fecha_alta_medica"],
      message: "Indica la fecha del alta médica",
    });
  }
  if (v.alta_psicologica && !v.fecha_alta_psico) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["fecha_alta_psico"],
      message: "Indica la fecha del alta psicológica",
    });
  }
  if (
    v.estado_reintegro === "total" &&
    !v.alta_medica &&
    !v.alta_psicologica &&
    !v.tipo_alta
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["tipo_alta"],
      message: MENSAJE_TOTAL_SIN_ALTA,
    });
  }
});

export type CierreForm = z.infer<typeof cierreSchema>;
