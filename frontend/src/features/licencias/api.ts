import { api } from "@/lib/apiClient";
import type { components } from "@/types/api";

// Qualified name: the full LicenciaRead (all fields), used by licencia endpoints.
export type LicenciaRead =
  components["schemas"]["app__schemas__licencia__LicenciaRead"];

// Slim projection used inside LicenciasResponse.historial
export type LicenciaReadSlim =
  components["schemas"]["app__schemas__licencia_api__LicenciaRead"];

export type LicenciaCreate = components["schemas"]["LicenciaCreate"];
export type LicenciasResponse = components["schemas"]["LicenciasResponse"];
export type LicenciaISLUpdate = components["schemas"]["LicenciaISLUpdate"];
export type LicenciaAnularUpdate = components["schemas"]["LicenciaAnularUpdate"];
export type AcumuladoRead = components["schemas"]["AcumuladoRead"];
export type AlertaLicenciaRead = components["schemas"]["AlertaLicenciaRead"];

export async function buscarLicenciasPorFolio(
  folio: string,
): Promise<LicenciasResponse> {
  const { data, error, response } = await api.GET(
    "/api/v1/licencias/folio/{folio}",
    { params: { path: { folio } } },
  );
  if (error || !data) {
    if (response.status === 404) {
      // Folio sin licencias registradas — devolver estructura vacía tipada
      const empty: LicenciasResponse = {
        folio,
        historial: [],
        dias_acumulados: 0,
      };
      return empty;
    }
    throw new Error("Error al buscar licencias");
  }
  return data;
}

export async function crearLicencia(body: LicenciaCreate): Promise<LicenciaRead> {
  const { data, error, response } = await api.POST("/api/v1/licencias", {
    body,
  });
  if (error || !data) {
    if (response.status === 409)
      throw new Error("Conflicto al registrar la licencia.");
    if (response.status === 422)
      throw new Error("Datos inválidos. Revisa los campos.");
    throw new Error("No se pudo crear la licencia");
  }
  // The OpenAPI spec declares 201 as { [key: string]: unknown } but the
  // backend returns the full LicenciaRead shape; cast to the known type.
  return data as unknown as LicenciaRead;
}

export async function anularLicencia(
  id: number,
  observaciones: string,
): Promise<LicenciaRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/licencias/{licencia_id}/anular",
    {
      params: { path: { licencia_id: id } },
      body: { observaciones },
    },
  );
  if (error || !data) throw new Error("No se pudo anular la licencia");
  return data;
}

export async function actualizarISL(
  id: number,
  body: LicenciaISLUpdate,
): Promise<LicenciaRead> {
  const { data, error } = await api.PATCH(
    "/api/v1/licencias/{licencia_id}/isl",
    {
      params: { path: { licencia_id: id } },
      body,
    },
  );
  if (error || !data) throw new Error("No se pudo actualizar el envío ISL");
  return data;
}

export async function generarAlertasLicencias(): Promise<AlertaLicenciaRead[]> {
  // No requestBody on this endpoint
  const { data, error } = await api.POST("/api/v1/licencias/alertas/generar", {});
  if (error) throw new Error("No se pudieron generar alertas");
  return data ?? [];
}

export async function acumuladoPorIngreso(
  ingresoId: number,
): Promise<AcumuladoRead> {
  const { data, error } = await api.GET(
    "/api/v1/ingresos/{ingreso_id}/licencias/acumulado",
    { params: { path: { ingreso_id: ingresoId } } },
  );
  if (error || !data) throw new Error("No se pudo obtener el acumulado");
  return data;
}
