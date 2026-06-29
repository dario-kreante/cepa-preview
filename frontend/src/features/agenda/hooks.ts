import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  confirmarCitas,
  crearDisponibilidad,
  generarPropuesta,
  listarCitas,
  listarDisponibilidad,
  listarPropuestas,
  type DisponibilidadProfCreate,
  type GenerarPropuestaRequest,
} from "./api";

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useDisponibilidad(profesionalId: number | null) {
  return useQuery({
    queryKey: ["agenda", "disponibilidad", profesionalId],
    queryFn: () => listarDisponibilidad(profesionalId as number),
    enabled: !!profesionalId,
  });
}

export function usePropuestas(profesionalId: number | null) {
  return useQuery({
    queryKey: ["agenda", "propuestas", profesionalId],
    queryFn: () => listarPropuestas(profesionalId ?? undefined),
    enabled: !!profesionalId,
  });
}

export function useCitas(propuestaId: number | null) {
  return useQuery({
    queryKey: ["agenda", "citas", propuestaId],
    queryFn: () => listarCitas(propuestaId as number),
    enabled: !!propuestaId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

export function useCrearDisponibilidad() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DisponibilidadProfCreate) => crearDisponibilidad(body),
    onSuccess: (_d, body) =>
      qc.invalidateQueries({
        queryKey: ["agenda", "disponibilidad", body.profesional_id],
      }),
  });
}

export function useGenerarPropuesta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: GenerarPropuestaRequest) => generarPropuesta(body),
    onSuccess: (_d, body) =>
      qc.invalidateQueries({
        queryKey: ["agenda", "propuestas", body.profesional_id],
      }),
  });
}

export function useConfirmarCitas() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      propuestaId,
      citaIds,
    }: {
      propuestaId: number;
      citaIds: number[];
    }) => confirmarCitas(propuestaId, citaIds),
    onSuccess: (_d, { propuestaId }) =>
      qc.invalidateQueries({ queryKey: ["agenda", "citas", propuestaId] }),
  });
}
