import { useMutation, useQuery } from "@tanstack/react-query";
import {
  buscarCasos,
  generarReporte,
  obtenerConsolidado,
  type BuscarCasosParams,
  type FiltrosReporte,
} from "./api";

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useConsolidado(ingresoId: number | null) {
  return useQuery({
    queryKey: ["auditoria", "consolidado", ingresoId],
    queryFn: () => obtenerConsolidado(ingresoId as number),
    enabled: !!ingresoId,
  });
}

export function useBuscarCasos(params: BuscarCasosParams, enabled: boolean) {
  return useQuery({
    queryKey: ["auditoria", "buscar", params],
    queryFn: () => buscarCasos(params),
    enabled,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

export function useGenerarReporte() {
  return useMutation({
    mutationFn: (filtros: FiltrosReporte) => generarReporte(filtros),
  });
}
