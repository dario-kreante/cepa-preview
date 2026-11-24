/**
 * RemisionIslDialog — marca el caso «Remitido a ISL» con su fecha, sin cerrarlo (QA-010).
 * Resuelve la alerta «Pendiente de remitir a ISL». El backend vuelve a validar la fecha.
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
import { useRegistrarRemisionIsl } from "./hooks";
import { hoyChile, validarFechaRemision } from "./solicitudRecaSchema";
import type { CasoReintegroRead } from "./api";

interface Props {
  caso: CasoReintegroRead;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RemisionIslDialog({ caso, open, onOpenChange }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{caso.remitido_isl ? "Corregir remisión a ISL" : "Marcar remitido a ISL"}</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            El caso sigue abierto. No puede ser una fecha futura ni anterior a la fecha del caso.
          </p>
        </DialogHeader>
        {/* Se desmonta al cerrar: cada apertura parte de la fecha registrada (o de hoy). */}
        <FormularioRemision caso={caso} onOpenChange={onOpenChange} />
      </DialogContent>
    </Dialog>
  );
}

function FormularioRemision({
  caso,
  onOpenChange,
}: {
  caso: CasoReintegroRead;
  onOpenChange: (open: boolean) => void;
}) {
  const registrar = useRegistrarRemisionIsl();
  const [fecha, setFecha] = useState(caso.fecha_remitido_isl ?? hoyChile());
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const mensaje = validarFechaRemision(fecha, caso.fecha_caso);
    setError(mensaje);
    if (mensaje) return;
    try {
      await registrar.mutateAsync({ casoId: caso.id, fecha });
      toast.success("Caso marcado como remitido a ISL");
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo marcar el caso como remitido a ISL");
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3 py-2" noValidate>
      <div>
        <Label htmlFor="fecha_remitido_isl">Fecha de remisión a ISL</Label>
        <Input
          id="fecha_remitido_isl"
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
