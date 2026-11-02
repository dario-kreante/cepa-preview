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
 *   - factor_riesgo        (required enum; solo la lista vigente del área)
 *   - corresponde_ept      (boolean, default true)
 *   - razon_social         (optional)
 *   - unidad_cargo_horario (optional)
 *
 * NOT included:
 *   - ingreso_id  → injected by the caller (not a form field)
 *   - estado      → managed server-side
 */
import { z } from "zod";

import type { components } from "@/types/api";

/** Factores que acepta el backend al crear o editar (QA UTalca 22-10, QA-003). */
export type FactorRiesgo = components["schemas"]["FactorRiesgo"];
/** Factores de la primera versión: solo llegan en lectura, en casos antiguos. */
export type FactorRiesgoLegado = components["schemas"]["FactorRiesgoLegado"];

/** Etiquetas del área EPT, en el orden en que se muestran en el selector. */
export const FACTOR_RIESGO_LABELS: Record<FactorRiesgo, string> = {
  sobrecarga: "Sobrecarga",
  subcarga: "Subcarga",
  trabajo_activo_continuo: "Trabajo activo continuo",
  ausencia_descansos: "Ausencia de descansos",
  tareas_rutinarias: "Tareas excesivamente rutinarias",
  trabajo_emocionalmente_comprometido: "Trabajo emocionalmente comprometido",
  ambiguedad_conflicto_roles: "Ambigüedad o conflicto de roles",
  limitacion_regular_trabajo: "Limitación o imposibilidad de regular el trabajo",
  limitacion_tomar_decisiones: "Limitación o imposibilidad de tomar decisiones",
  limitacion_regular_permisos: "Limitación o imposibilidad de regular permisos",
  carencia_uso_habilidades: "Carencia de utilización de habilidades del trabajador",
  ausencia_ayuda_informacion: "Ausencia de ayuda e información necesarias",
  ausencia_capacitacion_tecnologica: "Ausencia de capacitación tecnológica periódica",
  conflictos_interpersonales: "Conflictos interpersonales recurrentes",
  condiciones_organizacionales_estresantes: "Condiciones organizacionales estresantes",
  hostilidad_pares: "Hostilidad de pares",
  hostilidad_subalternos: "Hostilidad de subalternos",
  disfuncionalidad_jefatura: "Disfuncionalidad de la jefatura",
  hostilidad_jefatura: "Hostilidad de la jefatura",
  asedio_sexual: "Asedio sexual",
  violencia_acoso_usuarios: "Violencia o acoso desde usuarios, etc.",
  violencia_personas_ajenas: "Violencia desde personas ajenas (delincuencia, otros)",
  condiciones_fisicas_ergonomicas: "Condiciones físicas o ergonómicas deficientes",
  no_aplica: "No aplica (no se evidencia exposición a riesgo laboral)",
};

export const FACTORES_RIESGO = Object.keys(FACTOR_RIESGO_LABELS) as [
  FactorRiesgo,
  ...FactorRiesgo[],
];

const FACTOR_RIESGO_LEGADO_LABELS: Record<FactorRiesgoLegado, string> = {
  carga: "Carga",
  organizacion_trabajo: "Organización del trabajo",
  factores_psicosociales: "Factores psicosociales",
  violencia_laboral: "Violencia laboral",
  condiciones_ergonomicas: "Condiciones ergonómicas",
  otro: "Otro",
};

export function esFactorRiesgoVigente(valor: string): valor is FactorRiesgo {
  return Object.prototype.hasOwnProperty.call(FACTOR_RIESGO_LABELS, valor);
}

/**
 * Etiqueta para mostrar un factor guardado. Los casos creados antes de QA-003
 * conservan un valor de la lista anterior: se muestran como «(anterior) …».
 */
export function etiquetaFactorRiesgo(valor: string): string {
  if (esFactorRiesgoVigente(valor)) return FACTOR_RIESGO_LABELS[valor];
  if (Object.prototype.hasOwnProperty.call(FACTOR_RIESGO_LEGADO_LABELS, valor)) {
    return `(anterior) ${FACTOR_RIESGO_LEGADO_LABELS[valor as FactorRiesgoLegado]}`;
  }
  return valor;
}

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

  eista: z.string().trim().min(1, "El EPTista es requerido"),

  factor_riesgo: z.enum(FACTORES_RIESGO, {
    errorMap: () => ({ message: "Selecciona un factor de riesgo" }),
  }),

  // Reunión 29-10 (D11): hasta 2 factores más, opcionales ("" = ninguno).
  factor_adicional_1: z.union([z.enum(FACTORES_RIESGO), z.literal("")]).optional(),
  factor_adicional_2: z.union([z.enum(FACTORES_RIESGO), z.literal("")]).optional(),

  corresponde_ept: z.boolean().default(true),

  razon_social: z.string().trim().optional(),

  unidad_cargo_horario: z.string().trim().optional(),
}).superRefine((v, ctx) => {
  const elegidos = [v.factor_riesgo, v.factor_adicional_1, v.factor_adicional_2].filter(Boolean);
  if (new Set(elegidos).size !== elegidos.length) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["factor_adicional_2"],
      message: "No repitas un factor de riesgo",
    });
  }
});

/** Factores adicionales elegidos en el formulario, sin vacíos. */
export function factoresAdicionales(v: CasoEptForm): FactorRiesgo[] {
  return [v.factor_adicional_1, v.factor_adicional_2].filter(
    (f): f is FactorRiesgo => !!f,
  );
}

export type CasoEptForm = z.infer<typeof casoEptSchema>;
