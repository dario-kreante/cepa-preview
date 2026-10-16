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
import { useDescartarBorrador } from "./hooks";
import type { PacientePendienteRead } from "./api";

interface Props {
  paciente: PacientePendienteRead | null;
  onOpenChange: (open: boolean) => void;
}

const MAX_MOTIVO = 300;

export function DescartarBorradorDialog({ paciente, onOpenChange }: Props) {
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const descartar = useDescartarBorrador();

  function cerrar(open: boolean) {
    if (!open) {
      setMotivo("");
      setError(null);
    }
    onOpenChange(open);
  }

  async function confirmar(e: React.FormEvent) {
    e.preventDefault();
    if (!paciente) return;
    const texto = motivo.trim();
    if (!texto) {
      setError("Indica el motivo del descarte.");
      return;
    }
    try {
      await descartar.mutateAsync({ id: paciente.id, motivo: texto });
      toast.success("Paciente descartado");
      cerrar(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "No se pudo descartar el paciente");
    }
  }

  return (
    <Dialog open={paciente !== null} onOpenChange={cerrar}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Descartar paciente</DialogTitle>
          <DialogDescription className="text-[12.5px] text-muted-foreground">
            {paciente?.nombre} no es paciente del CEPA. Queda fuera de esta lista y se
            registra el motivo.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={confirmar} className="space-y-4 py-2">
          <div>
            <Label htmlFor="motivo-descarte">Motivo</Label>
            <textarea
              id="motivo-descarte"
              value={motivo}
              maxLength={MAX_MOTIVO}
              rows={3}
              onChange={(e) => {
                setMotivo(e.target.value);
                setError(null);
              }}
              className="mt-1 flex w-full rounded-md border border-input bg-background px-3 py-2 text-[13px] shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {error && <p className="text-[11.5px] text-destructive mt-1">{error}</p>}
          </div>
          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => cerrar(false)}
              disabled={descartar.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" variant="destructive" disabled={descartar.isPending}>
              {descartar.isPending ? "Descartando…" : "Descartar paciente"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
