/**
 * Zod schema para el formulario "Nuevo caso de reintegro" / "Editar caso".
 *
 * Campos enviados al backend vía CasoReintegroCreate / CasoReintegroUpdate.
 * `ingreso_id` lo inyecta el caller (no es campo del formulario).
 */
import { z } from "zod";
import type { TipoDerivacion } from "./api";

export const TIPO_DERIVACION_VALUES = [
  "DIEP",
  "DIAT",
  "PAPT a flujo AT",
  "Reingreso FUMP",
  "Reingreso SUSESO",
  "Convenio U.Clinica",
  "Proyecto",
  "Particular",
  "PAPT",
] as const satisfies readonly TipoDerivacion[];

export const SEXO_VALUES = ["F", "M", "otro"] as const;
export const SEXO_LABELS: Record<(typeof SEXO_VALUES)[number], string> = {
  F: "Femenino",
  M: "Masculino",
  otro: "Otro",
};

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const casoReintegroSchema = z.object({
  rut: z.string().trim().min(1, "El RUT es requerido"),
  nombre: z.string().trim().min(1, "El nombre es requerido"),
  tipo_derivacion: z.enum(TIPO_DERIVACION_VALUES, {
    required_error: "El tipo de derivación es requerido",
  }),
  fecha_caso: isoDate.min(1, "La fecha del caso es requerida"),
  sexo: z.enum(SEXO_VALUES, { required_error: "El sexo es requerido" }),
  edad: z.coerce
    .number({ invalid_type_error: "La edad debe ser un número" })
    .int("La edad debe ser un entero")
    .min(1, "Edad fuera de rango (1–130)")
    .max(130, "Edad fuera de rango (1–130)"),
  region: z.string().trim().min(1, "La región es requerida"),
  comuna: z.string().trim().optional(),
  rubro_empleador: z.string().trim().optional(),
});

export type CasoReintegroForm = z.infer<typeof casoReintegroSchema>;
