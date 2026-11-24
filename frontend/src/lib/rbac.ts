export type Rol = "Coordinacion" | "Administrativo" | "Auditor" | "Superadmin";
const ESCRITORES: Rol[] = ["Coordinacion", "Administrativo"];

/** ¿`rol` es uno de `roles`? Superadmin tiene todos los permisos (igual que require_role en el backend). */
export function tieneRol(rol: Rol | null | undefined, ...roles: Rol[]): boolean {
  return rol === "Superadmin" || (!!rol && roles.includes(rol));
}

export function puedeEscribir(rol: Rol | null | undefined): boolean {
  return tieneRol(rol, ...ESCRITORES);
}

/**
 * ¿Puede leer el módulo Auditoría? Coordinación, Auditor y Superadmin por rol; un Administrativo
 * solo con el permiso extra «Acceso a Auditoría» (CA-012). Igual que `require_auditoria` en el backend.
 */
export function puedeVerAuditoria(rol: Rol | null | undefined, accesoAuditoria = false): boolean {
  return tieneRol(rol, "Coordinacion", "Auditor") || (rol === "Administrativo" && accesoAuditoria);
}

/** EPT solo permite escritura a Administrativo (Coordinacion puede leer, no escribir). */
export function puedeEscribirEpt(rol: Rol | null | undefined): boolean {
  return tieneRol(rol, "Administrativo");
}
