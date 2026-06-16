import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acumuladoPorIngreso,
  actualizarISL,
  anularLicencia,
  buscarLicenciasPorFolio,
  crearLicencia,
  generarAlertasLicencias,
  type LicenciaCreate,
  type LicenciaISLUpdate,
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
