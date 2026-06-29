import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type UsuarioRead = components["schemas"]["UsuarioRead"];
export type UsuarioCreate = components["schemas"]["UsuarioCreate"];
export type UsuarioUpdate = components["schemas"]["UsuarioUpdate"];
export type RolUsuario = UsuarioCreate["rol"];

/** GET /api/v1/usuarios */
export async function listarUsuarios(): Promise<UsuarioRead[]> {
  const { data, error, response } = await api.GET("/api/v1/usuarios", {});
  if (error || !data) {
    // En este path sin parámetros openapi-fetch tipa `response` como never;
    // en runtime es un Response real, por eso el cast para leer el status.
    if ((response as Response).status === 403)
      throw new Error("Solo Coordinación puede gestionar usuarios.");
    throw new Error("No se pudieron cargar los usuarios");
  }
  return data;
}

/** POST /api/v1/usuarios */
export async function crearUsuario(body: UsuarioCreate): Promise<UsuarioRead> {
  const { data, error, response } = await api.POST("/api/v1/usuarios", { body });
  if (error || !data) {
    if (response.status === 409)
      throw new Error("El nombre de usuario ya existe.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear el usuario");
  }
  return data;
}

/** PUT /api/v1/usuarios/{usuario_id} */
export async function actualizarUsuario(
  usuarioId: number,
  body: UsuarioUpdate,
): Promise<UsuarioRead> {
  const { data, error } = await api.PUT("/api/v1/usuarios/{usuario_id}", {
    params: { path: { usuario_id: usuarioId } },
    body,
  });
  if (error || !data) throw new Error("No se pudo actualizar el usuario");
  return data;
}

/** PATCH /api/v1/usuarios/{usuario_id}/desactivar */
export async function desactivarUsuario(
  usuarioId: number,
): Promise<UsuarioRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/usuarios/{usuario_id}/desactivar",
    { params: { path: { usuario_id: usuarioId } } },
  );
  if (error || !data) throw new Error("No se pudo desactivar el usuario");
  return data;
}

/** PATCH /api/v1/usuarios/{usuario_id}/activar */
export async function activarUsuario(usuarioId: number): Promise<UsuarioRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/usuarios/{usuario_id}/activar",
    { params: { path: { usuario_id: usuarioId } } },
  );
  if (error || !data) throw new Error("No se pudo activar el usuario");
  return data;
}
