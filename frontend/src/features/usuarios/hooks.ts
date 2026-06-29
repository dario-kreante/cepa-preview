import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  activarUsuario,
  actualizarUsuario,
  crearUsuario,
  desactivarUsuario,
  listarUsuarios,
  type UsuarioCreate,
  type UsuarioUpdate,
} from "./api";

const KEY = ["usuarios"];

export function useUsuarios() {
  return useQuery({ queryKey: KEY, queryFn: listarUsuarios });
}

export function useCrearUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UsuarioCreate) => crearUsuario(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useActualizarUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UsuarioUpdate }) =>
      actualizarUsuario(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDesactivarUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => desactivarUsuario(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useActivarUsuario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => activarUsuario(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
