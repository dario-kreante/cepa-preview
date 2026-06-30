import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

export type ExtractedFieldOut = components["schemas"]["ExtractedFieldOut"];
export type PdfExtractResult = components["schemas"]["PdfExtractResult"];

export interface ConfirmOk {
  acknowledged: boolean;
  form_key: string;
  received_fields: number;
}

/**
 * POST /api/v1/pdf-extract/upload (multipart) — sube un PDF y devuelve los
 * campos extraídos. Degrada con gracia: el backend responde 200 con
 * success=false y error_message cuando la extracción falla.
 */
export async function uploadPdf(file: File): Promise<PdfExtractResult> {
  const fd = new FormData();
  fd.append("file", file);
  const { data, error } = await api.POST("/api/v1/pdf-extract/upload", {
    body: fd as never,
    bodySerializer: (b) => b as unknown as FormData,
  });
  if (error || !data) throw new Error("No se pudo procesar el PDF");
  return data;
}

/**
 * POST /api/v1/pdf-extract/confirm — confirma los campos editados contra el
 * formulario publicado `formKey`. En 422 el backend devuelve
 * `detail: { missing_required?, out_of_domain? }`; lo traducimos a un Error
 * con mensaje legible.
 */
export async function confirmExtraction(
  formKey: string,
  fields: ExtractedFieldOut[],
): Promise<ConfirmOk> {
  const { data, error, response } = await api.POST(
    "/api/v1/pdf-extract/confirm",
    { body: { form_key: formKey, fields } },
  );
  if (error || !data) {
    if (response.status === 404)
      throw new Error(`No hay un formulario publicado con la clave «${formKey}».`);
    if (response.status === 422) {
      const detail = (error as { detail?: { missing_required?: string[]; out_of_domain?: string[] } })
        ?.detail;
      const parts: string[] = [];
      if (detail?.missing_required?.length)
        parts.push(`Faltan campos requeridos: ${detail.missing_required.join(", ")}`);
      if (detail?.out_of_domain?.length)
        parts.push(`Valores fuera de dominio: ${detail.out_of_domain.join(", ")}`);
      throw new Error(parts.join(" · ") || "Validación fallida.");
    }
    throw new Error("No se pudo confirmar la extracción");
  }
  return data as unknown as ConfirmOk;
}
