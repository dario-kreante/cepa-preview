import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { buscarPacientes, crearIngreso, obtenerVista360, type IngresoCreate } from "./api";

export function useBuscarPacientes(q: string) {
  return useQuery({
    queryKey: ["pacientes", "buscar", q],
    queryFn: () => buscarPacientes(q),
    enabled: q.trim().length > 0,
  });
}

export function useVista360(id: number) {
  return useQuery({ queryKey: ["pacientes", id, "vista360"], queryFn: () => obtenerVista360(id) });
}

export function useCrearIngreso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IngresoCreate) => crearIngreso(body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pacientes"] }); },
  });
}
