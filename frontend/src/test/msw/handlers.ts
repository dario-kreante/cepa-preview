import { http, HttpResponse } from "msw";
const BASE = import.meta.env.VITE_API_BASE_URL;

export const handlers = [
  http.get(`${BASE}/api/v1/pacientes/buscar`, () => HttpResponse.json([])),
];
