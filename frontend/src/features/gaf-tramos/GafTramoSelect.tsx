/**
 * GafTramoSelect — select nativo con los tramos de GAF del catálogo (v5 D18).
 * El valor es la etiqueta del tramo ("41-50"); "" = sin tramo.
 */
import { forwardRef, type SelectHTMLAttributes } from "react";
import { useGafTramos } from "./hooks";

type Props = SelectHTMLAttributes<HTMLSelectElement> & { placeholder?: string };

export const GafTramoSelect = forwardRef<HTMLSelectElement, Props>(function GafTramoSelect(
  { placeholder = "Sin tramo", className, ...rest },
  ref,
) {
  const { data: tramos = [] } = useGafTramos();
  return (
    <select
      ref={ref}
      className={
        className ??
        "mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring appearance-none"
      }
      {...rest}
    >
      <option value="">{placeholder}</option>
      {tramos.map((t) => (
        <option key={t.id} value={t.etiqueta}>
          {t.etiqueta}
        </option>
      ))}
    </select>
  );
});
