import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { descartarBorrador, listarPendientesFolio } from "./api";

export function usePendientesFolio(habilitado = true) {
  return useQuery({
    queryKey: ["pacientes", "pendientes-folio"],
    queryFn: listarPendientesFolio,
    enabled: habilitado,
  });
}

/** Descarta un borrador; refresca la lista y las alertas (la alerta se resuelve). */
export function useDescartarBorrador() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) =>
      descartarBorrador(id, motivo),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pacientes", "pendientes-folio"] });
      qc.invalidateQueries({ queryKey: ["alertas"] });
    },
  });
}
