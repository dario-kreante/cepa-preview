/**
 * PlazosEptPanel — displays the plazos EPT for an active caso,
 * including backend-computed cumplimiento badges.
 *
 * States:
 *   - Loading / error
 *   - null (404) → empty state + "Registrar plazos" CTA (when canWrite)
 *   - data → read view with dates + cumplimiento badges + "Editar plazos" (when canWrite)
 */
import { useState } from "react";
import { AlertCircle, Clock } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/utils";
import { usePlazos } from "./hooks";
import { PlazosEptDialog } from "./PlazosEptDialog";
import type { EstadoCumplimiento, PlazoEptRead } from "./api";

interface Props {
  casoId: number;
  canWrite: boolean;
}

// ── Cumplimiento badge helpers ────────────────────────────────────────────────

const CUMPLIMIENTO_LABELS: Record<EstadoCumplimiento, string> = {
  en_plazo: "En plazo",
  por_vencer: "Por vencer",
  vencido: "Vencido",
  cumplido: "Cumplido",
};

function cumplimientoVariant(
  estado: EstadoCumplimiento
): "info" | "warning" | "destructive" | "success" {
  switch (estado) {
    case "en_plazo":
      return "info";
    case "por_vencer":
      return "warning";
    case "vencido":
      return "destructive";
    case "cumplido":
      return "success";
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <p className="text-[13px] mt-0.5">{value}</p>
    </div>
  );
}

function CumplimientoRow({
  label,
  estado,
}: {
  label: string;
  estado: EstadoCumplimiento;
}) {
  return (
    <div>
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <Badge
        variant={cumplimientoVariant(estado)}
        className="mt-0.5"
        data-testid={`badge-${label.toLowerCase().replace(/\s+/g, "-")}`}
      >
        {CUMPLIMIENTO_LABELS[estado]}
      </Badge>
    </div>
  );
}

function PlazosView({
  plazos,
  canWrite,
  onEdit,
}: {
  plazos: PlazoEptRead;
  canWrite: boolean;
  onEdit: () => void;
}) {
  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-[14px] font-semibold">Plazos EPT</h3>
        {canWrite && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[11.5px] px-2"
            onClick={onEdit}
            data-testid="btn-editar-plazos"
          >
            Editar plazos
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <FieldRow
          label="Plazo informe EPT"
          value={
            plazos.plazo_informe_ept ? fmtDate(plazos.plazo_informe_ept) : "—"
          }
        />
        <FieldRow
          label="Plazo portal ISL"
          value={
            plazos.plazo_portal_isl ? fmtDate(plazos.plazo_portal_isl) : "—"
          }
        />
        <FieldRow
          label="Fecha entrega ISL"
          value={
            plazos.fecha_entrega_isl ? fmtDate(plazos.fecha_entrega_isl) : "—"
          }
        />
        <FieldRow
          label="Fecha envío"
          value={plazos.fecha_envio ? fmtDate(plazos.fecha_envio) : "—"}
        />

        {/* Backend-computed cumplimiento badges — read-only */}
        <CumplimientoRow
          label="Estado informe"
          estado={plazos.estado_informe}
        />
        <CumplimientoRow
          label="Estado entrega ISL"
          estado={plazos.estado_entrega_isl}
        />
      </div>
    </Card>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function PlazosEptPanel({ casoId, canWrite }: Props) {
  const { data, isLoading, isError, error } = usePlazos(casoId);
  const [dialogOpen, setDialogOpen] = useState(false);

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando plazos EPT…
      </p>
    );
  }

  if (isError) {
    const msg =
      error instanceof Error
        ? error.message
        : "No se pudo cargar los plazos EPT";
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-start gap-2">
        <AlertCircle className="size-4 text-destructive mt-0.5 shrink-0" />
        <p className="text-[13px] text-destructive">{msg}</p>
      </div>
    );
  }

  // null = 404 = no plazos yet
  if (data === null || data === undefined) {
    return (
      <>
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-8 text-center space-y-3">
          <Clock className="mx-auto size-7 text-muted-foreground/50" />
          <p className="text-[13px] text-muted-foreground">
            Sin plazos registrados
          </p>
          {canWrite && (
            <Button
              size="sm"
              onClick={() => setDialogOpen(true)}
              data-testid="btn-registrar-plazos"
            >
              Registrar plazos
            </Button>
          )}
        </div>

        <PlazosEptDialog
          casoId={casoId}
          plazos={null}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      </>
    );
  }

  return (
    <>
      <PlazosView
        plazos={data}
        canWrite={canWrite}
        onEdit={() => setDialogOpen(true)}
      />
      <PlazosEptDialog
        casoId={casoId}
        plazos={data}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </>
  );
}
