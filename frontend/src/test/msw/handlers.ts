import { http, HttpResponse } from "msw";
const BASE = import.meta.env.VITE_API_BASE_URL;

// Catálogo de tramos de GAF sembrado por la migración 1300 (v5 D18, provisorio).
export const GAF_TRAMOS = Array.from({ length: 10 }, (_, i) => ({
  id: i + 1,
  desde: i * 10 + 1,
  hasta: i * 10 + 10,
  etiqueta: `${i * 10 + 1}-${i * 10 + 10}`,
  orden: i + 1,
  provisorio: true,
}));

export const handlers = [
  http.get(`${BASE}/api/v1/gaf-tramos`, () => HttpResponse.json(GAF_TRAMOS)),
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
  // Default handler for the fármacos sugeridos (SALUTEM) endpoint — returns empty list.
  // Individual tests can override via server.use().
  http.get(
    `${BASE}/api/v1/registro-farmacologico/:ingreso_id/sugeridos`,
    () => HttpResponse.json([]),
  ),
  // Default handler for proceso EPT — returns 404 (no proceso yet).
  // Individual tests can override via server.use().
  http.get(
    `${BASE}/api/v1/casos-ept/:casoId/proceso`,
    () => new HttpResponse(null, { status: 404 }),
  ),
  // Default handler for plazos EPT — returns 404 (no plazos yet).
  // Individual tests can override via server.use().
  http.get(
    `${BASE}/api/v1/casos-ept/:casoId/plazos`,
    () => new HttpResponse(null, { status: 404 }),
  ),
];
