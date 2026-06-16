import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acumuladoPorIngreso,
  actualizarISL,
  anularLicencia,
  buscarLicenciasPorFolio,
  crearLicencia,
  generarAlertasLicencias,
  getLicenciaDetalle,
  type LicenciaCreate,
  type LicenciaISLUpdate,
  type LicenciaRead,
} from "./api";

export function useLicenciasPorFolio(folio: string) {
  return useQuery({
    queryKey: ["licencias", "folio", folio],
    queryFn: () => buscarLicenciasPorFolio(folio),
    enabled: folio.trim().length > 0,
  });
}

export function useAcumulado(ingresoId: number | null) {
  return useQuery({
    queryKey: ["licencias", "acumulado", ingresoId],
    queryFn: () => acumuladoPorIngreso(ingresoId as number),
    enabled: ingresoId != null,
  });
}

export function useCrearLicencia(folio: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LicenciaCreate) => crearLicencia(body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["licencias", "folio", folio] }),
  });
}

export function useAnularLicencia(folio: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      observaciones,
    }: {
      id: number;
      observaciones: string;
    }) => anularLicencia(id, observaciones),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["licencias", "folio", folio] }),
  });
}

export function useActualizarISL(folio: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: LicenciaISLUpdate }) =>
      actualizarISL(id, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["licencias", "folio", folio] }),
  });
}

export function useGenerarAlertas() {
  return useMutation({
    mutationFn: () => generarAlertasLicencias(),
  });
}

/**
 * Fetches full LicenciaRead for each id in the provided array.
 * Returns an array of (data | undefined) in the same order.
 * Strategy: the folio-slim historial lacks tipo_reposo/eeag_gaf/envio_isl/folio_lm.
 * Per-row detail fetches are acceptable for small per-folio lists.
 */
export function useLicenciasDetalle(ids: number[]): Array<LicenciaRead | undefined> {
  const results = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["licencias", "detalle", id] as const,
      queryFn: () => getLicenciaDetalle(id),
      staleTime: 5 * 60 * 1000,
    })),
  });
  return results.map((r) => r.data);
}
