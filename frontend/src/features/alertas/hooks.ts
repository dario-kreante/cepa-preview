import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { actualizarAlerta, listarAlertas, listarTareas } from "./api";
import type { EstadoAlerta } from "./api";

export function useAlertas() {
  return useQuery({ queryKey: ["alertas"], queryFn: listarAlertas });
}

export function useTareas() {
  return useQuery({ queryKey: ["tareas"], queryFn: listarTareas });
}

export function useActualizarAlerta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, estado }: { id: number; estado: EstadoAlerta }) =>
      actualizarAlerta(id, estado),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alertas"] });
    },
  });
}
