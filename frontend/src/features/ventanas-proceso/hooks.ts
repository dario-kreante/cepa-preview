import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { crearVentana, listarVentanas, type VentanaProcesoCreate } from "./api";

const KEY = ["ventanas-proceso"];

export function useVentanas() {
  return useQuery({ queryKey: KEY, queryFn: listarVentanas });
}

export function useCrearVentana() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: VentanaProcesoCreate) => crearVentana(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
