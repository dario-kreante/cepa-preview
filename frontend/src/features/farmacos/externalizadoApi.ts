import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type FarmacoConvenioItem = components["schemas"]["FarmacoConvenioItem"];
export type ReporteFarmacosConvenioResponse =
  components["schemas"]["ReporteFarmacosConvenioResponse"];
export type ClasificacionFarmaco = FarmacoConvenioItem["clasificacion"];

export interface FiltroExternalizado {
  fecha_desde: string;
  fecha_hasta: string;
  paciente_id?: number;
}

function query(f: FiltroExternalizado) {
  return {
    fecha_desde: f.fecha_desde,
    fecha_hasta: f.fecha_hasta,
    ...(f.paciente_id ? { paciente_id: f.paciente_id } : {}),
  };
}

/** GET /api/v1/reportes/farmacos-convenio — fármacos recetados del período por convenio. */
export async function reporteExternalizado(
  f: FiltroExternalizado,
): Promise<ReporteFarmacosConvenioResponse> {
  const { data, error } = await api.GET("/api/v1/reportes/farmacos-convenio", {
    params: { query: query(f) },
  });
  if (error || !data) throw new Error("No se pudo generar el reporte Externalizado");
  return data;
}

/** GET /api/v1/reportes/farmacos-convenio/excel — la misma tabla como .xlsx. */
export async function descargarExternalizadoExcel(f: FiltroExternalizado): Promise<void> {
  const { data, error } = await api.GET("/api/v1/reportes/farmacos-convenio/excel", {
    params: { query: query(f) },
    parseAs: "blob",
  });
  if (error || !data) throw new Error("No se pudo descargar el Excel");
  const url = URL.createObjectURL(data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `externalizado-${f.fecha_desde}-${f.fecha_hasta}.xlsx`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export function useReporteExternalizado() {
  return useMutation({ mutationFn: (f: FiltroExternalizado) => reporteExternalizado(f) });
}

export function useDescargarExternalizadoExcel() {
  return useMutation({ mutationFn: (f: FiltroExternalizado) => descargarExternalizadoExcel(f) });
}
