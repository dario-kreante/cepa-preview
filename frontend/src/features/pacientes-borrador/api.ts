import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type PacientePendienteRead = components["schemas"]["PacientePendienteRead"];
export type PacienteRead = components["schemas"]["PacienteRead"];

/** GET /api/v1/pacientes/pendientes-folio (más antiguos primero) */
export async function listarPendientesFolio(): Promise<PacientePendienteRead[]> {
  const { data, error } = await api.GET("/api/v1/pacientes/pendientes-folio");
  if (error) throw new Error("No se pudieron cargar los pacientes pendientes de folio");
  return data ?? [];
}

/** POST /api/v1/pacientes/{paciente_id}/descartar */
export async function descartarBorrador(
  id: number,
  motivo: string,
): Promise<PacienteRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/pacientes/{paciente_id}/descartar",
    { params: { path: { paciente_id: id } }, body: { motivo } },
  );
  if (error || !data) {
    if (response.status === 409)
      throw new Error("El paciente ya no está pendiente de folio.");
    if (response.status === 422)
      throw new Error("El motivo debe tener entre 1 y 300 caracteres.");
    throw new Error("No se pudo descartar el paciente");
  }
  return data;
}
