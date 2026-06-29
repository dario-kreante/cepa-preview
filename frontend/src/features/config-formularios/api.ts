import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type FormVersionRead = components["schemas"]["FormVersionRead"];
export type FieldDefOut = components["schemas"]["FieldDefOut"];
export type FieldDefIn = components["schemas"]["FieldDefIn"];
export type FormVersionCreate = components["schemas"]["FormVersionCreate"];
export type PublishResult = components["schemas"]["PublishResult"];

export const FIELD_TYPES = [
  "text",
  "number",
  "date",
  "select",
  "boolean",
] as const;
export type FieldType = (typeof FIELD_TYPES)[number];

export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  text: "Texto",
  number: "Número",
  date: "Fecha",
  select: "Selección",
  boolean: "Sí/No",
};

/** GET /api/v1/form-definitions/{form_key}/published — null si no hay publicada (404). */
export async function obtenerPublicada(
  formKey: string,
): Promise<FormVersionRead | null> {
  const { data, error, response } = await api.GET(
    "/api/v1/form-definitions/{form_key}/published",
    { params: { path: { form_key: formKey } } },
  );
  if (error || !data) {
    if (response.status === 404) return null;
    throw new Error("No se pudo cargar el formulario publicado");
  }
  return data;
}

/** POST /api/v1/form-definitions/{form_key}/draft */
export async function crearBorrador(
  formKey: string,
  fields: FieldDefIn[],
): Promise<FormVersionRead> {
  const { data, error, response } = await api.POST(
    "/api/v1/form-definitions/{form_key}/draft",
    { params: { path: { form_key: formKey } }, body: { fields } },
  );
  if (error || !data) {
    if (response.status === 422)
      throw new Error("Datos inválidos en la definición de campos.");
    throw new Error("No se pudo guardar el borrador");
  }
  return data;
}

/**
 * POST /api/v1/form-definitions/{form_key}/publish/{version_id}
 * Devuelve el PublishResult. Si la validación falla, el backend responde 422
 * con `{ success:false, errors:[...] }`: lo devolvemos igual (no lanzamos) para
 * que la UI muestre los errores de parametrización.
 */
export async function publicar(
  formKey: string,
  versionId: number,
): Promise<PublishResult> {
  const { data, error } = await api.POST(
    "/api/v1/form-definitions/{form_key}/publish/{version_id}",
    { params: { path: { form_key: formKey, version_id: versionId } } },
  );
  // En 422 openapi-fetch deja el cuerpo en `error` (mismo shape que PublishResult).
  const body = (data ?? error) as PublishResult | undefined;
  if (!body) throw new Error("No se pudo publicar la versión");
  return body;
}
