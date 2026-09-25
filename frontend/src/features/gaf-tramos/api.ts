import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type GafTramoRead = components["schemas"]["GafTramoRead"];

/** GET /api/v1/gaf-tramos — catálogo de tramos de GAF (v5 D18, COMP-2609-12). */
export async function listarGafTramos(): Promise<GafTramoRead[]> {
  const { data, error } = await api.GET("/api/v1/gaf-tramos");
  if (error || !data) throw new Error("No se pudieron cargar los tramos de GAF");
  return data;
}
