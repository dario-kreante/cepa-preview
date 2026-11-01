import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ReporteOperativoResponse =
  components["schemas"]["ReporteOperativoResponse"];
export type ReporteCumplimientoResponse =
  components["schemas"]["ReporteCumplimientoResponse"];
export type ReporteCargaLaboralResponse =
  components["schemas"]["ReporteCargaLaboralResponse"];
export type ReporteLicenciasResponse =
  components["schemas"]["ReporteLicenciasResponse"];
export type ReporteODASVencidasResponse =
  components["schemas"]["ReporteODASVencidasResponse"];
export type AdherenciaPaciente = components["schemas"]["AdherenciaPaciente"];

export interface RangoFechas {
  fecha_desde: string;
  fecha_hasta: string;
}

/** GET /api/v1/reportes/operativo */
export async function reporteOperativo(
  r: RangoFechas,
): Promise<ReporteOperativoResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/operativo", {
    params: { query: { fecha_desde: r.fecha_desde, fecha_hasta: r.fecha_hasta } },
  });
  if (error || !data) throw new Error("No se pudo generar el reporte operativo");
  return data;
}

/** GET /api/v1/reportes/convenio */
export async function reporteConvenio(
  r: RangoFechas & { tipo_convenio: string },
): Promise<ReporteCumplimientoResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/convenio", {
    params: {
      query: {
        tipo_convenio: r.tipo_convenio,
        fecha_desde: r.fecha_desde,
        fecha_hasta: r.fecha_hasta,
      },
    },
  });
  if (error || !data)
    throw new Error("No se pudo generar el reporte de convenio");
  return data;
}

/** GET /api/v1/reportes/carga-laboral */
export async function reporteCargaLaboral(
  r: RangoFechas,
): Promise<ReporteCargaLaboralResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/carga-laboral", {
    params: { query: { fecha_desde: r.fecha_desde, fecha_hasta: r.fecha_hasta } },
  });
  if (error || !data)
    throw new Error("No se pudo generar el reporte de carga laboral");
  return data;
}

/** GET /api/v1/reportes/licencias */
export async function reporteLicencias(
  r: RangoFechas,
): Promise<ReporteLicenciasResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/licencias", {
    params: { query: { fecha_desde: r.fecha_desde, fecha_hasta: r.fecha_hasta } },
  });
  if (error || !data)
    throw new Error("No se pudo generar el reporte de licencias");
  return data;
}

/** GET /api/v1/reportes/odas-vencidas — sin filtros obligatorios. */
export async function reporteOdasVencidas(): Promise<ReporteODASVencidasResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/odas-vencidas", {
    params: { query: {} },
  });
  if (error || !data)
    throw new Error("No se pudo generar el reporte de ODAS vencidas");
  return data;
}

export type OdaImportResumen = components["schemas"]["OdaImportResumen"];

/**
 * POST /api/v1/odas/importar (multipart) — carga el «Reporte Prestador» del portal ISL.
 * Con `dryRun` el backend arma el resumen sin guardar nada (previsualización).
 */
export async function importarReporteIsl(
  file: File,
  dryRun: boolean,
): Promise<OdaImportResumen> {
  const fd = new FormData();
  fd.append("file", file);
  const { data, error } = await api.POST("/api/v1/odas/importar", {
    params: { query: { dry_run: dryRun } },
    body: fd as never,
    bodySerializer: (b) => b as unknown as FormData,
  });
  if (error || !data) {
    const detail = (error as { detail?: unknown } | undefined)?.detail;
    throw new Error(
      typeof detail === "string" ? detail : "No se pudo procesar el archivo.",
    );
  }
  return data;
}

/** GET /api/v1/reportes/adherencia/{folio_id} — adherencia y avance de un ingreso. */
export async function reporteAdherencia(
  folioId: number,
): Promise<AdherenciaPaciente> {
  const { data, error, response } = await api.GET(
    "/api/v1/reportes/adherencia/{folio_id}",
    { params: { path: { folio_id: folioId } } },
  );
  if (error || !data) {
    if (response.status === 404)
      throw new Error("No se encontró el ingreso indicado.");
    throw new Error("No se pudo obtener la adherencia");
  }
  return data;
}
