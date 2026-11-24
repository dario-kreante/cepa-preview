import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarCaso,
  actualizarReca,
  crearCaso,
  crearReca,
  listarCasos,
  listarCasosActivosDePaciente,
  listarPacientesConCasosRepetidos,
  obtenerCaso,
  obtenerPanel,
  obtenerPrecarga,
  obtenerReca,
  registrarCierre,
  registrarRemisionIsl,
  registrarSolicitudReca,
  type CasoReintegroCreate,
  type CasoReintegroUpdate,
  type CierreReintegroUpdate,
  type RecaCreate,
  type RecaUpdate,
} from "./api";

/** Lista global: la cambian el alta, el cierre, la solicitud de RECA, la RECA y la remisión. */
const PANEL_KEY = ["reintegro", "panel"] as const;

// ── Query hooks ──────────────────────────────────────────────────────────────

export function useCasosPorIngreso(ingresoId: number | null) {
  return useQuery({
    queryKey: ["reintegro", "ingreso", ingresoId],
    queryFn: () => listarCasos(ingresoId ?? undefined),
    enabled: !!ingresoId,
  });
}

/** Casos activos del paciente (todos sus ingresos), para avisar de un caso repetido. */
export function useCasosActivosDePaciente(pacienteId: number | null) {
  return useQuery({
    queryKey: ["reintegro", "paciente", pacienteId, "activos"],
    queryFn: () => listarCasosActivosDePaciente(pacienteId as number),
    enabled: !!pacienteId,
  });
}

/** Pacientes con más de un caso activo (revisión de duplicados). */
export function usePacientesConCasosRepetidos(enabled = true) {
  return useQuery({
    queryKey: ["reintegro", "duplicados"],
    queryFn: listarPacientesConCasosRepetidos,
    enabled,
  });
}

/** Lista global de la pestaña (QA-010): casos activos y pendientes por registrar. */
export function usePanelReintegro(enabled = true) {
  return useQuery({ queryKey: PANEL_KEY, queryFn: obtenerPanel, enabled });
}

/** Precarga del alta (QA-010): ocupación y tipo de trabajador de un caso anterior o de SALUTEM. */
export function usePrecargaCaso(ingresoId: number | null) {
  return useQuery({
    queryKey: ["reintegro", "precarga", ingresoId],
    queryFn: () => obtenerPrecarga(ingresoId as number),
    enabled: !!ingresoId,
  });
}

export function useCaso(casoId: number) {
  return useQuery({
    queryKey: ["reintegro", casoId],
    queryFn: () => obtenerCaso(casoId),
    enabled: !!casoId,
  });
}

export function useReca(casoId: number) {
  return useQuery({
    queryKey: ["reintegro", casoId, "reca"],
    queryFn: () => obtenerReca(casoId),
    enabled: !!casoId,
  });
}

// ── Mutation hooks ───────────────────────────────────────────────────────────

/** Crea un caso de reintegro nuevo. */
export function useCrearCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CasoReintegroCreate) => crearCaso(body),
    onSuccess: (caso) => {
      qc.invalidateQueries({
        queryKey: ["reintegro", "ingreso", caso.ingreso_id],
      });
      qc.invalidateQueries({ queryKey: ["reintegro", "paciente"] });
      qc.invalidateQueries({ queryKey: ["reintegro", "duplicados"] });
      qc.invalidateQueries({ queryKey: PANEL_KEY });
    },
  });
}

export function useActualizarCaso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      casoId,
      body,
    }: {
      casoId: number;
      body: CasoReintegroUpdate;
    }) => actualizarCaso(casoId, body),
    onSuccess: (_data, { casoId }) => {
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] });
      qc.invalidateQueries({ queryKey: PANEL_KEY });
    },
  });
}

export function useCrearReca() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: RecaCreate }) =>
      crearReca(casoId, body),
    // Con la RECA el estado de la solicitud pasa a «recibida» y se resuelve la alerta
    // «RECA por solicitar»: se refresca el caso (prefijo ["reintegro", casoId]) y las alertas.
    onSuccess: (_data, { casoId }) => {
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] });
      qc.invalidateQueries({ queryKey: ["alertas"] });
      qc.invalidateQueries({ queryKey: PANEL_KEY });
    },
  });
}

export function useActualizarReca() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, body }: { casoId: number; body: RecaUpdate }) =>
      actualizarReca(casoId, body),
    onSuccess: (_data, { casoId }) =>
      qc.invalidateQueries({ queryKey: ["reintegro", casoId, "reca"] }),
  });
}

export function useRegistrarCierre() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      casoId,
      body,
    }: {
      casoId: number;
      body: CierreReintegroUpdate;
    }) => registrarCierre(casoId, body),
    onSuccess: (caso, { casoId }) => {
      // Pasar a reintegro total saca al caso de los activos: refresca aviso y duplicados.
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] });
      qc.invalidateQueries({ queryKey: ["reintegro", "ingreso", caso.ingreso_id] });
      qc.invalidateQueries({ queryKey: ["reintegro", "paciente"] });
      qc.invalidateQueries({ queryKey: ["reintegro", "duplicados"] });
      // El reintegro total resuelve la alerta «RECA por solicitar».
      qc.invalidateQueries({ queryKey: ["alertas"] });
      qc.invalidateQueries({ queryKey: PANEL_KEY });
    },
  });
}

/** Registra o corrige la fecha de solicitud de RECA; resuelve la alerta «RECA por solicitar». */
export function useRegistrarSolicitudReca() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, fecha }: { casoId: number; fecha: string }) =>
      registrarSolicitudReca(casoId, fecha),
    onSuccess: (caso, { casoId }) => {
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] });
      qc.invalidateQueries({ queryKey: ["reintegro", "ingreso", caso.ingreso_id] });
      qc.invalidateQueries({ queryKey: ["alertas"] });
      qc.invalidateQueries({ queryKey: PANEL_KEY });
    },
  });
}

/** Marca el caso «Remitido a ISL» (QA-010); resuelve la alerta «Pendiente de remitir a ISL». */
export function useRegistrarRemisionIsl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ casoId, fecha }: { casoId: number; fecha: string }) =>
      registrarRemisionIsl(casoId, fecha),
    onSuccess: (caso, { casoId }) => {
      qc.invalidateQueries({ queryKey: ["reintegro", casoId] });
      qc.invalidateQueries({ queryKey: ["reintegro", "ingreso", caso.ingreso_id] });
      qc.invalidateQueries({ queryKey: ["alertas"] });
      qc.invalidateQueries({ queryKey: PANEL_KEY });
    },
  });
}
