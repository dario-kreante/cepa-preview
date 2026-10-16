import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarProfesional,
  crearProfesional,
  importarDesdeSalutem,
  listarProfesionales,
  type ProfesionalCreate,
  type ProfesionalUpdate,
} from "./api";

const KEY = ["profesionales"];

/** Catálogo completo (Configuración) o solo activos (selector de Agenda). */
export function useProfesionales(soloActivos = false) {
  return useQuery({
    queryKey: [...KEY, { soloActivos }],
    queryFn: () => listarProfesionales(soloActivos),
  });
}

export function useCrearProfesional() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfesionalCreate) => crearProfesional(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useActualizarProfesional() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ProfesionalUpdate }) =>
      actualizarProfesional(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useImportarDesdeSalutem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: importarDesdeSalutem,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
