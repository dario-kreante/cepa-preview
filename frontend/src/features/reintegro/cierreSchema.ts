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

export const TIPO_ALTA_VALUES = [
  "terapeutica",
  "medica",
  "psicologica",
  "abandono",
  "derivacion",
] as const satisfies readonly TipoAlta[];

export const TIPO_ALTA_LABELS: Record<TipoAlta, string> = {
  terapeutica: "Terapéutica",
  medica: "Médica",
  psicologica: "Psicológica",
  abandono: "Abandono",
  derivacion: "Derivación",
};

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
    .union([z.enum(TIPO_ALTA_VALUES), z.literal("")])
    .optional(),
  observaciones: z.string().trim().optional(),
});

export type CierreForm = z.infer<typeof cierreSchema>;
