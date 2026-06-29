import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type CasoEptCreate = components["schemas"]["CasoEptCreate"];
export type CasoEptRead = components["schemas"]["CasoEptRead"];
export type CasoEptUpdate = components["schemas"]["CasoEptUpdate"];

export type ContactoEptPayload = components["schemas"]["ContactoEptPayload"];
export type ContactoEptRead = components["schemas"]["ContactoEptRead"];

export type ProcesoEptRead = components["schemas"]["ProcesoEptRead"];
export type ProcesoEptCreate = components["schemas"]["ProcesoEptCreate"];
export type ProcesoEptUpdate = components["schemas"]["ProcesoEptUpdate"];

export type PlazoEptRead = components["schemas"]["PlazoEptRead"];
export type PlazoEptCreate = components["schemas"]["PlazoEptCreate"];
export type PlazoEptUpdate = components["schemas"]["PlazoEptUpdate"];

export type FactorRiesgo = components["schemas"]["FactorRiesgo"];
export type EstadoEpt = components["schemas"]["EstadoEpt"];
export type EstadoCumplimiento = components["schemas"]["EstadoCumplimiento"];

// ── API functions ────────────────────────────────────────────────────────────

/** POST /api/v1/casos-ept */
export async function crearCaso(body: CasoEptCreate): Promise<CasoEptRead> {
  const { data, error, response } = await api.POST("/api/v1/casos-ept", {
    body,
  });
  if (error || !data) {
    if (response.status === 409)
      throw new Error("Ya existe un caso EPT para este ingreso.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el caso EPT");
  }
  return data;
}

/** GET /api/v1/casos-ept/{caso_id} */
export async function obtenerCaso(casoId: number): Promise<CasoEptRead> {
  const { data, error } = await api.GET("/api/v1/casos-ept/{caso_id}", {
    params: { path: { caso_id: casoId } },
  });
  if (error || !data) throw new Error("No se pudo obtener el caso EPT");
  return data;
}

/** PATCH /api/v1/casos-ept/{caso_id} */
export async function actualizarCaso(
  casoId: number,
  body: CasoEptUpdate,
): Promise<CasoEptRead> {
  const { data, error } = await api.PATCH("/api/v1/casos-ept/{caso_id}", {
    params: { path: { caso_id: casoId } },
    body,
  });
  if (error || !data) throw new Error("No se pudo actualizar el caso EPT");
  return data;
}

/** POST /api/v1/casos-ept/{caso_id}/contactos */
export async function agregarContacto(
  casoId: number,
  body: ContactoEptPayload,
): Promise<ContactoEptRead> {
  const { data, error } = await api.POST(
    "/api/v1/casos-ept/{caso_id}/contactos",
    {
      params: { path: { caso_id: casoId } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudo agregar el contacto EPT");
  return data;
}

/** GET /api/v1/casos-ept/{caso_id}/proceso
 *  Returns null on 404 (proceso no creado aún).
 */
export async function obtenerProceso(
  casoId: number,
): Promise<ProcesoEptRead | null> {
  const { data, error, response } = await api.GET(
    "/api/v1/casos-ept/{caso_id}/proceso",
    { params: { path: { caso_id: casoId } } },
  );
  if (error || !data) {
    if (response.status === 404) return null;
    throw new Error("No se pudo obtener el proceso EPT");
  }
  return data;
}

/** POST /api/v1/casos-ept/{caso_id}/proceso */
export async function crearProceso(
  casoId: number,
  body: ProcesoEptCreate,
): Promise<ProcesoEptRead> {
  const { data, error } = await api.POST(
    "/api/v1/casos-ept/{caso_id}/proceso",
    {
      params: { path: { caso_id: casoId } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudo crear el proceso EPT");
  return data;
}

/** PATCH /api/v1/casos-ept/{caso_id}/proceso */
export async function actualizarProceso(
  casoId: number,
  body: ProcesoEptUpdate,
): Promise<ProcesoEptRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/casos-ept/{caso_id}/proceso",
    {
      params: { path: { caso_id: casoId } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudo actualizar el proceso EPT");
  return data;
}

/** GET /api/v1/casos-ept/{caso_id}/plazos
 *  Returns null on 404 (plazos no creados aún).
 */
export async function obtenerPlazos(
  casoId: number,
): Promise<PlazoEptRead | null> {
  const { data, error, response } = await api.GET(
    "/api/v1/casos-ept/{caso_id}/plazos",
    { params: { path: { caso_id: casoId } } },
  );
  if (error || !data) {
    if (response.status === 404) return null;
    throw new Error("No se pudieron obtener los plazos EPT");
  }
  return data;
}

/** POST /api/v1/casos-ept/{caso_id}/plazos */
export async function crearPlazos(
  casoId: number,
  body: PlazoEptCreate,
): Promise<PlazoEptRead> {
  const { data, error } = await api.POST(
    "/api/v1/casos-ept/{caso_id}/plazos",
    {
      params: { path: { caso_id: casoId } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudieron crear los plazos EPT");
  return data;
}

/** PATCH /api/v1/casos-ept/{caso_id}/plazos */
export async function actualizarPlazos(
  casoId: number,
  body: PlazoEptUpdate,
): Promise<PlazoEptRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/casos-ept/{caso_id}/plazos",
    {
      params: { path: { caso_id: casoId } },
      body,
    },
  );
  if (error || !data)
    throw new Error("No se pudieron actualizar los plazos EPT");
  return data;
}
