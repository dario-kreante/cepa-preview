/**
 * Zod schema for the "Agregar indicación" form.
 *
 * FrecuenciaFarmaco enum (backend exact literals):
 *   "c/24h" | "c/12h" | "c/8h" | "c/6h" | "semanal" | "bisemanal" | "mensual" | "otro"
 *
 * NOTE: There is NO "socorro" value in the enum — never add one.
 */
import { z } from "zod";
import type { FrecuenciaFarmaco } from "./api";

export const FRECUENCIA_VALUES = [
  "c/24h",
  "c/12h",
  "c/8h",
  "c/6h",
  "semanal",
  "bisemanal",
  "mensual",
  "otro",
] as const satisfies readonly FrecuenciaFarmaco[];

export const FRECUENCIA_LABELS: Record<FrecuenciaFarmaco, string> = {
  "c/24h": "Cada 24 h",
  "c/12h": "Cada 12 h",
  "c/8h": "Cada 8 h",
  "c/6h": "Cada 6 h",
  semanal: "Semanal",
  bisemanal: "Bisemanal",
  mensual: "Mensual",
  otro: "Otro",
};

export const indicacionSchema = z.object({
  medicamento: z
    .string()
    .trim()
    .min(1, "El medicamento es requerido"),

  dosis: z
    .string()
    .trim()
    .min(1, "La dosis es requerida"),

  frecuencia: z.enum(FRECUENCIA_VALUES, {
    required_error: "La frecuencia es requerida",
  }),

  extra_sistema: z.boolean().default(false),
});

export type IndicacionForm = z.infer<typeof indicacionSchema>;
