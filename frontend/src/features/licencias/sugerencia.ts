import type { SugerenciaLicencia } from "./AltaLicenciaDialog";
import type { LicenciaSugeridaRead } from "@/features/ingresos/api";

/** Lo que la indicación dice pasa al alta (el reposo es el mismo período de la licencia). */
export function aSugerencia(s: LicenciaSugeridaRead): SugerenciaLicencia {
  return {
    valores: {
      tipo_lm: s.tipo_lm ?? undefined,
      tipo_reposo: s.tipo_reposo ?? undefined,
      fecha_inicio: s.fecha_inicio ?? undefined,
      fecha_termino: s.fecha_termino ?? undefined,
      cantidad_dias: s.cantidad_dias ?? undefined,
      eeag_gaf_tramo: s.eeag_gaf_tramo ?? undefined,
      // Lo que el médico escribió en "Indicación de reposo" (el campo admite 300).
      indicacion_reposo: s.texto ? s.texto.slice(0, 300) : undefined,
      origen: s.origen,
    },
    avisos: s.avisos,
  };
}
