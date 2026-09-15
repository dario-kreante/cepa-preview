import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type PacienteRead = components["schemas"]["PacienteRead"];
export type Vista360 = components["schemas"]["Vista360"];
export type IngresoCreate = components["schemas"]["IngresoCreate"];
export type IngresoRead = components["schemas"]["IngresoRead"];
export type LicenciaRead = components["schemas"]["app__schemas__licencia__LicenciaRead"];
export type ControlMedicoRead = components["schemas"]["ControlMedicoRead"];
export type RecetaRead = components["schemas"]["RecetaRead"];
export type FichaClinicaRead = components["schemas"]["FichaClinicaRead"];
export type IngresoUpdate = components["schemas"]["IngresoUpdate"];

/** Edita la ficha del ingreso (BUG-2608-01). RUT y folio no forman parte del cuerpo. */
export async function actualizarIngreso(
  ingresoId: number,
  body: IngresoUpdate,
): Promise<IngresoRead> {
  const { data, error, response } = await api.PUT("/api/v1/ingresos/{ingreso_id}", {
    params: { path: { ingreso_id: ingresoId } },
    body,
  });
  if (error || !data) {
    if (response.status === 404) throw new Error("El ingreso ya no existe.");
    if (response.status === 422) throw new Error("Hay datos inválidos. Revisa los campos.");
    if (response.status === 403) throw new Error("Tu perfil no puede editar fichas.");
    throw new Error("El servidor no respondió. Intenta nuevamente.");
  }
  return data;
}

export async function listarFichasClinicas(folio: string): Promise<FichaClinicaRead[]> {
  const { data, error } = await api.GET("/api/v1/fichas-clinicas/{folio}", {
    params: { path: { folio } },
  });
  if (error) throw new Error("No se pudieron cargar las atenciones de SALUTEM");
  return data ?? [];
}

/**
 * Trae desde SALUTEM las atenciones del paciente que caen en la ventana del
 * ingreso. El backend explica en `detail` por qué falló (RUT rechazado, SALUTEM
 * caído), y ese texto es lo que tiene que leer el usuario.
 */
export async function importarDesdeSalutem(folio: string): Promise<FichaClinicaRead[]> {
  const { data, error } = await api.POST("/api/v1/fichas-clinicas/pull-salutem", {
    body: { folio },
  });
  if (error) {
    const detalle = (error as { detail?: unknown }).detail;
    throw new Error(
      typeof detalle === "string" ? detalle : "No se pudo importar desde SALUTEM",
    );
  }
  return data ?? [];
}

export async function buscarPacientes(q: string): Promise<PacienteRead[]> {
  const { data, error } = await api.GET("/api/v1/pacientes/buscar", { params: { query: { q } } });
  if (error) throw new Error("Error al buscar pacientes");
  return data ?? [];
}

export async function obtenerVista360(id: number): Promise<Vista360> {
  const { data, error } = await api.GET("/api/v1/pacientes/{paciente_id}/vista-360", {
    params: { path: { paciente_id: id } },
  });
  if (error || !data) throw new Error("No se pudo cargar la vista 360");
  return data;
}

export async function crearIngreso(body: IngresoCreate): Promise<IngresoRead> {
  const { data, error, response } = await api.POST("/api/v1/ingresos", { body });
  if (error || !data) {
    if (response.status === 409) throw new Error("El folio ya está emitido para otro ingreso.");
    if (response.status === 422) throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el ingreso");
  }
  return data;
}

export async function obtenerLicenciasPorIngreso(ingresoId: number): Promise<LicenciaRead[]> {
  const { data, error } = await api.GET("/api/v1/ingresos/{ingreso_id}/licencias", {
    params: { path: { ingreso_id: ingresoId } },
  });
  if (error) throw new Error("No se pudieron cargar las licencias");
  return data ?? [];
}

export async function obtenerControlesPorIngreso(ingresoId: number): Promise<ControlMedicoRead[]> {
  const { data, error } = await api.GET("/api/v1/controles-medicos/por-ingreso/{ingreso_id}", {
    params: { path: { ingreso_id: ingresoId } },
  });
  if (error) throw new Error("No se pudieron cargar los controles médicos");
  return data ?? [];
}

export async function obtenerRecetasPorIngreso(ingresoId: number): Promise<RecetaRead[]> {
  const { data, error } = await api.GET("/api/v1/registro-farmacologico/{ingreso_id}/recetas", {
    params: { path: { ingreso_id: ingresoId } },
  });
  if (error) throw new Error("No se pudieron cargar las recetas");
  return data ?? [];
}
