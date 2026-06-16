import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  buscarPacientes,
  crearIngreso,
  obtenerVista360,
  obtenerLicenciasPorIngreso,
  obtenerControlesPorIngreso,
  obtenerRecetasPorIngreso,
  type IngresoCreate,
} from "./api";

export function useBuscarPacientes(q: string) {
  return useQuery({
    queryKey: ["pacientes", "buscar", q],
    queryFn: () => buscarPacientes(q),
    enabled: q.trim().length > 0,
  });
}

export function useVista360(id: number | null) {
  return useQuery({
    queryKey: ["pacientes", id, "vista360"],
    queryFn: () => obtenerVista360(id!),
    enabled: id !== null,
  });
}

export function useLicenciasPorIngreso(ingresoId: number | undefined) {
  return useQuery({
    queryKey: ["ingresos", ingresoId, "licencias"],
    queryFn: () => obtenerLicenciasPorIngreso(ingresoId!),
    enabled: ingresoId !== undefined,
  });
}

export function useControlesPorIngreso(ingresoId: number | undefined) {
  return useQuery({
    queryKey: ["ingresos", ingresoId, "controles"],
    queryFn: () => obtenerControlesPorIngreso(ingresoId!),
    enabled: ingresoId !== undefined,
  });
}

export function useRecetasPorIngreso(ingresoId: number | undefined) {
  return useQuery({
    queryKey: ["ingresos", ingresoId, "recetas"],
    queryFn: () => obtenerRecetasPorIngreso(ingresoId!),
    enabled: ingresoId !== undefined,
  });
}

export function useCrearIngreso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IngresoCreate) => crearIngreso(body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pacientes"] }); },
  });
}
