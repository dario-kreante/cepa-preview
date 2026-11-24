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

/**
 * Tras crear, anular o marcar ISL se refrescan todas las vistas de la licencia: el módulo
 * (por folio), la ficha del paciente (por ingreso) y el acumulado de días.
 */
function invalidarVistasLicencia(
  qc: ReturnType<typeof useQueryClient>,
  folio: string,
  ingresoId: number | undefined,
) {
  qc.invalidateQueries({ queryKey: ["licencias", "folio", folio] });
  qc.invalidateQueries({ queryKey: ["licencias", "acumulado"] });
  if (ingresoId !== undefined) {
    qc.invalidateQueries({ queryKey: ["ingresos", ingresoId, "licencias"] });
  }
}

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
    // La ficha del paciente cuenta las licencias por ingreso, no por folio.
    onSuccess: (_licencia, body) => invalidarVistasLicencia(qc, folio, body.ingreso_id),
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
    onSuccess: (licencia) => invalidarVistasLicencia(qc, folio, licencia?.ingreso_id),
  });
}

export function useActualizarISL(folio: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: LicenciaISLUpdate }) =>
      actualizarISL(id, body),
    onSuccess: (licencia) => invalidarVistasLicencia(qc, folio, licencia?.ingreso_id),
  });
}

export function useGenerarAlertas() {
  return useMutation({
    mutationFn: () => generarAlertasLicencias(),
  });
}
