import type { AlertaRead } from "./api";

/** Módulos del menú lateral que muestran un número de alertas. */
export type ModuloConAlertas = "licencias" | "ept";

/**
 * Alertas pendientes de un módulo. Es la única definición del número rojo del menú
 * (AppShell) y de la lista que muestra cada módulo al entrar: así nunca difieren.
 */
export function alertasPendientesDeModulo(
  alertas: AlertaRead[],
  modulo: ModuloConAlertas,
): AlertaRead[] {
  return alertas.filter((a) => {
    if (a.estado !== "pendiente") return false;
    if (modulo === "licencias") return a.tipo.toLowerCase().includes("licencia");
    return ["ept", "caso_ept"].includes(a.caso_tipo?.toLowerCase() ?? "");
  });
}
