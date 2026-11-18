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

/** Filtro por programa del reporte de ODAS (el backend compara sin mayúsculas y por fragmento). */
export type ProgramaFiltro = "regular" | "ley_karin" | "pipt";
export type EstadoGestion = "pendiente" | "solicitada" | "recibida";
export type ODAVencidaItem = components["schemas"]["ODAVencidaItem"];
export type ReporteODAEstadoResponse =
  components["schemas"]["ReporteODAEstadoResponse"];

/** GET /api/v1/reportes/odas-vencidas — sin filtros obligatorios. */
export async function reporteOdasVencidas(
  programa?: ProgramaFiltro,
): Promise<ReporteODASVencidasResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/odas-vencidas", {
    params: { query: programa ? { programa } : {} },
  });
  if (error || !data)
    throw new Error("No se pudo generar el reporte de ODAS vencidas");
  return data;
}

/** GET /api/v1/reportes/odas-estado — estado de la ODA de cada paciente (QA-006). */
export async function reporteOdasEstado(
  estadoCaso?: string,
): Promise<ReporteODAEstadoResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/odas-estado", {
    params: { query: estadoCaso ? { estado_caso: estadoCaso } : {} },
  });
  if (error || !data)
    throw new Error("No se pudo consultar el estado de las ODA");
  return data;
}

/** PATCH /api/v1/odas/{id}/gestion — estado de gestión de una ODA vencida. */
export async function cambiarGestionOda(
  odaId: number,
  estado: EstadoGestion,
): Promise<void> {
  const { error } = await api.PATCH("/api/v1/odas/{oda_id}/gestion", {
    params: { path: { oda_id: odaId } },
    body: { estado_gestion: estado },
  });
  if (error) throw new Error("No se pudo guardar el estado de gestión");
}

/** GET /api/v1/reportes/odas-vencidas/excel — descarga la tabla (mismo filtro) como .xlsx. */
export async function descargarOdasVencidasExcel(
  programa?: ProgramaFiltro,
): Promise<void> {
  const { data, error } = await api.GET(
    "/api/v1/reportes/odas-vencidas/excel",
    { params: { query: programa ? { programa } : {} }, parseAs: "blob" },
  );
  if (error || !data) throw new Error("No se pudo descargar el Excel");
  const url = URL.createObjectURL(data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `odas-vencidas-${new Date().toISOString().slice(0, 10)}.xlsx`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
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
