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
