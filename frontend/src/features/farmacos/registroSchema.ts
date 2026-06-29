/**
 * Zod schema for the "Crear registro farmacológico" form.
 *
 * EstadoFarmacologico enum (backend exact literals):
 *   "activo" | "suspendido" | "completado" | "pendiente"
 */
import { z } from "zod";
import type { EstadoFarmacologico } from "./api";

export const ESTADO_VALUES = [
  "activo",
  "suspendido",
  "completado",
  "pendiente",
] as const satisfies readonly EstadoFarmacologico[];

export const ESTADO_LABELS: Record<EstadoFarmacologico, string> = {
  activo: "Activo",
  suspendido: "Suspendido",
  completado: "Completado",
  pendiente: "Pendiente",
};

export const registroSchema = z.object({
  medico_tratante: z
    .string()
    .trim()
    .min(1, "El médico tratante es requerido"),

  estado_farmacologico: z.enum(ESTADO_VALUES, {
    required_error: "El estado farmacológico es requerido",
  }),

  antecedentes_previos: z.string().trim().optional().or(z.literal("")),

  tratamiento_previo: z.string().trim().optional().or(z.literal("")),
});

export type RegistroForm = z.infer<typeof registroSchema>;
