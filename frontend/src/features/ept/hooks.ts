import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarCaso,
  actualizarPlazos,
  actualizarProceso,
  agregarContacto,
  crearCaso,
  crearPlazos,
  crearProceso,
  eliminarCaso,
  listarCasosPorPaciente,
  obtenerCaso,
  obtenerPlazos,
  obtenerPlazosSugeridos,
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

export function useCasosPorPaciente(pacienteId: number | null) {
  return useQuery({
    queryKey: ["ept", "paciente", pacienteId],
    queryFn: () => listarCasosPorPaciente(pacienteId!),
    enabled: !!pacienteId,
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

/** Plazos que propone el backend (ingreso + 15 / + 19, día hábil anterior; QA-009). */
export function usePlazosSugeridos(casoId: number, enabled = true) {
  return useQuery({
    queryKey: ["ept", casoId, "plazos-sugeridos"],
    queryFn: () => obtenerPlazosSugeridos(casoId),
    enabled: !!casoId && enabled,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

/**
 * QA-009: al guardar un caso, su proceso o sus plazos el backend genera (o resuelve) sus
 * alertas en el mismo request; se refrescan las alertas y el listado del paciente.
 */
function refrescarTrasGuardar(qc: ReturnType<typeof useQueryClient>, casoId: number, parte?: string) {
  return Promise.all([
    qc.invalidateQueries({ queryKey: parte ? ["ept", casoId, parte] : ["ept", casoId] }),
    qc.invalidateQueries({ queryKey: ["ept", "paciente"] }),
    qc.invalidateQueries({ queryKey: ["alertas"] }),
  ]);
}

/** Crea un caso EPT nuevo; refresca el listado del paciente. */
export function useCrearCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CasoEptCreate) => crearCaso(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ept", "paciente"] }),
  });
}

/** Elimina un caso EPT (creado por error); refresca el listado del paciente. */
export function useEliminarCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (casoId: number) => eliminarCaso(casoId),
    onSuccess: (_data, casoId) => {
      qc.removeQueries({ queryKey: ["ept", casoId] });
      return qc.invalidateQueries({ queryKey: ["ept", "paciente"] });
    },
  });
}

export function useActualizarCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: CasoEptUpdate }) =>
      actualizarCaso(casoId, body),
    onSuccess: (_data, { casoId }) => refrescarTrasGuardar(qc, casoId),
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
    onSuccess: (_data, { casoId }) => refrescarTrasGuardar(qc, casoId, "proceso"),
  });
}

export function useActualizarProceso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: ProcesoEptUpdate }) =>
      actualizarProceso(casoId, body),
    onSuccess: (_data, { casoId }) => refrescarTrasGuardar(qc, casoId, "proceso"),
  });
}

export function useCrearPlazos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: PlazoEptCreate }) =>
      crearPlazos(casoId, body),
    onSuccess: (_data, { casoId }) => refrescarTrasGuardar(qc, casoId, "plazos"),
  });
}

export function useActualizarPlazos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: PlazoEptUpdate }) =>
      actualizarPlazos(casoId, body),
    onSuccess: (_data, { casoId }) => refrescarTrasGuardar(qc, casoId, "plazos"),
  });
}
