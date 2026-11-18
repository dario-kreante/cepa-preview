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

/** QA-005: días corridos desde el ingreso EPT (feriados y fines de semana cuentan). */
export const DIAS_PLAZO_INFORME = 18;
export const DIAS_PLAZO_PORTAL_ISL = 20; // último día posible de envío

function sumarDias(iso: string, dias: number): string {
  const [a, m, d] = iso.split("-").map(Number);
  // UTC para que el cambio de hora no mueva el día.
  return new Date(Date.UTC(a, m - 1, d + dias)).toISOString().slice(0, 10);
}

/** Plazos que el sistema propone a partir de la fecha de ingreso EPT (YYYY-MM-DD). */
export function plazosAutomaticos(fechaIngresoEpt: string): {
  plazo_informe_ept: string;
  plazo_portal_isl: string;
} {
  return {
    plazo_informe_ept: sumarDias(fechaIngresoEpt, DIAS_PLAZO_INFORME),
    plazo_portal_isl: sumarDias(fechaIngresoEpt, DIAS_PLAZO_PORTAL_ISL),
  };
}
