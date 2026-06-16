import { http, HttpResponse } from "msw";
const BASE = import.meta.env.VITE_API_BASE_URL;

export const handlers = [
  http.get(`${BASE}/api/v1/pacientes/buscar`, () => HttpResponse.json([])),
  // Default handler for the esquema endpoint — returns empty list.
  // Individual tests can override via server.use().
  http.get(
    `${BASE}/api/v1/registro-farmacologico/:ingreso_id/esquema`,
    () => HttpResponse.json([]),
  ),
  // Default handler for the seguimiento endpoint — returns empty list.
  // Individual tests can override via server.use().
  http.get(
    `${BASE}/api/v1/registro-farmacologico/:ingreso_id/seguimiento`,
    () => HttpResponse.json([]),
  ),
  // Default handler for proceso EPT — returns 404 (no proceso yet).
  // Individual tests can override via server.use().
  http.get(
    `${BASE}/api/v1/casos-ept/:casoId/proceso`,
    () => new HttpResponse(null, { status: 404 }),
  ),
];
