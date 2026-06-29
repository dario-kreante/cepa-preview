import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarRegistro,
  agregarIndicacion,
  crearReceta,
  crearRegistro,
  crearSeguimiento,
  generarAlertasRevision,
  listarIndicaciones,
  listarRecetas,
  listarSeguimientos,
  obtenerRegistro,
  type EsquemaIndicacionBody,
  type RecetaBody,
  type RegistroFarmacologicoCreate,
  type RegistroFarmacologicoUpdate,
  type SeguimTratamientoBody,
} from "./api";

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useRegistro(ingresoId: number) {
  return useQuery({
    queryKey: ["farmacos", ingresoId, "registro"],
    queryFn: () => obtenerRegistro(ingresoId),
    enabled: !!ingresoId,
  });
}

export function useIndicaciones(ingresoId: number) {
  return useQuery({
    queryKey: ["farmacos", ingresoId, "esquema"],
    queryFn: () => listarIndicaciones(ingresoId),
    enabled: !!ingresoId,
  });
}

export function useRecetas(ingresoId: number) {
  return useQuery({
    queryKey: ["farmacos", ingresoId, "recetas"],
    queryFn: () => listarRecetas(ingresoId),
    enabled: !!ingresoId,
  });
}

export function useSeguimientos(ingresoId: number) {
  return useQuery({
    queryKey: ["farmacos", ingresoId, "seguimiento"],
    queryFn: () => listarSeguimientos(ingresoId),
    enabled: !!ingresoId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

export function useCrearRegistro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RegistroFarmacologicoCreate) => crearRegistro(body),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({
        queryKey: ["farmacos", vars.ingreso_id, "registro"],
      }),
  });
}

export function useActualizarRegistro(ingresoId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RegistroFarmacologicoUpdate) =>
      actualizarRegistro(ingresoId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["farmacos", ingresoId, "registro"] }),
  });
}

export function useAgregarIndicacion(ingresoId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EsquemaIndicacionBody) =>
      agregarIndicacion(ingresoId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["farmacos", ingresoId, "esquema"] }),
  });
}

export function useCrearReceta(ingresoId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecetaBody) => crearReceta(ingresoId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["farmacos", ingresoId, "recetas"] }),
  });
}

export function useCrearSeguimiento(ingresoId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SeguimTratamientoBody) =>
      crearSeguimiento(ingresoId, body),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["farmacos", ingresoId, "seguimiento"],
      }),
  });
}

export function useGenerarAlertasRevision() {
  return useMutation({
    mutationFn: () => generarAlertasRevision(),
  });
}
