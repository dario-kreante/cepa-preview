/**
 * Zod schema para el formulario de RECA (CEPA-041).
 * Las validaciones de coherencia temporal las hace el backend; aquí solo
 * obligatoriedad y formato. Los campos condicionales (detalle/fecha) se piden
 * cuando el flag correspondiente está activo.
 */
import { z } from "zod";
import type { TipoReca } from "./api";

export const TIPO_RECA_VALUES = ["AT", "EP"] as const satisfies readonly TipoReca[];
export const TIPO_RECA_LABELS: Record<TipoReca, string> = {
  AT: "Accidente del trabajo (AT)",
  EP: "Enfermedad profesional (EP)",
};

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const recaSchema = z
  .object({
    fecha_reca: isoDate.min(1, "La fecha de la RECA es requerida"),
    tipo_reca: z.enum(TIPO_RECA_VALUES, {
      required_error: "El tipo de RECA es requerido",
    }),
    numero_reca: z.string().trim().min(1, "El número de RECA es requerido"),
    razon_social: z.string().trim().min(1, "La razón social es requerida"),
    riesgos_calificados: z.string().trim().optional(),
    solicita_medidas: z.boolean().default(false),
    detalle_medidas: z.string().trim().optional(),
    fecha_medidas: z.union([isoDate, z.literal("")]).optional(),
    verifica_medidas: z.boolean().default(false),
    detalle_verificacion: z.string().trim().optional(),
    fecha_verificacion: z.union([isoDate, z.literal("")]).optional(),
  })
  .refine(
    (v) => !v.solicita_medidas || !!v.detalle_medidas?.trim(),
    {
      message: "Detalla las medidas solicitadas",
      path: ["detalle_medidas"],
    },
  )
  .refine(
    (v) => !v.verifica_medidas || !!v.detalle_verificacion?.trim(),
    {
      message: "Detalla la verificación de medidas",
      path: ["detalle_verificacion"],
    },
  );

export type RecaForm = z.infer<typeof recaSchema>;
