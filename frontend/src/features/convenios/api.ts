import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ConvenioRead = components["schemas"]["ConvenioRead"];
export type ConvenioCreate = components["schemas"]["ConvenioCreate"];
export type ConvenioUpdate = components["schemas"]["ConvenioUpdate"];
export type ActualizacionConvenios = components["schemas"]["ActualizacionConvenios"];
export type ConvenioSugerido = components["schemas"]["ConvenioSugerido"];

/** GET /api/v1/convenios?solo_seleccionables= */
export async function listarConvenios(
  soloSeleccionables = false,
): Promise<ConvenioRead[]> {
  const { data, error } = await api.GET("/api/v1/convenios", {
    params: { query: { solo_seleccionables: soloSeleccionables } },
  });
  if (error || !data) throw new Error("No se pudieron cargar los convenios");
  return data;
}

function mensajeEscritura(status: number, porDefecto: string): string {
  if (status === 409) return "Ya existe un convenio con ese nombre.";
  if (status === 422)
    return "Revisa los datos: el nombre es obligatorio y los convenios de SALUTEM no se renombran.";
  if (status === 403) return "Tu perfil no puede modificar el catálogo de convenios.";
  if (status === 404) return "El convenio ya no existe.";
  return porDefecto;
}

/** POST /api/v1/convenios */
export async function crearConvenio(body: ConvenioCreate): Promise<ConvenioRead> {
  const { data, error, response } = await api.POST("/api/v1/convenios", { body });
  if (error || !data)
    throw new Error(mensajeEscritura(response.status, "No se pudo crear el convenio"));
  return data;
}

/** PATCH /api/v1/convenios/{convenio_id} */
export async function actualizarConvenio(
  id: number,
  body: ConvenioUpdate,
): Promise<ConvenioRead> {
  const { data, error, response } = await api.PATCH("/api/v1/convenios/{convenio_id}", {
    params: { path: { convenio_id: id } },
    body,
  });
  if (error || !data)
    throw new Error(mensajeEscritura(response.status, "No se pudo actualizar el convenio"));
  return data;
}

/** POST /api/v1/convenios/actualizar-salutem (502 trae el motivo en `detail`). */
export async function actualizarDesdeSalutem(): Promise<ActualizacionConvenios> {
  const { data, error, response } = await api.POST("/api/v1/convenios/actualizar-salutem");
  if (!data) {
    const detalle = (error as { detail?: unknown } | undefined)?.detail;
    if (response.status === 502 && typeof detalle === "string") throw new Error(detalle);
    throw new Error(
      mensajeEscritura(response.status, "No se pudo actualizar desde SALUTEM"),
    );
  }
  return data;
}

/** GET /api/v1/convenios/para-reportes: nombres para los filtros de reportes. */
export async function conveniosParaReportes(): Promise<string[]> {
  const { data, error } = await api.GET("/api/v1/convenios/para-reportes");
  if (error || !data) throw new Error("No se pudieron cargar los convenios");
  return data;
}

/** GET /api/v1/convenios/sugerido?paciente_id=|rut= */
export async function convenioSugerido(q: {
  paciente_id?: number;
  rut?: string;
}): Promise<ConvenioSugerido> {
  const { data, error } = await api.GET("/api/v1/convenios/sugerido", {
    params: { query: q },
  });
  if (error || !data) throw new Error("No se pudo obtener el convenio sugerido");
  return data;
}
