import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  crearDisponibilidad,
  listarDisponibilidad,
  listarGestiones,
  listarPacientesPorCitar,
  quitarDisponibilidad,
  registrarGestion,
  type DisponibilidadProfCreate,
  type GestionCreate,
} from "./api";

export type RangoAgenda = "semana" | "dos_semanas" | "mes";

function iso(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${dia}`;
}

/**
 * Fechas `desde`/`hasta` del rango. "dos_semanas" devuelve `{}` para que el backend
 * use su valor por defecto. "semana" va de hoy al viernes de esta semana (si hoy es
 * fin de semana, al viernes siguiente); "mes", hasta el último día del mes.
 */
export function rangoFechas(
  rango: RangoAgenda,
  hoy: Date = new Date(),
): { desde?: string; hasta?: string } {
  if (rango === "dos_semanas") return {};
  const desde = iso(hoy);
  if (rango === "mes") {
    return { desde, hasta: iso(new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0)) };
  }
  const dow = (hoy.getDay() + 6) % 7; // lunes = 0
  const viernes = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - dow + 4);
  if (viernes < new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())) {
    viernes.setDate(viernes.getDate() + 7);
  }
  return { desde, hasta: iso(viernes) };
}

// ── Query hooks ──────────────────────────────────────────────────────────────

export function usePacientesPorCitar(
  profesionalId: number | null,
  rango: RangoAgenda,
) {
  return useQuery({
    queryKey: ["agenda", "por-citar", profesionalId, rango],
    queryFn: () => {
      const { desde, hasta } = rangoFechas(rango);
      return listarPacientesPorCitar(profesionalId as number, desde, hasta);
    },
    enabled: profesionalId != null,
  });
}

export function useGestiones(pacienteId: number | null) {
  return useQuery({
    queryKey: ["agenda", "gestiones", pacienteId],
    queryFn: () => listarGestiones(pacienteId as number),
    enabled: pacienteId != null,
  });
}

export function useDisponibilidad(profesionalId: number | null) {
  return useQuery({
    queryKey: ["agenda", "disponibilidad", profesionalId],
    queryFn: () => listarDisponibilidad(profesionalId as number),
    enabled: !!profesionalId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

export function useRegistrarGestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      pacienteId,
      body,
    }: {
      pacienteId: number;
      body: GestionCreate;
    }) => registrarGestion(pacienteId, body),
    onSuccess: (_d, { pacienteId }) => {
      qc.invalidateQueries({ queryKey: ["agenda", "por-citar"] });
      qc.invalidateQueries({ queryKey: ["agenda", "gestiones", pacienteId] });
    },
  });
}

// La disponibilidad cambia los cupos: se refresca también la lista por citar.
function invalidarDisponibilidad(
  qc: ReturnType<typeof useQueryClient>,
  profesionalId?: number,
) {
  qc.invalidateQueries({
    queryKey:
      profesionalId != null
        ? ["agenda", "disponibilidad", profesionalId]
        : ["agenda", "disponibilidad"],
  });
  qc.invalidateQueries({ queryKey: ["agenda", "por-citar"] });
}

export function useCrearDisponibilidad() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DisponibilidadProfCreate) => crearDisponibilidad(body),
    onSuccess: (_d, body) => invalidarDisponibilidad(qc, body.profesional_id),
  });
}

export function useQuitarDisponibilidad() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (disponibilidadId: number) => quitarDisponibilidad(disponibilidadId),
    onSuccess: () => invalidarDisponibilidad(qc),
  });
}
