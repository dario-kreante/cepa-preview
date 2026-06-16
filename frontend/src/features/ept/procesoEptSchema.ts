/**
 * Zod schema for the Proceso EPT form (CEPA-031).
 *
 * Fields mirror ProcesoEptCreate / ProcesoEptUpdate from the OpenAPI spec.
 * Numbers use z.coerce so RHF string→number conversion works via setValueAs.
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

export const procesoEptSchema = z.object({
  plazo_evid_denunciante: optionalDate,
  plazo_insumos_empresa: optionalDate,
  hay_testigos: z.boolean().default(false),
  testigos_cantidad: z.coerce
    .number({ invalid_type_error: "Debe ser un número" })
    .int("Debe ser un número entero")
    .min(0, "No puede ser negativo")
    .default(0),
  num_entrevistas: z.coerce
    .number({ invalid_type_error: "Debe ser un número" })
    .int("Debe ser un número entero")
    .min(0, "No puede ser negativo")
    .default(0),
  insumos_eista: z.string().optional(),
  doc_incumplimiento: z.string().optional(),
  observaciones: z.string().optional(),
});

export type ProcesoEptForm = z.infer<typeof procesoEptSchema>;
