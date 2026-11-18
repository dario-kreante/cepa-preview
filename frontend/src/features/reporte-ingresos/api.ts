import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ReporteIngresos = components["schemas"]["ReporteIngresosResponse"];
export type IngresoReporteItem = components["schemas"]["IngresoReporteItem"];

/** GET /api/v1/reportes/ingresos — ingresos del período más pendientes de folio. */
export async function obtenerReporteIngresos(periodo: {
  fecha_desde: string;
  fecha_hasta: string;
}): Promise<ReporteIngresos> {
  const { data, error } = await api.GET("/api/v1/reportes/ingresos", {
    params: { query: periodo },
  });
  if (error || !data) throw new Error("No se pudo cargar el reporte de ingresos");
  return data;
}
