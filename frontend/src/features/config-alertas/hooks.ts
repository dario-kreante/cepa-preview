import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  crearFestivo,
  eliminarFestivo,
  guardarConfig,
  listarConfig,
  listarFestivos,
  type ConfigAlertaItem,
  type FestivoCreate,
} from "./api";

const KEY_CONFIG = ["config-alertas"];
const KEY_FESTIVOS = ["config-alertas", "festivos"];

export function useConfigAlertas() {
  return useQuery({ queryKey: KEY_CONFIG, queryFn: listarConfig });
}

export function useGuardarConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConfigAlertaItem[]) => guardarConfig(body),
    onSuccess: (data) => qc.setQueryData(KEY_CONFIG, data),
  });
}

export function useFestivos() {
  return useQuery({ queryKey: KEY_FESTIVOS, queryFn: listarFestivos });
}

export function useCrearFestivo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FestivoCreate) => crearFestivo(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY_FESTIVOS }),
  });
}

export function useEliminarFestivo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => eliminarFestivo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY_FESTIVOS }),
  });
}
