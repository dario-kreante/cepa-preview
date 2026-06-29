import { useQuery } from "@tanstack/react-query";
import { obtenerDashboard, type DashboardFiltros } from "./api";

export function useDashboard(filtros: DashboardFiltros) {
  return useQuery({
    queryKey: ["dashboard", filtros],
    queryFn: () => obtenerDashboard(filtros),
  });
}
