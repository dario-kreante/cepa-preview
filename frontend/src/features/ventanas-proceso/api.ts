import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type VentanaProcesoRead = components["schemas"]["VentanaProcesoRead"];
export type VentanaProcesoCreate =
  components["schemas"]["VentanaProcesoCreate"];

export const PROCESOS = [
  "licencias",
  "farmacos",
  "auditoria",
  "reintegro",
  "controles",
] as const;
export type Proceso = (typeof PROCESOS)[number];

export const PROCESO_LABELS: Record<Proceso, string> = {
  licencias: "Licencias",
  farmacos: "Fármacos",
  auditoria: "Auditoría",
  reintegro: "Reintegro",
  controles: "Controles",
};

/** GET /api/v1/ventanas-proceso */
export async function listarVentanas(): Promise<VentanaProcesoRead[]> {
  const { data, error } = await api.GET("/api/v1/ventanas-proceso", {
    params: { query: {} },
  });
  if (error || !data) throw new Error("No se pudieron cargar las ventanas");
  return data;
}

/** POST /api/v1/ventanas-proceso */
export async function crearVentana(
  body: VentanaProcesoCreate,
): Promise<VentanaProcesoRead> {
  const { data, error, response } = await api.POST("/api/v1/ventanas-proceso", {
    body,
  });
  if (error || !data) {
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa el proceso y las columnas.");
    throw new Error("No se pudo crear la ventana de proceso");
  }
  return data;
}
