import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type RegistroFarmacologicoRead =
  components["schemas"]["RegistroFarmacologicoRead"];
export type RegistroFarmacologicoCreate =
  components["schemas"]["RegistroFarmacologicoCreate"];
export type RegistroFarmacologicoUpdate =
  components["schemas"]["RegistroFarmacologicoUpdate"];

export type EsquemaIndicacionRead =
  components["schemas"]["EsquemaIndicacionRead"];
export type EsquemaIndicacionBody =
  components["schemas"]["EsquemaIndicacionBody"];

export type RecetaRead = components["schemas"]["RecetaRead"];
export type RecetaBody = components["schemas"]["RecetaBody"];

export type SeguimTratamientoRead =
  components["schemas"]["SeguimTratamientoRead"];
export type SeguimTratamientoBody =
  components["schemas"]["SeguimTratamientoBody"];

export type AlertaFarmacosRead =
  components["schemas"]["app__schemas__farmacos__AlertaRead"];

export type EstadoFarmacologico =
  components["schemas"]["EstadoFarmacologico"];
export type FrecuenciaFarmaco =
  components["schemas"]["FrecuenciaFarmaco"];

// ── API functions ────────────────────────────────────────────────────────────

/** GET /api/v1/registro-farmacologico/{ingreso_id}
 *  Returns null on 404 (no registro yet for this ingreso).
 */
export async function obtenerRegistro(
  ingresoId: number,
): Promise<RegistroFarmacologicoRead | null> {
  const { data, error, response } = await api.GET(
    "/api/v1/registro-farmacologico/{ingreso_id}",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error || !data) {
    if (response.status === 404) return null;
    throw new Error("No se pudo obtener el registro farmacológico");
  }
  return data;
}

/** POST /api/v1/registro-farmacologico */
export async function crearRegistro(
  body: RegistroFarmacologicoCreate,
): Promise<RegistroFarmacologicoRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/registro-farmacologico",
    { body },
  );
  if (error || !data) {
    if (response.status === 409)
      throw new Error("Ya existe un registro farmacológico para este ingreso.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el registro farmacológico");
  }
  return data;
}

/** PATCH /api/v1/registro-farmacologico/{ingreso_id} */
export async function actualizarRegistro(
  ingresoId: number,
  body: RegistroFarmacologicoUpdate,
): Promise<RegistroFarmacologicoRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/registro-farmacologico/{ingreso_id}",
    {
      params: { path: { ingreso_id: ingresoId } },
      body,
    },
  );
  if (error || !data)
    throw new Error("No se pudo actualizar el registro farmacológico");
  return data;
}

/** GET /api/v1/registro-farmacologico/{ingreso_id}/esquema */
export async function listarIndicaciones(
  ingresoId: number,
): Promise<EsquemaIndicacionRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/registro-farmacologico/{ingreso_id}/esquema",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error) throw new Error("No se pudieron cargar las indicaciones");
  return data ?? [];
}

/** POST /api/v1/registro-farmacologico/{ingreso_id}/esquema */
export async function agregarIndicacion(
  ingresoId: number,
  body: EsquemaIndicacionBody,
): Promise<EsquemaIndicacionRead> {
  const { data, error } = await api.POST(
    "/api/v1/registro-farmacologico/{ingreso_id}/esquema",
    {
      params: { path: { ingreso_id: ingresoId } },
      body,
    },
  );
  if (error || !data)
    throw new Error("No se pudo agregar la indicación al esquema");
  return data;
}

/** GET /api/v1/registro-farmacologico/{ingreso_id}/recetas */
export async function listarRecetas(
  ingresoId: number,
): Promise<RecetaRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/registro-farmacologico/{ingreso_id}/recetas",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error) throw new Error("No se pudieron cargar las recetas");
  return data ?? [];
}

/** POST /api/v1/registro-farmacologico/{ingreso_id}/recetas */
export async function crearReceta(
  ingresoId: number,
  body: RecetaBody,
): Promise<RecetaRead> {
  const { data, error } = await api.POST(
    "/api/v1/registro-farmacologico/{ingreso_id}/recetas",
    {
      params: { path: { ingreso_id: ingresoId } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudo crear la receta");
  return data;
}

/** GET /api/v1/registro-farmacologico/{ingreso_id}/seguimiento */
export async function listarSeguimientos(
  ingresoId: number,
): Promise<SeguimTratamientoRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error) throw new Error("No se pudieron cargar los seguimientos");
  return data ?? [];
}

/** POST /api/v1/registro-farmacologico/{ingreso_id}/seguimiento */
export async function crearSeguimiento(
  ingresoId: number,
  body: SeguimTratamientoBody,
): Promise<SeguimTratamientoRead> {
  const { data, error } = await api.POST(
    "/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
    {
      params: { path: { ingreso_id: ingresoId } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudo registrar el seguimiento");
  return data;
}

/** POST /api/v1/registro-farmacologico/recetas/alertas/generar */
export async function generarAlertasRevision(): Promise<AlertaFarmacosRead[]> {
  const { data, error } = await api.POST(
    "/api/v1/registro-farmacologico/recetas/alertas/generar",
    {},
  );
  if (error) throw new Error("No se pudieron generar las alertas de revisión");
  return data ?? [];
}
