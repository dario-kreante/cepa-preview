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
];
