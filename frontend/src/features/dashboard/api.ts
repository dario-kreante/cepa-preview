import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ResumenDashboard = components["schemas"]["ResumenDashboard"];

export interface DashboardFiltros {
  fecha_desde?: string;
  fecha_hasta?: string;
  programa?: string;
}

/** GET /api/v1/dashboard — indicadores multiprograma (filtros combinables, opcionales). */
export async function obtenerDashboard(
  filtros: DashboardFiltros = {},
): Promise<ResumenDashboard> {
  const query: Record<string, string> = {};
  if (filtros.fecha_desde) query.fecha_desde = filtros.fecha_desde;
  if (filtros.fecha_hasta) query.fecha_hasta = filtros.fecha_hasta;
  if (filtros.programa) query.programa = filtros.programa;
  const { data, error } = await api.GET("/api/v1/dashboard", {
    params: { query },
  });
  if (error || !data) throw new Error("No se pudo cargar el dashboard");
  return data;
}
