/**
 * EsquemaPanel — displays the medication scheme (indicaciones) for a given ingreso.
 *
 * Shows a list/table of `EsquemaIndicacionRead` items with: medicamento, dosis,
 * frecuencia (friendly Spanish label), and badges for extra_sistema / vigente.
 *
 * Hosts the "Agregar indicación" action in its header, delegating to
 * AgregarIndicacionDialog. The add button is hidden when:
 *   - there is no registro (cannot add indicaciones without a registro)
 *   - the user is not a writer (!canWrite)
 */
import { useState } from "react";
import { Plus, Pill } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useIndicaciones } from "./hooks";
import { AgregarIndicacionDialog } from "./AgregarIndicacionDialog";
import { FRECUENCIA_LABELS } from "./indicacionSchema";
import type { EsquemaIndicacionRead, FrecuenciaFarmaco, RegistroFarmacologicoRead } from "./api";

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function IndicacionRow({ ind }: { ind: EsquemaIndicacionRead }) {
  const frecuenciaLabel =
    FRECUENCIA_LABELS[ind.frecuencia as FrecuenciaFarmaco] ?? ind.frecuencia;

  return (
    <tr className="border-b hover:bg-muted/40 transition-colors">
      {/* Medicamento */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="size-7 rounded-md bg-[oklch(0.95_0.05_290)] text-[oklch(0.42_0.16_290)] grid place-items-center shrink-0">
            <Pill className="size-3.5" />
          </div>
          <span className="font-semibold text-[13px]">{ind.medicamento}</span>
        </div>
      </td>
      {/* Dosis */}
      <td className="px-4 py-3 text-[12.5px] text-muted-foreground">{ind.dosis}</td>
      {/* Frecuencia */}
      <td className="px-4 py-3 text-[12.5px]">{frecuenciaLabel}</td>
      {/* Badges */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1.5">
          {ind.extra_sistema && (
            <Badge variant="warning">Extra sistema</Badge>
          )}
          {ind.vigente ? (
            <Badge variant="success">Vigente</Badge>
          ) : (
            <Badge variant="neutral">Inactiva</Badge>
          )}
        </div>
      </td>
    </tr>
  );
}

interface Props {
  ingresoId: number;
  /** The registro for this ingreso (null if not yet created). */
  registro: RegistroFarmacologicoRead | null | undefined;
  canWrite: boolean;
}

export function EsquemaPanel({ ingresoId, registro, canWrite }: Props) {
  const { data: indicaciones = [], isLoading, isError } = useIndicaciones(ingresoId);
  const [dialogOpen, setDialogOpen] = useState(false);

  const canAdd = canWrite && registro != null;

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando esquema de indicaciones…
      </p>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 text-[13px] text-destructive">
        No se pudo cargar el esquema de indicaciones.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Panel header */}
      <div className="flex items-center justify-between gap-4 px-0.5">
        <h2 className="text-[14px] font-semibold">Esquema de indicaciones</h2>
        {canAdd && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setDialogOpen(true)}
            aria-label="Agregar indicación"
            data-testid="btn-agregar-indicacion"
          >
            <Plus /> Agregar indicación
          </Button>
        )}
      </div>

      {/* Empty state */}
      {indicaciones.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
          <Pill className="mx-auto mb-3 size-7 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            Sin indicaciones en el esquema.
          </p>
        </div>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Medicamento</Th>
                  <Th>Dosis</Th>
                  <Th>Frecuencia</Th>
                  <Th>Estado</Th>
                </tr>
              </thead>
              <tbody>
                {indicaciones.map((ind) => (
                  <IndicacionRow key={ind.id} ind={ind} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Dialog */}
      {canAdd && (
        <AgregarIndicacionDialog
          ingresoId={ingresoId}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
    </div>
  );
}
