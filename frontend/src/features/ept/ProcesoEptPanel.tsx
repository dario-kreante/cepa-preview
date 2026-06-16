/**
 * ProcesoEptPanel — displays the proceso EPT for an active caso.
 *
 * States:
 *   - Loading / error
 *   - null (404) → empty state + "Registrar proceso" CTA (when canWrite)
 *   - data → read view + "Editar proceso" button (when canWrite)
 */
import { useState } from "react";
import { AlertCircle, ClipboardList } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/utils";
import { useProceso } from "./hooks";
import { ProcesoEptDialog } from "./ProcesoEptDialog";
import type { ProcesoEptRead } from "./api";

interface Props {
  casoId: number;
  canWrite: boolean;
}

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

function ProcesoView({
  proceso,
  canWrite,
  onEdit,
}: {
  proceso: ProcesoEptRead;
  canWrite: boolean;
  onEdit: () => void;
}) {
  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-[14px] font-semibold">Proceso EPT</h3>
        {canWrite && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[11.5px] px-2"
            onClick={onEdit}
            data-testid="btn-editar-proceso"
          >
            Editar proceso
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <FieldRow
          label="Plazo evid. denunciante"
          value={proceso.plazo_evid_denunciante ? fmtDate(proceso.plazo_evid_denunciante) : "—"}
        />
        <FieldRow
          label="Plazo insumos empresa"
          value={proceso.plazo_insumos_empresa ? fmtDate(proceso.plazo_insumos_empresa) : "—"}
        />
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Testigos
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <Badge variant={proceso.hay_testigos ? "info" : "neutral"}>
              {proceso.hay_testigos ? "Sí" : "No"}
            </Badge>
            {proceso.hay_testigos && (
              <span className="text-[13px]">({proceso.testigos_cantidad})</span>
            )}
          </div>
        </div>
        <FieldRow
          label="N° entrevistas"
          value={proceso.num_entrevistas}
        />
        {proceso.insumos_eista && (
          <FieldRow label="Insumos EISTA" value={proceso.insumos_eista} />
        )}
        {proceso.doc_incumplimiento && (
          <FieldRow
            label="Doc. incumplimiento"
            value={proceso.doc_incumplimiento}
          />
        )}
        {proceso.observaciones && (
          <div className="col-span-2">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
              Observaciones
            </p>
            <p className="text-[13px] mt-0.5 whitespace-pre-line">
              {proceso.observaciones}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

export function ProcesoEptPanel({ casoId, canWrite }: Props) {
  const { data, isLoading, isError, error } = useProceso(casoId);
  const [dialogOpen, setDialogOpen] = useState(false);

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando proceso EPT…
      </p>
    );
  }

  if (isError) {
    const msg =
      error instanceof Error ? error.message : "No se pudo cargar el proceso EPT";
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-start gap-2">
        <AlertCircle className="size-4 text-destructive mt-0.5 shrink-0" />
        <p className="text-[13px] text-destructive">{msg}</p>
      </div>
    );
  }

  // null = 404 = no proceso yet
  if (data === null || data === undefined) {
    return (
      <>
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-8 text-center space-y-3">
          <ClipboardList className="mx-auto size-7 text-muted-foreground/50" />
          <p className="text-[13px] text-muted-foreground">
            Sin proceso registrado
          </p>
          {canWrite && (
            <Button
              size="sm"
              onClick={() => setDialogOpen(true)}
              data-testid="btn-registrar-proceso"
            >
              Registrar proceso
            </Button>
          )}
        </div>

        <ProcesoEptDialog
          casoId={casoId}
          proceso={null}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      </>
    );
  }

  return (
    <>
      <ProcesoView
        proceso={data}
        canWrite={canWrite}
        onEdit={() => setDialogOpen(true)}
      />
      <ProcesoEptDialog
        casoId={casoId}
        proceso={data}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </>
  );
}
