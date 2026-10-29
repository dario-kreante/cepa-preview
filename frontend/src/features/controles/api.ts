import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// ── Type exports ────────────────────────────────────────────────────────────

export type ControlMedicoRead = components["schemas"]["ControlMedicoRead"];
export type ControlMedicoCreate = components["schemas"]["ControlMedicoCreate"];
export type ProximoControlUpdate = components["schemas"]["ProximoControlUpdate"];
export type LicenciaUpdate = components["schemas"]["LicenciaUpdate"];
export type EvaluacionUpdate = components["schemas"]["EvaluacionUpdate"];
export type ArchivoControlRead = components["schemas"]["ArchivoControlRead"];
export type AtencionSalutemRead = components["schemas"]["AtencionSalutemRead"];

// Calificación RECA: mismo catálogo que la RECA del reintegro (D20).
export type EstadoReca = components["schemas"]["TipoReca"];
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

/** PATCH /api/v1/controles-medicos/{control_id}/evaluacion */
export async function actualizarEvaluacion(
  controlId: number,
  body: EvaluacionUpdate,
): Promise<ControlMedicoRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/controles-medicos/{control_id}/evaluacion",
    {
      params: { path: { control_id: controlId } },
      body,
    },
  );
  if (error || !data)
    throw new Error("No se pudo actualizar la evaluación del control");
  return data;
}

/** GET /api/v1/controles-medicos/{control_id}/archivos */
export async function archivosDeControl(controlId: number): Promise<ArchivoControlRead[]> {
  const { data, error } = await api.GET("/api/v1/controles-medicos/{control_id}/archivos", {
    params: { path: { control_id: controlId } },
  });
  if (error || !data) throw new Error("No se pudieron cargar los documentos de SALUTEM");
  return data;
}

/** El navegador no dejó abrir la pestaña nueva (bloqueador de ventanas emergentes). */
/** GET /api/v1/salutem/atenciones/{cita_id} — atención médica que no es control. */
export async function obtenerAtencionSalutem(citaId: number): Promise<AtencionSalutemRead> {
  const { data, error } = await api.GET("/api/v1/salutem/atenciones/{cita_id}", {
    params: { path: { cita_id: citaId } },
  });
  if (error || !data) throw new Error("No se encontró la atención");
  return data;
}

/** GET /api/v1/salutem/atenciones/{cita_id}/archivos */
export async function archivosDeAtencion(citaId: number): Promise<ArchivoControlRead[]> {
  const { data, error } = await api.GET("/api/v1/salutem/atenciones/{cita_id}/archivos", {
    params: { path: { cita_id: citaId } },
  });
  if (error || !data) throw new Error("No se pudieron cargar los documentos de SALUTEM");
  return data;
}

export type DocumentoSalutemRead = components["schemas"]["DocumentoSalutemRead"];
/** Relación DEDUCIDA de la atención: SALUTEM no informa la carpeta del archivo. */
export type RelacionDocumento = "licencia" | "receta";

/** GET /api/v1/pacientes/{paciente_id}/documentos-salutem */
export async function documentosDePaciente(
  pacienteId: number,
  relacion?: RelacionDocumento,
): Promise<DocumentoSalutemRead[]> {
  const { data, error } = await api.GET("/api/v1/pacientes/{paciente_id}/documentos-salutem", {
    params: { path: { paciente_id: pacienteId }, query: relacion ? { relacion } : {} },
  });
  if (error || !data) throw new Error("No se pudieron cargar los documentos de SALUTEM");
  return data;
}

export function abrirDocumentoDePaciente(pacienteId: number, archivoId: number, nombre: string) {
  return abrirArchivo(
    () =>
      api.GET("/api/v1/pacientes/{paciente_id}/documentos-salutem/{archivo_id}/contenido", {
        params: { path: { paciente_id: pacienteId, archivo_id: archivoId } },
        parseAs: "blob",
      }),
    nombre,
  );
}

export class PestanaBloqueadaError extends Error {
  constructor() {
    super("El navegador bloqueó la pestaña nueva.");
    this.name = "PestanaBloqueadaError";
  }
}

// Solo estos tipos se muestran en una pestaña; el resto (p. ej. HTML o SVG) se descarga,
// porque un documento activo abierto como blob correría con el origen de la aplicación.
const TIPOS_ABRIBLES = new Set(["application/pdf", "image/jpeg", "image/png", "image/gif", "image/heic"]);
const REVOCAR_URL_MS = 5 * 60_000;

/**
 * Abre un documento de SALUTEM. Se pide con la sesión (Bearer) y se entrega como blob:
 * una URL directa del backend no llevaría el token.
 *
 * La pestaña se abre de forma síncrona en el clic y recién después se pide el contenido:
 * un `window.open` tras un `await` lo bloquean los navegadores sin avisar.
 */
export function abrirArchivoDeControl(controlId: number, archivoId: number, nombre: string) {
  return abrirArchivo(
    () =>
      api.GET("/api/v1/controles-medicos/{control_id}/archivos/{archivo_id}/contenido", {
        params: { path: { control_id: controlId, archivo_id: archivoId } },
        parseAs: "blob",
      }),
    nombre,
  );
}

export function abrirArchivoDeAtencion(citaId: number, archivoId: number, nombre: string) {
  return abrirArchivo(
    () =>
      api.GET("/api/v1/salutem/atenciones/{cita_id}/archivos/{archivo_id}/contenido", {
        params: { path: { cita_id: citaId, archivo_id: archivoId } },
        parseAs: "blob",
      }),
    nombre,
  );
}

async function abrirArchivo(
  pedir: () => Promise<{ data?: unknown; error?: unknown }>,
  nombre: string,
): Promise<void> {
  const pestana = window.open("", "_blank");
  if (!pestana) throw new PestanaBloqueadaError();
  try {
    pestana.opener = null;
    pestana.document.title = "Cargando documento…";
    pestana.document.body.textContent = "Cargando documento…";
  } catch {
    // La pestaña es solo un contenedor: el texto de espera es cosmético.
  }
  try {
    const { data, error } = await pedir();
    if (error || !data) throw new Error("No se pudo abrir el documento");
    const blob = data as Blob;
    const tipo = blob.type.split(";")[0].trim().toLowerCase();
    if (TIPOS_ABRIBLES.has(tipo)) {
      const url = URL.createObjectURL(blob);
      pestana.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), REVOCAR_URL_MS);
    } else {
      descargar(new Blob([blob], { type: "application/octet-stream" }), nombre);
      pestana.close();
    }
  } catch (e) {
    pestana.close();
    throw e;
  }
}

function descargar(blob: Blob, nombre: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), REVOCAR_URL_MS);
}
