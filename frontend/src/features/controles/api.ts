import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type ControlMedicoRead = components["schemas"]["ControlMedicoRead"];
export type ControlMedicoCreate = components["schemas"]["ControlMedicoCreate"];
export type ProximoControlUpdate = components["schemas"]["ProximoControlUpdate"];
export type LicenciaUpdate = components["schemas"]["LicenciaUpdate"];

export type EstadoReca = components["schemas"]["EstadoReca"];
export type TipoLicencia =
  components["schemas"]["app__domain__enums_controles__TipoLicencia"];
export type TipoReposo =
  components["schemas"]["app__domain__enums_controles__TipoReposo"];

// ── API functions ────────────────────────────────────────────────────────────

/** POST /api/v1/controles-medicos */
export async function crearControl(
  body: ControlMedicoCreate,
): Promise<ControlMedicoRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/controles-medicos",
    { body },
  );
  if (error || !data) {
    if (response.status === 409)
      throw new Error("Ya existe un control médico para esta fecha e ingreso.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el control médico");
  }
  return data;
}

/** GET /api/v1/controles-medicos/por-ingreso/{ingreso_id} */
export async function controlesPorIngreso(
  ingresoId: number,
): Promise<ControlMedicoRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/controles-medicos/por-ingreso/{ingreso_id}",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error) throw new Error("No se pudieron cargar los controles médicos");
  return data ?? [];
}

/** GET /api/v1/controles-medicos/{control_id} */
export async function obtenerControl(
  controlId: number,
): Promise<ControlMedicoRead> {
  const { data, error } = await api.GET(
    "/api/v1/controles-medicos/{control_id}",
    { params: { path: { control_id: controlId } } },
  );
  if (error || !data)
    throw new Error("No se pudo obtener el control médico");
  return data;
}

/** PATCH /api/v1/controles-medicos/{control_id}/proximo-control */
export async function actualizarProximoControl(
  controlId: number,
  body: ProximoControlUpdate,
): Promise<ControlMedicoRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/controles-medicos/{control_id}/proximo-control",
    {
      params: { path: { control_id: controlId } },
      body,
    },
  );
  if (error || !data)
    throw new Error("No se pudo actualizar el próximo control");
  return data;
}

/** PATCH /api/v1/controles-medicos/{control_id}/licencia */
export async function actualizarLicencia(
  controlId: number,
  body: LicenciaUpdate,
): Promise<ControlMedicoRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/controles-medicos/{control_id}/licencia",
    {
      params: { path: { control_id: controlId } },
      body,
    },
  );
  if (error || !data)
    throw new Error("No se pudo actualizar la licencia del control");
  return data;
}
