import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarCaso,
  actualizarReca,
  crearCaso,
  crearReca,
  listarCasos,
  obtenerCaso,
  obtenerReca,
  registrarCierre,
  type CasoReintegroCreate,
  type CasoReintegroUpdate,
  type CierreReintegroUpdate,
  type RecaCreate,
  type RecaUpdate,
} from "./api";

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useCasosPorIngreso(ingresoId: number | null) {
  return useQuery({
    queryKey: ["reintegro", "ingreso", ingresoId],
    queryFn: () => listarCasos(ingresoId ?? undefined),
    enabled: !!ingresoId,
  });
}

export function useCaso(casoId: number) {
  return useQuery({
    queryKey: ["reintegro", casoId],
    queryFn: () => obtenerCaso(casoId),
    enabled: !!casoId,
  });
}

export function useReca(casoId: number) {
  return useQuery({
    queryKey: ["reintegro", casoId, "reca"],
    queryFn: () => obtenerReca(casoId),
    enabled: !!casoId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

/** Crea un caso de reintegro nuevo. */
export function useCrearCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CasoReintegroCreate) => crearCaso(body),
    onSuccess: (caso) =>
      qc.invalidateQueries({
        queryKey: ["reintegro", "ingreso", caso.ingreso_id],
      }),
  });
}

export function useActualizarCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      casoId,
      body,
    }: {
      casoId: number;
      body: CasoReintegroUpdate;
    }) => actualizarCaso(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] }),
  });
}

export function useCrearReca() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: RecaCreate }) =>
      crearReca(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["reintegro", casoId, "reca"] }),
  });
}

export function useActualizarReca() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: RecaUpdate }) =>
      actualizarReca(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["reintegro", casoId, "reca"] }),
  });
}

export function useRegistrarCierre() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      casoId,
      body,
    }: {
      casoId: number;
      body: CierreReintegroUpdate;
    }) => registrarCierre(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] }),
  });
}
