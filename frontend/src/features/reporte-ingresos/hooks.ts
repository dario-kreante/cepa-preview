import { useQuery } from "@tanstack/react-query";
import { obtenerReporteIngresos } from "./api";

export function useReporteIngresos(periodo: { fecha_desde: string; fecha_hasta: string }) {
  return useQuery({
    queryKey: ["reportes", "ingresos", periodo],
    queryFn: () => obtenerReporteIngresos(periodo),
  });
}
