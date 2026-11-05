/** Regiones de Chile, de norte a sur. Lista cerrada para no repetir «Maule», «Del Maule», «VII»… */
export const REGIONES_CHILE = [
  "Arica y Parinacota",
  "Tarapacá",
  "Antofagasta",
  "Atacama",
  "Coquimbo",
  "Valparaíso",
  "Metropolitana",
  "O'Higgins",
  "Maule",
  "Ñuble",
  "Biobío",
  "La Araucanía",
  "Los Ríos",
  "Los Lagos",
  "Aysén",
  "Magallanes",
] as const;

/**
 * Opciones para un selector de región. Un valor antiguo fuera de la lista (escrito a mano
 * antes de existir el selector) se conserva como opción para no perderlo al guardar.
 */
export function opcionesRegion(actual?: string | null): string[] {
  const valor = actual?.trim();
  const lista: string[] = [...REGIONES_CHILE];
  return valor && !lista.includes(valor) ? [valor, ...lista] : lista;
}
