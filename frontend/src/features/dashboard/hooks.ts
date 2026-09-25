import { useQuery } from "@tanstack/react-query";
import { obtenerDashboard, obtenerIngresosActivos, type DashboardFiltros } from "./api";

export function useDashboard(filtros: DashboardFiltros) {
  return useQuery({
    queryKey: ["dashboard", filtros],
    queryFn: () => obtenerDashboard(filtros),
  });
}

/** Conteo de ingresos activos. Se invalida junto con ["dashboard"] al crear/editar un ingreso. */
export function useIngresosActivos() {
  return useQuery({
    queryKey: ["dashboard", "activos"],
    queryFn: obtenerIngresosActivos,
  });
}
