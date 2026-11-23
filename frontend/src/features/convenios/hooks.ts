import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarConvenio,
  actualizarDesdeSalutem,
  convenioSugerido,
  conveniosParaReportes,
  crearConvenio,
  listarConvenios,
  type ConvenioCreate,
  type ConvenioUpdate,
} from "./api";

const KEY = ["convenios"];

/** Catálogo completo (Configuración) o solo los seleccionables (ficha de ingreso). */
export function useConvenios(soloSeleccionables = false) {
  return useQuery({
    queryKey: [...KEY, { soloSeleccionables }],
    queryFn: () => listarConvenios(soloSeleccionables),
  });
}

export function useCrearConvenio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConvenioCreate) => crearConvenio(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useActualizarConvenio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ConvenioUpdate }) =>
      actualizarConvenio(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useActualizarDesdeSalutem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: actualizarDesdeSalutem,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** Nombres de convenio para los filtros de reportes. */
export function useConveniosParaReportes() {
  return useQuery({
    queryKey: [...KEY, "para-reportes"],
    queryFn: conveniosParaReportes,
  });
}

/** Convenio que sugiere el historial del paciente; deshabilitado con `null`. */
export function useConvenioSugerido(q: { paciente_id?: number; rut?: string } | null) {
  return useQuery({
    queryKey: [...KEY, "sugerido", q],
    queryFn: () => convenioSugerido(q as { paciente_id?: number; rut?: string }),
    enabled: q !== null,
  });
}
