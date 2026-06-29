/**
 * SeguimientoPanel — displays the seguimientos de tratamiento for a given ingreso.
 *
 * Lists SeguimTratamientoRead items: badges for disminucion_farmacos and cambio_esquema,
 * plus plan_disminucion, detalle_cambio, and observaciones text when present.
 *
 * Hosts the "Agregar seguimiento" action in its header, gated by canWrite && registro != null.
 */
import { useState } from "react";
import { Plus, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSeguimientos } from "./hooks";
import { NuevoSeguimientoDialog } from "./NuevoSeguimientoDialog";
import type { SeguimTratamientoRead, RegistroFarmacologicoRead } from "./api";

// ── Item card ────────────────────────────────────────────────────────────────

function SeguimientoItem({ seg }: { seg: SeguimTratamientoRead }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-2">
      {/* Badges */}
      <div className="flex flex-wrap gap-2">
        {seg.disminucion_farmacos ? (
          <Badge variant="warning">Disminución de fármacos</Badge>
        ) : (
          <Badge variant="neutral">Sin disminución</Badge>
        )}
        {seg.cambio_esquema ? (
          <Badge variant="info">Cambio de esquema</Badge>
        ) : (
          <Badge variant="neutral">Sin cambio de esquema</Badge>
        )}
      </div>

      {/* Plan de disminución */}
      {seg.plan_disminucion && (
        <div className="text-[12.5px]">
          <span className="text-muted-foreground font-medium">
            Plan de disminución:{" "}
          </span>
          <span>{seg.plan_disminucion}</span>
        </div>
      )}

      {/* Detalle del cambio */}
      {seg.detalle_cambio && (
        <div className="text-[12.5px]">
          <span className="text-muted-foreground font-medium">
            Detalle del cambio:{" "}
          </span>
          <span>{seg.detalle_cambio}</span>
        </div>
      )}

      {/* Observaciones */}
      {seg.observaciones && (
        <div className="text-[12.5px]">
          <span className="text-muted-foreground font-medium">
            Observaciones:{" "}
          </span>
          <span>{seg.observaciones}</span>
        </div>
      )}
    </div>
  );
}

// ── Panel ────────────────────────────────────────────────────────────────────

interface Props {
  ingresoId: number;
  /** The registro for this ingreso (null if not yet created). */
  registro: RegistroFarmacologicoRead | null | undefined;
  canWrite: boolean;
}

export function SeguimientoPanel({ ingresoId, registro, canWrite }: Props) {
  const { data: seguimientos = [], isLoading, isError } = useSeguimientos(ingresoId);
  const [dialogOpen, setDialogOpen] = useState(false);

  const canAdd = canWrite && registro != null;

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando seguimientos…
      </p>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 text-[13px] text-destructive">
        No se pudieron cargar los seguimientos de tratamiento.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Panel header */}
      <div className="flex items-center justify-between gap-4 px-0.5">
        <h2 className="text-[14px] font-semibold">Seguimientos de tratamiento</h2>
        {canAdd && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setDialogOpen(true)}
            aria-label="Agregar seguimiento"
            data-testid="btn-agregar-seguimiento"
          >
            <Plus /> Agregar seguimiento
          </Button>
        )}
      </div>

      {/* Empty state */}
      {seguimientos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
          <ClipboardList className="mx-auto mb-3 size-7 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            Sin seguimientos registrados.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {seguimientos.map((seg) => (
            <SeguimientoItem key={seg.id} seg={seg} />
          ))}
        </div>
      )}

      {/* Dialog */}
      {canAdd && (
        <NuevoSeguimientoDialog
          ingresoId={ingresoId}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
    </div>
  );
}
