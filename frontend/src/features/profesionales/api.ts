import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ProfesionalRead = components["schemas"]["ProfesionalRead"];
export type ProfesionalCreate = components["schemas"]["ProfesionalCreate"];
export type ProfesionalUpdate = components["schemas"]["ProfesionalUpdate"];

/** GET /api/v1/profesionales?solo_activos= */
export async function listarProfesionales(
  soloActivos = false,
): Promise<ProfesionalRead[]> {
  const { data, error } = await api.GET("/api/v1/profesionales", {
    params: { query: { solo_activos: soloActivos } },
  });
  if (error || !data) throw new Error("No se pudieron cargar los profesionales");
  return data;
}

function mensajeEscritura(status: number, porDefecto: string): string {
  if (status === 409) return "Ya existe un profesional con ese nombre.";
  if (status === 422) return "Revisa los datos: el nombre es obligatorio.";
  if (status === 403) return "Tu perfil no puede modificar el catálogo de profesionales.";
  return porDefecto;
}

/** POST /api/v1/profesionales */
export async function crearProfesional(
  body: ProfesionalCreate,
): Promise<ProfesionalRead> {
  const { data, error, response } = await api.POST("/api/v1/profesionales", {
    body,
  });
  if (error || !data)
    throw new Error(mensajeEscritura(response.status, "No se pudo crear el profesional"));
  return data;
}

/** PATCH /api/v1/profesionales/{profesional_id} */
export async function actualizarProfesional(
  id: number,
  body: ProfesionalUpdate,
): Promise<ProfesionalRead> {
  const { data, error, response } = await api.PATCH(
    "/api/v1/profesionales/{profesional_id}",
    { params: { path: { profesional_id: id } }, body },
  );
  if (error || !data)
    throw new Error(
      mensajeEscritura(response.status, "No se pudo actualizar el profesional"),
    );
  return data;
}

/** POST /api/v1/profesionales/importar-salutem */
export async function importarDesdeSalutem(): Promise<{ creados: number }> {
  const { data, response } = await api.POST(
    "/api/v1/profesionales/importar-salutem",
  );
  if (!data)
    throw new Error(
      mensajeEscritura(response.status, "No se pudo importar desde SALUTEM"),
    );
  return data;
}
