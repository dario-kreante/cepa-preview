import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type CasoReintegroCreate = components["schemas"]["CasoReintegroCreate"];
export type CasoReintegroRead = components["schemas"]["CasoReintegroRead"];
export type CasoReintegroUpdate = components["schemas"]["CasoReintegroUpdate"];

export type RecaCreate = components["schemas"]["RecaCreate"];
export type RecaRead = components["schemas"]["RecaRead"];
export type RecaUpdate = components["schemas"]["RecaUpdate"];

export type CierreReintegroUpdate =
  components["schemas"]["CierreReintegroUpdate"];

export type EstadoReintegro = components["schemas"]["EstadoReintegro"];
export type TipoReca = components["schemas"]["TipoReca"];
export type TipoAlta = components["schemas"]["TipoAlta"];
export type TipoDerivacion = components["schemas"]["TipoDerivacion"];

// ── CEPA-040: Caso de reintegro ──────────────────────────────────────────────

/** POST /api/v1/reintegros */
export async function crearCaso(
  body: CasoReintegroCreate,
): Promise<CasoReintegroRead> {
  const { data, error, response } = await api.POST("/api/v1/reintegros", {
    body,
  });
  if (error || !data) {
    if (response.status === 409)
      throw new Error("Ya existe un caso de reintegro para este ingreso.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el caso de reintegro");
  }
  return data;
}

/** GET /api/v1/reintegros?ingreso_id= */
export async function listarCasos(
  ingresoId?: number,
): Promise<CasoReintegroRead[]> {
  const { data, error } = await api.GET("/api/v1/reintegros", {
    params: { query: ingresoId != null ? { ingreso_id: ingresoId } : {} },
  });
  if (error || !data) throw new Error("No se pudieron listar los casos de reintegro");
  return data;
}

/** GET /api/v1/reintegros/{caso_id} */
export async function obtenerCaso(casoId: number): Promise<CasoReintegroRead> {
  const { data, error } = await api.GET("/api/v1/reintegros/{caso_id}", {
    params: { path: { caso_id: casoId } },
  });
  if (error || !data) throw new Error("No se pudo obtener el caso de reintegro");
  return data;
}

/** PATCH /api/v1/reintegros/{caso_id} */
export async function actualizarCaso(
  casoId: number,
  body: CasoReintegroUpdate,
): Promise<CasoReintegroRead> {
  const { data, error } = await api.PATCH("/api/v1/reintegros/{caso_id}", {
    params: { path: { caso_id: casoId } },
    body,
  });
  if (error || !data)
    throw new Error("No se pudo actualizar el caso de reintegro");
  return data;
}

// ── CEPA-041: RECA y medidas correctivas ─────────────────────────────────────

/** GET /api/v1/reintegros/{caso_id}/reca — returns null on 404 (sin RECA aún). */
export async function obtenerReca(casoId: number): Promise<RecaRead | null> {
  const { data, error, response } = await api.GET(
    "/api/v1/reintegros/{caso_id}/reca",
    { params: { path: { caso_id: casoId } } },
  );
  if (error || !data) {
    if (response.status === 404) return null;
    throw new Error("No se pudo obtener la RECA");
  }
  return data;
}

/** POST /api/v1/reintegros/{caso_id}/reca */
export async function crearReca(
  casoId: number,
  body: RecaCreate,
): Promise<RecaRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/reintegros/{caso_id}/reca",
    { params: { path: { caso_id: casoId } }, body },
  );
  if (error || !data) {
    if (response.status === 409)
      throw new Error("Este caso ya tiene una RECA registrada.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa fechas y campos de la RECA.");
    throw new Error("No se pudo registrar la RECA");
  }
  return data;
}

/** PATCH /api/v1/reintegros/{caso_id}/reca */
export async function actualizarReca(
  casoId: number,
  body: RecaUpdate,
): Promise<RecaRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/reintegros/{caso_id}/reca",
    { params: { path: { caso_id: casoId } }, body },
  );
  if (error || !data) throw new Error("No se pudo actualizar la RECA");
  return data;
}

// ── CEPA-042: Cierre / reintegro ──────────────────────────────────────────────

/** PATCH /api/v1/reintegros/{caso_id}/cierre */
export async function registrarCierre(
  casoId: number,
  body: CierreReintegroUpdate,
): Promise<CasoReintegroRead> {
  const { data, error, response } = await api.PATCH(
    "/api/v1/reintegros/{caso_id}/cierre",
    { params: { path: { caso_id: casoId } }, body },
  );
  if (error || !data) {
    if (response.status === 422)
      throw new Error(
        "Datos de cierre inválidos (revisa coherencia de fechas y altas).",
      );
    throw new Error("No se pudo registrar el cierre del reintegro");
  }
  return data;
}
