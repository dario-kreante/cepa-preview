import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a Chilean RUT string to the canonical display form with dots and dash.
 * Accepts inputs with or without formatting (e.g. "12345678-5", "123456785", "12.345.678-5").
 * Returns the formatted RUT or the original string if it cannot be parsed.
 *
 * @example
 *   formatRut("123456785")   → "12.345.678-5"
 *   formatRut("12345678-5")  → "12.345.678-5"
 *   formatRut("12.345.678-5") → "12.345.678-5"
 */
export function formatRut(rut: string): string {
  if (!rut) return rut;

  // Strip everything except digits and the letter K
  const clean = rut.replace(/[^0-9kK]/g, "").toUpperCase();
  if (clean.length < 2) return rut;

  const body = clean.slice(0, -1);
  const dv = clean.slice(-1);

  // Insert dots every 3 digits from right
  const withDots = body.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

  return `${withDots}-${dv}`;
}

/**
 * Format a date string for display. Handles:
 *   - DD-MM-YYYY (v2 seed format)  → "DD/MM/YYYY"
 *   - ISO 8601 (YYYY-MM-DD or full datetime) → "DD/MM/YYYY"
 *   - Already-formatted strings → returned as-is
 *
 * @example
 *   fmtDate("15-06-2026")    → "15/06/2026"
 *   fmtDate("2026-06-15")    → "15/06/2026"
 *   fmtDate("2026-06-15T10:30:00Z") → "15/06/2026"
 */
export function fmtDate(d: string): string {
  if (!d) return d;

  // DD-MM-YYYY (v2 format)
  if (/^\d{2}-\d{2}-\d{4}$/.test(d)) {
    return d.replace(/-/g, "/");
  }

  // ISO: YYYY-MM-DD or YYYY-MM-DDTHH:mm...
  const isoMatch = d.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    const [, year, month, day] = isoMatch;
    return `${day}/${month}/${year}`;
  }

  // Fallback: return unchanged
  return d;
}

/**
 * Tiempo transcurrido en español ("hace 5 min", "hace 3 días").
 * Acepta un ISO con o sin zona; sin zona se asume UTC (el backend guarda en UTC).
 */
export function fmtRelativo(iso: string | null | undefined, ahora: Date = new Date()): string {
  if (!iso) return "—";
  const conZona = /(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
  const t = new Date(conZona).getTime();
  if (Number.isNaN(t)) return "—";
  const seg = Math.max(0, Math.round((ahora.getTime() - t) / 1000));
  if (seg < 60) return "hace un momento";
  const min = Math.floor(seg / 60);
  if (min < 60) return `hace ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return h === 1 ? "hace 1 hora" : `hace ${h} horas`;
  const d = Math.floor(h / 24);
  if (d < 30) return d === 1 ? "hace 1 día" : `hace ${d} días`;
  const m = Math.floor(d / 30);
  if (m < 12) return m === 1 ? "hace 1 mes" : `hace ${m} meses`;
  const a = Math.floor(d / 365);
  return a <= 1 ? "hace 1 año" : `hace ${a} años`;
}
