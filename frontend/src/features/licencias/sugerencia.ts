import type { SugerenciaLicencia } from "./AltaLicenciaDialog";
import type { LicenciaSugeridaRead } from "@/features/ingresos/api";

/** Lo que la indicación dice pasa al alta; el reposo parte igual que la licencia. */
export function aSugerencia(s: LicenciaSugeridaRead): SugerenciaLicencia {
  return {
    valores: {
      tipo_lm: s.tipo_lm ?? undefined,
      tipo_reposo: s.tipo_reposo ?? undefined,
      fecha_inicio: s.fecha_inicio ?? undefined,
      fecha_termino: s.fecha_termino ?? undefined,
      inicio_reposo: s.fecha_inicio ?? undefined,
      fin_reposo: s.fecha_termino ?? undefined,
      cantidad_dias: s.cantidad_dias ?? undefined,
      origen: s.origen,
    },
    avisos: s.avisos,
  };
}
