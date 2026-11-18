import type { MotivoCierre } from "./api";

/** Motivos de cierre del caso (QA-011), en el orden pedido por la clienta. */
export const MOTIVOS_CIERRE: { value: MotivoCierre; label: string }[] = [
  { value: "reca_ec", label: "RECA EC" },
  { value: "alta_medica", label: "Alta médica" },
  { value: "alta_administrativa", label: "Alta administrativa" },
  { value: "abandono", label: "Abandono" },
  { value: "desiste_proceso", label: "Desiste del proceso" },
  { value: "cambio_prestador", label: "Cambio de prestador" },
];

export function etiquetaMotivo(motivo: string | null | undefined): string | null {
  return MOTIVOS_CIERRE.find((m) => m.value === motivo)?.label ?? null;
}

/** Etiqueta del estado del caso; un caso cerrado muestra su motivo: «Cerrado – Alta médica». */
export function etiquetaEstadoCaso(estado: string, motivo?: string | null): string {
  const base: Record<string, string> = {
    activo: "Activo",
    encuadre: "En encuadre",
    cerrado: "Cerrado",
    derivado: "Derivado",
  };
  const etiqueta = base[estado] ?? estado;
  const m = estado === "cerrado" ? etiquetaMotivo(motivo) : null;
  return m ? `${etiqueta} – ${m}` : etiqueta;
}
