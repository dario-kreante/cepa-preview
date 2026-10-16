import { useQuery } from "@tanstack/react-query";
import {
  obtenerDashboard,
  obtenerDashboardOperativo,
  obtenerIngresosActivos,
  type DashboardFiltros,
} from "./api";

export function useDashboard(filtros: DashboardFiltros) {
  return useQuery({
    queryKey: ["dashboard", filtros],
    queryFn: () => obtenerDashboard(filtros),
  });
}

/** Dashboard de inicio. Bajo ["dashboard"] para invalidarse junto con los ingresos. */
export function useDashboardOperativo(periodo: { fecha_desde?: string; fecha_hasta?: string }) {
  return useQuery({
    queryKey: ["dashboard", "operativo", periodo],
    queryFn: () => obtenerDashboardOperativo(periodo),
  });
}

/** Conteo de ingresos activos. Se invalida junto con ["dashboard"] al crear/editar un ingreso. */
export function useIngresosActivos() {
  return useQuery({
    queryKey: ["dashboard", "activos"],
    queryFn: obtenerIngresosActivos,
  });
}
