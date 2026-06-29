import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type DisponibilidadProfCreate =
  components["schemas"]["DisponibilidadProfCreate"];
export type DisponibilidadProfRead =
  components["schemas"]["DisponibilidadProfRead"];
export type GenerarPropuestaRequest =
  components["schemas"]["GenerarPropuestaRequest"];
export type PropuestaAgendaRead =
  components["schemas"]["PropuestaAgendaRead"];
export type CitaPropuestaRead = components["schemas"]["CitaPropuestaRead"];
export type TipoPropuesta = components["schemas"]["TipoPropuesta"];
export type PrioridadCita = components["schemas"]["PrioridadCita"];

// ── Disponibilidad ────────────────────────────────────────────────────────────

/** GET /api/v1/disponibilidad-profesional/{profesional_id} */
export async function listarDisponibilidad(
  profesionalId: number,
): Promise<DisponibilidadProfRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/disponibilidad-profesional/{profesional_id}",
    { params: { path: { profesional_id: profesionalId } } },
  );
  if (error || !data) throw new Error("No se pudo cargar la disponibilidad");
  return data;
}

/** POST /api/v1/disponibilidad-profesional */
export async function crearDisponibilidad(
  body: DisponibilidadProfCreate,
): Promise<DisponibilidadProfRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/disponibilidad-profesional",
    { body },
  );
  if (error || !data) {
    if (response.status === 422)
      throw new Error("Datos inválidos (día 1–5 y cupo ≥ 1).");
    throw new Error("No se pudo registrar la disponibilidad");
  }
  return data;
}

// ── Propuestas ──────────────────────────────────────────────────────────────────

/** POST /api/v1/propuestas-agenda */
export async function generarPropuesta(
  body: GenerarPropuestaRequest,
): Promise<PropuestaAgendaRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/propuestas-agenda",
    { body },
  );
  if (error || !data) {
    if (response.status === 422)
      throw new Error("La fecha de inicio debe ser un día hábil (lun–vie).");
    throw new Error("No se pudo generar la propuesta");
  }
  return data;
}

/** GET /api/v1/propuestas-agenda?profesional_id= */
export async function listarPropuestas(
  profesionalId?: number,
): Promise<PropuestaAgendaRead[]> {
  const { data, error } = await api.GET("/api/v1/propuestas-agenda", {
    params: {
      query: profesionalId != null ? { profesional_id: profesionalId } : {},
    },
  });
  if (error || !data) throw new Error("No se pudieron listar las propuestas");
  return data;
}

/** GET /api/v1/propuestas-agenda/{propuesta_id}/citas */
export async function listarCitas(
  propuestaId: number,
): Promise<CitaPropuestaRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/propuestas-agenda/{propuesta_id}/citas",
    { params: { path: { propuesta_id: propuestaId } } },
  );
  if (error || !data) throw new Error("No se pudieron cargar las citas");
  return data;
}

/** POST /api/v1/propuestas-agenda/{propuesta_id}/confirmar */
export async function confirmarCitas(
  propuestaId: number,
  citaIds: number[],
): Promise<CitaPropuestaRead[]> {
  const { data, error, response } = await api.POST(
    "/api/v1/propuestas-agenda/{propuesta_id}/confirmar",
    {
      params: { path: { propuesta_id: propuestaId } },
      body: { cita_ids: citaIds },
    },
  );
  if (error || !data) {
    if (response.status === 422)
      throw new Error("Selecciona al menos una cita para confirmar.");
    throw new Error("No se pudieron confirmar las citas");
  }
  return data;
}
