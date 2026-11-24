/**
 * Programas del ingreso. Los reportes filtran por estos valores exactos
 * (`Ingreso.programa`): no cambiar el texto sin migrar los datos existentes.
 */
export const PROGRAMAS = ["Programa Regular", "Ingreso ISL", "Tratamiento ISL", "Ley Karin", "PIPT"] as const;

/**
 * Opciones del selector: la lista, más el valor actual si es antiguo y ya no está en
 * la lista. Así un programa viejo se ve y no se pierde al guardar la ficha.
 */
export function opcionesPrograma(actual?: string | null): string[] {
  if (!actual || (PROGRAMAS as readonly string[]).includes(actual)) return [...PROGRAMAS];
  return [...PROGRAMAS, actual];
}
