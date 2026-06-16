/**
 * AnularLicenciaDialog — confirms the annulment of a licencia médica.
 *
 * Requires a non-empty `observaciones` before the confirm button is enabled.
 * On confirm: PATCH /api/v1/licencias/{id}/anular { observaciones }.
 */
import { useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useAnularLicencia } from "./hooks";

interface Props {
  licenciaId: number;
  folio: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AnularLicenciaDialog({ licenciaId, folio, open, onOpenChange }: Props) {
  const [observaciones, setObservaciones] = useState("");
  const anularMutation = useAnularLicencia(folio);

  async function handleConfirm() {
    try {
      await anularMutation.mutateAsync({ id: licenciaId, observaciones });
      toast.success("Licencia anulada correctamente");
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "No se pudo anular la licencia";
      toast.error(msg);
    }
  }

  const isSubmitting = anularMutation.isPending;
  const canConfirm = observaciones.trim().length > 0 && !isSubmitting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Anular licencia</DialogTitle>
          <DialogDescription className="text-[12.5px]">
            Esta acción es irreversible. Debes justificar la anulación.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div>
            <Label htmlFor="anular-obs">Observaciones</Label>
            <textarea
              id="anular-obs"
              aria-label="Observaciones"
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              rows={4}
              placeholder="Motivo de anulación…"
              className="mt-1 flex w-full rounded-md border border-input bg-card px-3 py-2 text-[13px] shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={!canConfirm}
          >
            {isSubmitting ? "Anulando…" : "Anular"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
