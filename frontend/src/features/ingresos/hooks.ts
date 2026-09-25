import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  buscarPacientes,
  crearIngreso,
  obtenerVista360,
  obtenerLicenciasPorIngreso,
  obtenerControlesPorIngreso,
  obtenerRecetasPorIngreso,
  listarFichasClinicas,
  importarDesdeSalutem,
  obtenerLicenciasSugeridas,
  actualizarIngreso,
  type IngresoCreate,
  type IngresoUpdate,
} from "./api";

export function useFichasClinicas(folio: string | undefined) {
  return useQuery({
    queryKey: ["fichas-clinicas", folio],
    queryFn: () => listarFichasClinicas(folio!),
    enabled: folio !== undefined,
  });
}

export function useImportarSalutem(folio: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => importarDesdeSalutem(folio!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fichas-clinicas", folio] });
      // Atenciones nuevas pueden traer licencias nuevas en sus indicaciones.
      qc.invalidateQueries({ queryKey: ["licencias", "folio", folio, "sugeridas"] });
    },
  });
}

/**
 * La clave cuelga de ["licencias", "folio", folio]: al registrar una licencia,
 * useCrearLicencia invalida ese prefijo y la sugerencia pasa a "ya registrada".
 */
export function useLicenciasSugeridas(folio: string | undefined) {
  return useQuery({
    queryKey: ["licencias", "folio", folio, "sugeridas"],
    queryFn: () => obtenerLicenciasSugeridas(folio!),
    enabled: folio !== undefined,
  });
}

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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pacientes"] });
      // La píldora "N activos" del Topbar cambia con cada ingreso nuevo.
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useActualizarIngreso(pacienteId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ingresoId, body }: { ingresoId: number; body: IngresoUpdate }) =>
      actualizarIngreso(ingresoId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pacientes", pacienteId, "vista360"] });
      qc.invalidateQueries({ queryKey: ["pacientes", "buscar"] });
      // Un cierre o derivación cambia el conteo de activos del Topbar.
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
