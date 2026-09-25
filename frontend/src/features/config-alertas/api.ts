import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ConfigAlertaRead = components["schemas"]["ConfigAlertaRead"];
export type ConfigAlertaItem = components["schemas"]["ConfigAlertaItem"];
export type FestivoRead = components["schemas"]["FestivoRead"];
export type FestivoCreate = components["schemas"]["FestivoCreate"];

export const TIPO_LABELS: Record<string, string> = {
  vencimiento_licencia: "Vencimiento de licencia",
  plazo_ept: "Plazo informe EPT",
  plazo_isl: "Plazo portal ISL",
  receta_por_renovar: "Receta por renovar",
  oda_por_vencer: "ODA por vencer",
  control_medico: "Control médico",
  consentimiento_pendiente: "Consentimiento pendiente",
};

/** GET /api/v1/config-alertas */
export async function listarConfig(): Promise<ConfigAlertaRead[]> {
  const { data, error } = await api.GET("/api/v1/config-alertas");
  if (error || !data) throw new Error("No se pudo cargar la configuración de alertas");
  return data;
}

/** PUT /api/v1/config-alertas */
export async function guardarConfig(body: ConfigAlertaItem[]): Promise<ConfigAlertaRead[]> {
  const { data, error, response } = await api.PUT("/api/v1/config-alertas", { body });
  if (error || !data) {
    if (response.status === 422) throw new Error("Datos inválidos: los días van de 0 a 365.");
    throw new Error("No se pudo guardar la configuración");
  }
  return data;
}

/** GET /api/v1/config-alertas/festivos */
export async function listarFestivos(): Promise<FestivoRead[]> {
  const { data, error } = await api.GET("/api/v1/config-alertas/festivos");
  if (error || !data) throw new Error("No se pudieron cargar los festivos");
  return data;
}

/** POST /api/v1/config-alertas/festivos */
export async function crearFestivo(body: FestivoCreate): Promise<FestivoRead> {
  const { data, error, response } = await api.POST("/api/v1/config-alertas/festivos", { body });
  if (error || !data) {
    if (response.status === 409) throw new Error("Ya existe un festivo en esa fecha.");
    if (response.status === 422) throw new Error("Indica una fecha y una descripción.");
    throw new Error("No se pudo agregar el festivo");
  }
  return data;
}

/** DELETE /api/v1/config-alertas/festivos/{festivo_id} */
export async function eliminarFestivo(id: number): Promise<void> {
  const { response } = await api.DELETE("/api/v1/config-alertas/festivos/{festivo_id}", {
    params: { path: { festivo_id: id } },
  });
  if (!response.ok) throw new Error("No se pudo eliminar el festivo");
}
