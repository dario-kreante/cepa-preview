import { useMutation } from "@tanstack/react-query";
import {
  reporteCargaLaboral,
  reporteConvenio,
  reporteLicencias,
  reporteOdasVencidas,
  reporteOperativo,
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
  return useMutation({ mutationFn: () => reporteOdasVencidas() });
}
