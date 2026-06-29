/**
 * Zod schema para el formulario de filtros del reporte de auditoría (CEPA-051).
 * RN-2: el período (fecha_desde + fecha_hasta) es obligatorio; el resto es opcional.
 */
import { z } from "zod";

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)");

export const reporteSchema = z
  .object({
    fecha_desde: isoDate.min(1, "La fecha desde es requerida"),
    fecha_hasta: isoDate.min(1, "La fecha hasta es requerida"),
    diagnostico: z.string().trim().optional(),
    profesional: z.string().trim().optional(),
    estado_caso: z.string().trim().optional(),
    programa: z.string().trim().optional(),
    region: z.string().trim().optional(),
    tipo_denuncia: z.string().trim().optional(),
  })
  .refine((v) => v.fecha_desde <= v.fecha_hasta, {
    message: "La fecha desde no puede ser posterior a la fecha hasta",
    path: ["fecha_hasta"],
  });

export type ReporteForm = z.infer<typeof reporteSchema>;
