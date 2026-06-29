import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type CasoConsolidadoRead =
  components["schemas"]["CasoConsolidadoRead"];
export type FiltrosReporte = components["schemas"]["FiltrosReporte"];
export type ReporteAuditoriaRead =
  components["schemas"]["ReporteAuditoriaRead"];
export type FilaReporteRead = components["schemas"]["FilaReporteRead"];

export interface BuscarCasosParams {
  rut?: string;
  folio?: string;
  numero_siniestro?: string;
}

// ── CEPA-050: Vista consolidada ───────────────────────────────────────────────

/** GET /api/v1/auditoria/casos/{ingreso_id} */
export async function obtenerConsolidado(
  ingresoId: number,
): Promise<CasoConsolidadoRead> {
  const { data, error, response } = await api.GET(
    "/api/v1/auditoria/casos/{ingreso_id}",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error || !data) {
    if (response.status === 404)
      throw new Error("Caso no encontrado.");
    if (response.status === 403)
      throw new Error("No tienes permisos para ver auditoría.");
    throw new Error("No se pudo cargar la vista consolidada");
  }
  return data;
}

/** GET /api/v1/auditoria/casos?rut=&folio=&numero_siniestro= */
export async function buscarCasos(
  params: BuscarCasosParams,
): Promise<CasoConsolidadoRead[]> {
  const query: Record<string, string> = {};
  if (params.rut) query.rut = params.rut;
  if (params.folio) query.folio = params.folio;
  if (params.numero_siniestro) query.numero_siniestro = params.numero_siniestro;
  const { data, error } = await api.GET("/api/v1/auditoria/casos", {
    params: { query },
  });
  if (error || !data) throw new Error("No se pudieron buscar los casos");
  return data;
}

// ── CEPA-051: Reportes ─────────────────────────────────────────────────────────

/** POST /api/v1/auditoria/reportes */
export async function generarReporte(
  filtros: FiltrosReporte,
): Promise<ReporteAuditoriaRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/auditoria/reportes",
    { body: filtros },
  );
  if (error || !data) {
    if (response.status === 422)
      throw new Error("El período (desde/hasta) es obligatorio.");
    throw new Error("No se pudo generar el reporte");
  }
  return data;
}

/** POST /api/v1/auditoria/reportes/descargar → dispara descarga del CSV. */
export async function descargarReporteCsv(
  filtros: FiltrosReporte,
): Promise<void> {
  const { data, error } = await api.POST(
    "/api/v1/auditoria/reportes/descargar",
    { body: filtros, parseAs: "blob" },
  );
  if (error || !data) throw new Error("No se pudo descargar el reporte CSV");
  const blob = data as Blob;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `reporte_auditoria_${filtros.fecha_desde}_${filtros.fecha_hasta}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
