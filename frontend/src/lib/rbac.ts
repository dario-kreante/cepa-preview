export type Rol = "Coordinacion" | "Administrativo" | "Auditor";
const ESCRITORES: Rol[] = ["Coordinacion", "Administrativo"];
export function puedeEscribir(rol: Rol | null | undefined): boolean {
  return !!rol && ESCRITORES.includes(rol);
}
