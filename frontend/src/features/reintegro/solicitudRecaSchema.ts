/**
 * Solicitud de RECA del caso de reintegro (QA-003, PRD v5 §7.4.2).
 * El estado lo deriva el backend: pendiente (sin fecha ni RECA), solicitada (con fecha, sin
 * RECA) o recibida (con RECA registrada). La fecha no puede ser futura ni anterior a la del caso.
 */
import type { EstadoSolicitudReca } from "./api";

export const ESTADO_SOLICITUD_RECA_LABELS: Record<EstadoSolicitudReca, string> = {
  pendiente: "Pendiente",
  solicitada: "Solicitada",
  recibida: "Recibida",
};

export const ESTADO_SOLICITUD_RECA_VARIANT: Record<
  EstadoSolicitudReca,
  "warning" | "info" | "success"
> = {
  pendiente: "warning",
  solicitada: "info",
  recibida: "success",
};

/** Hoy en Chile (YYYY-MM-DD): de noche, la fecha UTC ya sería la del día siguiente. */
export function hoyChile(ahora: Date = new Date()): string {
  return ahora.toLocaleDateString("en-CA", { timeZone: "America/Santiago" });
}

function dmy(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}-${m}-${y}`;
}

/** Mensaje de error de la fecha de solicitud, o null si es válida. Fechas YYYY-MM-DD. */
export function validarFechaSolicitud(
  fecha: string,
  fechaCaso: string,
  hoy: string = hoyChile(),
): string | null {
  if (!fecha) return "Indica la fecha en que se solicitó la RECA.";
  if (fecha > hoy) return "La fecha de solicitud no puede ser futura.";
  if (fecha < fechaCaso)
    return `La fecha de solicitud no puede ser anterior a la fecha del caso (${dmy(fechaCaso)}).`;
  return null;
}

/** Mensaje de error de la fecha de remisión a ISL (QA-010), o null si es válida. */
export function validarFechaRemision(
  fecha: string,
  fechaCaso: string,
  hoy: string = hoyChile(),
): string | null {
  if (!fecha) return "Indica la fecha en que se remitió el caso a ISL.";
  if (fecha > hoy) return "La fecha de remisión no puede ser futura.";
  if (fecha < fechaCaso)
    return `La fecha de remisión no puede ser anterior a la fecha del caso (${dmy(fechaCaso)}).`;
  return null;
}
