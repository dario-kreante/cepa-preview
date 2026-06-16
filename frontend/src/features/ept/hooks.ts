import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarCaso,
  actualizarPlazos,
  actualizarProceso,
  agregarContacto,
  crearCaso,
  crearPlazos,
  crearProceso,
  obtenerCaso,
  obtenerPlazos,
  obtenerProceso,
  type CasoEptCreate,
  type CasoEptUpdate,
  type ContactoEptPayload,
  type PlazoEptCreate,
  type PlazoEptUpdate,
  type ProcesoEptCreate,
  type ProcesoEptUpdate,
} from "./api";

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useCaso(casoId: number) {
  return useQuery({
    queryKey: ["ept", casoId],
    queryFn: () => obtenerCaso(casoId),
    enabled: !!casoId,
  });
}

export function useProceso(casoId: number) {
  return useQuery({
    queryKey: ["ept", casoId, "proceso"],
    queryFn: () => obtenerProceso(casoId),
    enabled: !!casoId,
  });
}

export function usePlazos(casoId: number) {
  return useQuery({
    queryKey: ["ept", casoId, "plazos"],
    queryFn: () => obtenerPlazos(casoId),
    enabled: !!casoId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

/** Crea un caso EPT nuevo; no hay casoId previo → no invalida nada. */
export function useCrearCaso() {
  return useMutation({
    mutationFn: (body: CasoEptCreate) => crearCaso(body),
  });
}

export function useActualizarCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: CasoEptUpdate }) =>
      actualizarCaso(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["ept", casoId] }),
  });
}

export function useAgregarContacto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      casoId,
      body,
    }: {
      casoId: number;
      body: ContactoEptPayload;
    }) => agregarContacto(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["ept", casoId] }),
  });
}

export function useCrearProceso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: ProcesoEptCreate }) =>
      crearProceso(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["ept", casoId, "proceso"] }),
  });
}

export function useActualizarProceso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: ProcesoEptUpdate }) =>
      actualizarProceso(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["ept", casoId, "proceso"] }),
  });
}

export function useCrearPlazos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: PlazoEptCreate }) =>
      crearPlazos(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["ept", casoId, "plazos"] }),
  });
}

export function useActualizarPlazos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: PlazoEptUpdate }) =>
      actualizarPlazos(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["ept", casoId, "plazos"] }),
  });
}
