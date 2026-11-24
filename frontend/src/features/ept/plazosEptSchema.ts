/**
 * Zod schema for the Plazos EPT form.
 *
 * Fields mirror PlazoEptCreate / PlazoEptUpdate from the OpenAPI spec.
 * Note: estado_informe and estado_entrega_isl are backend-computed and
 * read-only — they are NOT included here.
 */
import { z } from "zod";

const optionalDate = z
  .string()
  .optional()
  .transform((v) => (v === "" ? undefined : v))
  .pipe(
    z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)")
      .optional()
  );

export const plazosEptSchema = z.object({
  plazo_informe_ept: optionalDate,
  plazo_portal_isl: optionalDate,
  fecha_entrega_isl: optionalDate,
  fecha_envio: optionalDate,
});

export type PlazosEptForm = z.infer<typeof plazosEptSchema>;

/**
 * QA-009 (23-11): días corridos desde el ingreso EPT. Si el día cae en sábado, domingo o
 * feriado, el plazo se adelanta al día hábil anterior. El cálculo lo hace el backend
 * (GET /casos-ept/{id}/plazos-sugeridos) porque conoce los feriados registrados.
 */
export const DIAS_PLAZO_INFORME = 15; // fecha de envío del informe EPT
export const DIAS_PLAZO_PORTAL_ISL = 19; // último día posible de envío al portal ISL
