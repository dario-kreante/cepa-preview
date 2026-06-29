import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarLicencia,
  actualizarProximoControl,
  controlesPorIngreso,
  crearControl,
  obtenerControl,
  type ControlMedicoCreate,
  type LicenciaUpdate,
  type ProximoControlUpdate,
} from "./api";

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useControlesPorIngreso(ingresoId: number) {
  return useQuery({
    queryKey: ["controles", ingresoId],
    queryFn: () => controlesPorIngreso(ingresoId),
    enabled: !!ingresoId,
  });
}

export function useControl(controlId: number) {
  return useQuery({
    queryKey: ["controles", "detail", controlId],
    queryFn: () => obtenerControl(controlId),
    enabled: !!controlId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

/** Crea un control nuevo; invalida la lista del ingreso correspondiente. */
export function useCrearControl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ControlMedicoCreate) => crearControl(body),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({ queryKey: ["controles", vars.ingreso_id] }),
  });
}

/**
 * Actualiza el próximo control de un registro ya existente.
 *
 * Acepta `ingresoId` para invalidación dirigida de la lista por ingreso.
 * Si se omite, invalida todo el prefijo ["controles"] para cubrir
 * cualquier lista cacheada — mismo criterio que `useActualizarLicencia`.
 */
export function useActualizarProximoControl(ingresoId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      controlId,
      body,
    }: {
      controlId: number;
      body: ProximoControlUpdate;
    }) => actualizarProximoControl(controlId, body),
    onSuccess: () =>
      ingresoId
        ? qc.invalidateQueries({ queryKey: ["controles", ingresoId] })
        : qc.invalidateQueries({ queryKey: ["controles"] }),
  });
}

/**
 * Actualiza la licencia asociada a un control médico.
 *
 * Acepta `ingresoId` para invalidación dirigida de la lista por ingreso.
 * Si se omite, invalida todo el prefijo ["controles"].
 */
export function useActualizarLicencia(ingresoId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      controlId,
      body,
    }: {
      controlId: number;
      body: LicenciaUpdate;
    }) => actualizarLicencia(controlId, body),
    onSuccess: () =>
      ingresoId
        ? qc.invalidateQueries({ queryKey: ["controles", ingresoId] })
        : qc.invalidateQueries({ queryKey: ["controles"] }),
  });
}
