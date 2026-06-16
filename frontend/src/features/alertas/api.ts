import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// The generated type uses the fully-qualified name to disambiguate from
// the farmacos AlertaRead (app__schemas__farmacos__AlertaRead).
export type AlertaRead = components["schemas"]["app__schemas__alertas__AlertaRead"];
export type AlertaUpdate = components["schemas"]["AlertaUpdate"];
export type EstadoAlerta = components["schemas"]["EstadoAlerta"];
export type TareaItemRead = components["schemas"]["TareaItemRead"];

export async function listarAlertas(): Promise<AlertaRead[]> {
  const { data, error } = await api.GET("/api/v1/alertas", {});
  if (error) throw new Error("Error al cargar alertas");
  return data ?? [];
}

export async function listarTareas(): Promise<TareaItemRead[]> {
  const { data, error } = await api.GET("/api/v1/tareas", {});
  if (error) throw new Error("Error al cargar tareas");
  return data ?? [];
}

export async function actualizarAlerta(
  id: number,
  estado: EstadoAlerta,
): Promise<AlertaRead> {
  const body: AlertaUpdate = { estado };
  const { data, error } = await api.PATCH("/api/v1/alertas/{alerta_id}", {
    params: { path: { alerta_id: id } },
    body,
  });
  if (error || !data) throw new Error("No se pudo actualizar la alerta");
  return data;
}
