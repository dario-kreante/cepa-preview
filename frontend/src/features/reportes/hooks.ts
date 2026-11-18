import { useMutation } from "@tanstack/react-query";
import {
  cambiarGestionOda,
  descargarOdasVencidasExcel,
  importarReporteIsl,
  reporteAdherencia,
  reporteCargaLaboral,
  reporteConvenio,
  reporteLicencias,
  reporteOdasEstado,
  reporteOdasVencidas,
  reporteOperativo,
  type EstadoGestion,
  type ProgramaFiltro,
  type RangoFechas,
} from "./api";

export function useReporteOperativo() {
  return useMutation({ mutationFn: (r: RangoFechas) => reporteOperativo(r) });
}

export function useReporteConvenio() {
  return useMutation({
    mutationFn: (r: RangoFechas & { tipo_convenio: string }) =>
      reporteConvenio(r),
  });
}

export function useReporteCargaLaboral() {
  return useMutation({
    mutationFn: (r: RangoFechas) => reporteCargaLaboral(r),
  });
}

export function useReporteLicencias() {
  return useMutation({ mutationFn: (r: RangoFechas) => reporteLicencias(r) });
}

export function useReporteOdasVencidas() {
  return useMutation({
    mutationFn: (programa: ProgramaFiltro | void) => reporteOdasVencidas(programa || undefined),
  });
}

export function useReporteOdasEstado() {
  return useMutation({
    mutationFn: (estadoCaso: string | void) => reporteOdasEstado(estadoCaso || undefined),
  });
}

export function useCambiarGestionOda() {
  return useMutation({
    mutationFn: ({ odaId, estado }: { odaId: number; estado: EstadoGestion }) =>
      cambiarGestionOda(odaId, estado),
  });
}

export function useDescargarOdasExcel() {
  return useMutation({
    mutationFn: (programa: ProgramaFiltro | void) =>
      descargarOdasVencidasExcel(programa || undefined),
  });
}

export function useImportarReporteIsl() {
  return useMutation({
    mutationFn: ({ file, dryRun }: { file: File; dryRun: boolean }) =>
      importarReporteIsl(file, dryRun),
  });
}

export function useReporteAdherencia() {
  return useMutation({ mutationFn: (folioId: number) => reporteAdherencia(folioId) });
}
