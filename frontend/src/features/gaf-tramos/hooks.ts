import { useQuery } from "@tanstack/react-query";
import { listarGafTramos } from "./api";

/** Catálogo de tramos de GAF. Cambia muy poco: se cachea por la sesión. */
export function useGafTramos() {
  return useQuery({
    queryKey: ["gaf-tramos"],
    queryFn: listarGafTramos,
    staleTime: Infinity,
  });
}
