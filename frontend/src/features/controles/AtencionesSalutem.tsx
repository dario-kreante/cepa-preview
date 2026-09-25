import { Stethoscope } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useFichasClinicas } from "@/features/ingresos/hooks";
import type { FichaClinicaRead } from "@/features/ingresos/api";

function texto(v: unknown): string | null {
  return typeof v === "string" && v.trim() !== "" ? v : null;
}

/** "2025-01-22" → "22/01/2025"; cualquier otro formato se muestra tal cual. */
function fechaCorta(v: unknown): string {
  const s = texto(v);
  if (!s) return "Sin fecha";
  const [y, m, d] = s.slice(0, 10).split("-");
  return y && m && d ? `${d}/${m}/${y}` : s;
}

/** Solo las atenciones que vienen de SALUTEM, de la más reciente a la más antigua. */
function deSalutem(fichas: FichaClinicaRead[]): FichaClinicaRead[] {
  const fecha = (f: FichaClinicaRead) => texto(f.contenido?.citaFecha) ?? "";
  return fichas.filter((f) => f.origen === "SALUTEM").sort((a, b) => fecha(b).localeCompare(fecha(a)));
}

export interface AtencionesSalutemProps {
  fichas: FichaClinicaRead[];
  cargando?: boolean;
  error?: boolean;
}

/**
 * Atenciones de SALUTEM dentro de Controles médicos: lo que el equipo clínico registró en
 * SALUTEM durante el ingreso, junto a los controles del CEPA. Solo lectura (D12).
 */
export function AtencionesSalutem({ fichas, cargando, error }: AtencionesSalutemProps) {
  const atenciones = deSalutem(fichas);
  const titulo = `Atenciones en SALUTEM (${atenciones.length})`;

  return (
    <section aria-label={titulo} className="space-y-2">
      <div>
        <h3 className="text-[13px] font-semibold">{titulo}</h3>
        <p className="text-[11.5px] text-muted-foreground">
          Registradas por el equipo clínico en SALUTEM durante este ingreso. Solo lectura: se
          actualizan solas desde SALUTEM.
        </p>
      </div>
      {cargando ? (
        <p className="text-[12px] text-muted-foreground">Cargando atenciones…</p>
      ) : error ? (
        <p className="text-[12px] text-danger-600">No se pudieron cargar las atenciones de SALUTEM.</p>
      ) : atenciones.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">SALUTEM no tiene atenciones para este ingreso.</p>
      ) : (
        <ul className="space-y-2">
          {atenciones.map((f) => {
            const c = f.contenido ?? {};
            const detalle = [texto(c.profesionalNombre), texto(c.sucursalNombre), texto(c.estadoCitaNombre)]
              .filter(Boolean)
              .join(" · ");
            return (
              <li key={f.id}>
                <Card>
                  <CardContent className="p-3 flex items-center gap-3">
                    <div className="size-8 rounded-md bg-muted text-muted-foreground grid place-items-center shrink-0">
                      <Stethoscope className="size-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-[13px]">
                        {texto(c.especialidadNombre) ?? "Atención SALUTEM"}
                        <span className="ml-2 align-middle rounded border border-border px-1.5 py-px text-[10px] font-medium text-muted-foreground">
                          SALUTEM
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground truncate">
                        {fechaCorta(c.citaFecha)}
                        {detalle ? ` · ${detalle}` : ""}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/** Variante que carga sola las atenciones del folio (para la página de Controles). */
export function AtencionesSalutemDelFolio({ folio }: { folio: string }) {
  const { data: fichas = [], isLoading, isError } = useFichasClinicas(folio);
  return <AtencionesSalutem fichas={fichas} cargando={isLoading} error={isError} />;
}
