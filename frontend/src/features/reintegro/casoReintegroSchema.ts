/**
 * Zod schema para el formulario "Nuevo caso de reintegro" / "Editar caso".
 *
 * Campos enviados al backend vía CasoReintegroCreate / CasoReintegroUpdate.
 * `ingreso_id` lo inyecta el caller (no es campo del formulario).
 */
import { z } from "zod";
import type { TipoDerivacion, TipoTrabajador } from "./api";

export const TIPO_DERIVACION_VALUES = [
  "DIEP",
  "DIAT",
  "PAPT a flujo AT",
  "Reingreso FUMP",
  "Reingreso SUSESO",
  "Reingreso ISL",
  "Convenio U.Clinica",
  "Proyecto",
  "Particular",
  "PAPT",
] as const satisfies readonly TipoDerivacion[];

// QA-008 (QA UTalca 22-10): el alta ya no pide edad ni sexo (el backend los copia del
// paciente) y pide la razón social de la empresa y el tipo de trabajador.
export const TIPO_TRABAJADOR_VALUES = [
  "dependiente",
  "independiente",
] as const satisfies readonly TipoTrabajador[];
export const TIPO_TRABAJADOR_LABELS: Record<TipoTrabajador, string> = {
  dependiente: "Dependiente",
  independiente: "Independiente",
};

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const casoReintegroSchema = z.object({
  // Opcional: si el paciente no tiene RUT (p. ej. viene de SALUTEM) el backend usa el del
  // paciente del ingreso o lo deja vacío.
  rut: z.string().trim().optional(),
  nombre: z.string().trim().min(1, "El nombre es requerido"),
  tipo_derivacion: z.enum(TIPO_DERIVACION_VALUES, {
    required_error: "El tipo de derivación es requerido",
  }),
  fecha_caso: isoDate.min(1, "La fecha del caso es requerida"),
  region: z.string().trim().min(1, "La región es requerida"),
  comuna: z.string().trim().optional(),
  rubro_empleador: z.string().trim().optional(),
  razon_social: z.string().trim().optional(),
  // "" = sin indicar (casos previos a QA-008). En el alta es obligatorio (ver abajo).
  tipo_trabajador: z.enum(TIPO_TRABAJADOR_VALUES).or(z.literal("")),
});

/** Alta: además exige el tipo de trabajador (los casos previos pueden no tenerlo). */
export const casoReintegroAltaSchema = casoReintegroSchema.refine(
  (v) => v.tipo_trabajador !== "",
  { message: "El tipo de trabajador es requerido", path: ["tipo_trabajador"] },
);

export type CasoReintegroForm = z.infer<typeof casoReintegroSchema>;
