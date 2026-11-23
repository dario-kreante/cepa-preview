import { useEffect, useState } from "react";
import { useConvenios, useConvenioSugerido } from "./hooks";

interface Props {
  id: string;
  /** Nombre del convenio elegido; `""` = Sin convenio. */
  value: string;
  onChange: (valor: string) => void;
  /** Valor ya guardado: si salió del catálogo, se sigue viendo y no se pierde al guardar. */
  valorGuardado?: string | null;
  /** Con esto se pide el convenio sugerido por el historial del paciente (SALUTEM). */
  sugerencia?: { paciente_id?: number; rut?: string } | null;
  className?: string;
}

const CLASE_BASE = "w-full rounded-md border border-ink-300 px-3 py-2 text-sm";

/**
 * Selector «Convenio» de la ficha de ingreso. Ofrece Sin convenio y los convenios
 * seleccionables; con `sugerencia` precarga el del historial mientras el usuario no haya
 * tocado el campo (una vez que elige algo, la sugerencia no vuelve a pisarlo).
 */
export function ConvenioSelect({ id, value, onChange, valorGuardado, sugerencia, className }: Props) {
  const { data: convenios = [], isSuccess } = useConvenios(true);
  const { data: sugerido } = useConvenioSugerido(sugerencia ?? null);
  // Una vez que el usuario elige algo, la sugerencia no vuelve a tocar el campo.
  const [tocado, setTocado] = useState(false);
  // Convenio que puso la sugerencia (no el usuario): solo para mostrar la nota.
  const [aplicado, setAplicado] = useState<string | null>(null);

  const nombres = convenios.map((c) => c.nombre);
  const fueraDeCatalogo = isSuccess && valorGuardado && !nombres.includes(valorGuardado) ? valorGuardado : null;
  const candidato = sugerido?.convenio;
  const vigente = candidato?.seleccionable ? candidato.nombre : null;

  // `aplicado` se ajusta durante el render (patrón de React para derivar estado de props):
  // marca el valor que puso la sugerencia y se suelta cuando el valor ya es otro.
  if (!tocado && vigente !== null && value === vigente && aplicado !== vigente) {
    setAplicado(vigente);
  } else if (aplicado !== null && value !== aplicado) {
    setAplicado(null);
  }

  // El efecto solo avisa al formulario; no toca estado propio.
  useEffect(() => {
    if (tocado) return;
    // La sugerencia aplicada dejó de valer (cambió el RUT: recargando, sin sugerido u otro
    // convenio): se retira, para no dejar un convenio equivocado en silencio.
    if (aplicado !== null && value === aplicado && vigente !== aplicado) {
      onChange("");
      return;
    }
    if (vigente && value === "") onChange(vigente);
  }, [tocado, aplicado, vigente, value, onChange]);

  return (
    <>
      <select
        id={id}
        value={value}
        onChange={(e) => {
          setTocado(true);
          onChange(e.target.value);
        }}
        className={className ?? CLASE_BASE}
      >
        <option value="">Sin convenio</option>
        {nombres.map((n) => (
          <option key={n} value={n}>{n}</option>
        ))}
        {fueraDeCatalogo && (
          <option value={fueraDeCatalogo}>{`${fueraDeCatalogo} (valor anterior)`}</option>
        )}
      </select>
      {aplicado !== null && value === aplicado && (
        <p className="text-[12px] text-muted-foreground">Sugerido desde SALUTEM</p>
      )}
    </>
  );
}
