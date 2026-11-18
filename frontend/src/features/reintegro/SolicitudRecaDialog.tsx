/**
 * SolicitudRecaDialog — registra o corrige la fecha en que se solicitó la RECA (QA-003).
 * El backend vuelve a validar (no futura, no anterior a la fecha del caso).
 */
import { useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRegistrarSolicitudReca } from "./hooks";
import { hoyChile, validarFechaSolicitud } from "./solicitudRecaSchema";
import type { CasoReintegroRead } from "./api";

interface Props {
  caso: CasoReintegroRead;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SolicitudRecaDialog({ caso, open, onOpenChange }: Props) {
  const corrigiendo = caso.fecha_solicitud_reca != null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{corrigiendo ? "Corregir solicitud de RECA" : "Registrar solicitud de RECA"}</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Fecha en que el CEPA solicitó la RECA. No puede ser futura ni anterior a la fecha del caso.
          </p>
        </DialogHeader>
        {/* El contenido se desmonta al cerrar: cada apertura parte de la fecha registrada. */}
        <FormularioSolicitud caso={caso} onOpenChange={onOpenChange} />
      </DialogContent>
    </Dialog>
  );
}

function FormularioSolicitud({
  caso,
  onOpenChange,
}: {
  caso: CasoReintegroRead;
  onOpenChange: (open: boolean) => void;
}) {
  const registrar = useRegistrarSolicitudReca();
  const [fecha, setFecha] = useState(caso.fecha_solicitud_reca ?? "");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const mensaje = validarFechaSolicitud(fecha, caso.fecha_caso);
    setError(mensaje);
    if (mensaje) return;
    try {
      await registrar.mutateAsync({ casoId: caso.id, fecha });
      toast.success("Solicitud de RECA registrada");
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar la solicitud de RECA");
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3 py-2" noValidate>
      <div>
        <Label htmlFor="fecha_solicitud_reca">Fecha de solicitud</Label>
        <Input
          id="fecha_solicitud_reca"
          type="date"
          min={caso.fecha_caso}
          max={hoyChile()}
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          aria-invalid={error ? true : undefined}
        />
        {error && (
          <p role="alert" className="mt-1 text-[12px] text-destructive">
            {error}
          </p>
        )}
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
          Cancelar
        </Button>
        <Button type="submit" disabled={registrar.isPending}>
          {registrar.isPending ? "Guardando…" : "Guardar"}
        </Button>
      </DialogFooter>
    </form>
  );
}
