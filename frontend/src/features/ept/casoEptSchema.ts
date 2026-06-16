/**
 * Zod schema for the "Nuevo caso EPT" / "Editar caso EPT" form.
 *
 * Fields sent to the backend via CasoEptCreate / CasoEptUpdate:
 *   - mes                  (required, non-empty)
 *   - fecha_ingreso_ept    (required, ISO date)
 *   - nombre_trabajador    (required, non-empty)
 *   - rut_trabajador       (required, non-empty)
 *   - region_trabajador    (required, non-empty)
 *   - eista                (required, non-empty)
 *   - factor_riesgo        (required enum)
 *   - corresponde_ept      (boolean, default true)
 *   - razon_social         (optional)
 *   - unidad_cargo_horario (optional)
 *
 * NOT included:
 *   - ingreso_id  → injected by the caller (not a form field)
 *   - estado      → managed server-side
 */
import { z } from "zod";

export type FactorRiesgo =
  | "carga"
  | "organizacion_trabajo"
  | "factores_psicosociales"
  | "violencia_laboral"
  | "condiciones_ergonomicas"
  | "otro";

const factorRiesgoValues = [
  "carga",
  "organizacion_trabajo",
  "factores_psicosociales",
  "violencia_laboral",
  "condiciones_ergonomicas",
  "otro",
] as const satisfies [FactorRiesgo, ...FactorRiesgo[]];

export const FACTOR_RIESGO_LABELS: Record<FactorRiesgo, string> = {
  carga: "Carga",
  organizacion_trabajo: "Organización del trabajo",
  factores_psicosociales: "Factores psicosociales",
  violencia_laboral: "Violencia laboral",
  condiciones_ergonomicas: "Condiciones ergonómicas",
  otro: "Otro",
};

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const casoEptSchema = z.object({
  mes: z.string().trim().min(1, "El mes es requerido"),

  fecha_ingreso_ept: isoDate.min(1, "La fecha de ingreso EPT es requerida"),

  nombre_trabajador: z
    .string()
    .trim()
    .min(1, "El nombre del trabajador es requerido"),

  rut_trabajador: z
    .string()
    .trim()
    .min(1, "El RUT del trabajador es requerido"),

  region_trabajador: z
    .string()
    .trim()
    .min(1, "La región del trabajador es requerida"),

  eista: z.string().trim().min(1, "El EISTA es requerido"),

  factor_riesgo: z.enum(factorRiesgoValues, {
    required_error: "El factor de riesgo es requerido",
  }),

  corresponde_ept: z.boolean().default(true),

  razon_social: z.string().trim().optional(),

  unidad_cargo_horario: z.string().trim().optional(),
});

export type CasoEptForm = z.infer<typeof casoEptSchema>;
