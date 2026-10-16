import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type DisponibilidadProfCreate =
  components["schemas"]["DisponibilidadProfCreate"];
export type DisponibilidadProfRead =
  components["schemas"]["DisponibilidadProfRead"];
export type PrioridadCita = components["schemas"]["PrioridadCita"];
export type ResultadoGestion = components["schemas"]["ResultadoGestion"];
export type GestionCreate = components["schemas"]["GestionCreate"];
export type GestionRead = components["schemas"]["GestionRead"];
export type CargaDiaRead = components["schemas"]["CargaDiaRead"];
export type PacientePorCitarRead =
  components["schemas"]["PacientePorCitarRead"];
export type PacientesPorCitarRead =
  components["schemas"]["PacientesPorCitarRead"];

export const RESULTADO_LABELS: Record<ResultadoGestion, string> = {
  agendada_en_salutem: "Agendada en SALUTEM",
  no_contesta: "No contesta",
  rechaza: "Rechaza",
  otro: "Otro",
};

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

/** POST /api/v1/disponibilidad-profesional (reemplaza el día si ya existía) */
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

/** DELETE /api/v1/disponibilidad-profesional/{disponibilidad_id} */
export async function quitarDisponibilidad(
  disponibilidadId: number,
): Promise<void> {
  const { error } = await api.DELETE(
    "/api/v1/disponibilidad-profesional/{disponibilidad_id}",
    { params: { path: { disponibilidad_id: disponibilidadId } } },
  );
  if (error) throw new Error("No se pudo quitar la disponibilidad");
}

// ── Pacientes por citar ─────────────────────────────────────────────────────────

/** GET /api/v1/pacientes-por-citar?profesional_id=&desde=&hasta= */
export async function listarPacientesPorCitar(
  profesionalId: number,
  desde?: string,
  hasta?: string,
): Promise<PacientesPorCitarRead> {
  const { data, error } = await api.GET("/api/v1/pacientes-por-citar", {
    params: {
      query: {
        profesional_id: profesionalId,
        ...(desde ? { desde } : {}),
        ...(hasta ? { hasta } : {}),
      },
    },
  });
  if (error || !data)
    throw new Error("No se pudo cargar la lista de pacientes por citar");
  return data;
}

// ── Gestiones de contacto ───────────────────────────────────────────────────────

/** POST /api/v1/pacientes-por-citar/{paciente_id}/gestiones */
export async function registrarGestion(
  pacienteId: number,
  body: GestionCreate,
): Promise<GestionRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/pacientes-por-citar/{paciente_id}/gestiones",
    { params: { path: { paciente_id: pacienteId } }, body },
  );
  if (error || !data) {
    if (response.status === 403)
      throw new Error("Tu perfil no puede registrar contactos.");
    throw new Error("No se pudo registrar el contacto");
  }
  return data;
}

/** GET /api/v1/pacientes-por-citar/{paciente_id}/gestiones */
export async function listarGestiones(
  pacienteId: number,
): Promise<GestionRead[]> {
  const { data, error } = await api.GET(
    "/api/v1/pacientes-por-citar/{paciente_id}/gestiones",
    { params: { path: { paciente_id: pacienteId } } },
  );
  if (error || !data)
    throw new Error("No se pudo cargar el historial de contacto");
  return data;
}
