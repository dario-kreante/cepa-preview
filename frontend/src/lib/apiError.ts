/**
 * Mensaje que el usuario debe leer cuando el backend rechaza una operación.
 *
 * Las reglas de negocio responden con `detail` en texto, escrito para el
 * usuario (p. ej. «Marcaste que hay testigos: indica al menos 1…»). Ese texto
 * explica qué corregir; un mensaje genérico no. Los errores de esquema de
 * FastAPI traen `detail` como lista en inglés: ahí se usa el respaldo.
 */
export function mensajeDelBackend(error: unknown, respaldo: string): string {
  const detalle = (error as { detail?: unknown } | null | undefined)?.detail;
  return typeof detalle === "string" && detalle.trim() !== "" ? detalle : respaldo;
}
