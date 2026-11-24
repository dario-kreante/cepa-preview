/**
 * CierreCasoDialog — cierra o reabre un caso (QA-011).
 *
 * Cerrar: el motivo es obligatorio (lista propia, distinta del tipo de alta). Reabrir:
 * solo Coordinación; el caso vuelve a «Activo» y el cierre anterior queda en el historial de
 * cierres de la ficha (QA-007), con el motivo de reapertura si se indica.
 */
import { useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCambiarEstadoIngreso } from "./hooks";
import { MOTIVOS_CIERRE, etiquetaMotivo } from "./motivosCierre";
import type { MotivoCierre } from "./api";

interface Props {
  modo: "cerrar" | "reabrir";
  open: boolean;
  onOpenChange: (o: boolean) => void;
  pacienteId: number;
  ingresoId: number;
  /** Motivo con el que está cerrado (solo al reabrir, para informarlo). */
  motivoActual?: string | null;
}

export function CierreCasoDialog({ modo, open, onOpenChange, pacienteId, ingresoId, motivoActual }: Props) {
  const [motivo, setMotivo] = useState<MotivoCierre | "">("");
  const [motivoReapertura, setMotivoReapertura] = useState("");
  const cambiar = useCambiarEstadoIngreso(pacienteId);
  const cerrando = modo === "cerrar";

  function confirmar() {
    if (cerrando && !motivo) return;
    cambiar.mutate(
      cerrando
        ? { ingresoId, estado: "cerrado", motivoCierre: motivo as MotivoCierre }
        : { ingresoId, estado: "activo", motivoReapertura },
      {
        onSuccess: () => {
          toast.success(cerrando ? "Caso cerrado" : "Caso reabierto: vuelve a Activo");
          setMotivo("");
          setMotivoReapertura("");
          onOpenChange(false);
        },
        onError: (e) => toast.error(e.message),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{cerrando ? "Cerrar caso" : "Reabrir caso"}</DialogTitle>
          <DialogDescription>
            {cerrando
              ? "El paciente dejará de contar como caso activo y de generar alertas. Elige el motivo del cierre."
              : `El caso volverá a «Activo». El cierre anterior${
                  etiquetaMotivo(motivoActual) ? ` (motivo: ${etiquetaMotivo(motivoActual)})` : ""
                } queda registrado en el historial de cierres de la ficha.`}
          </DialogDescription>
        </DialogHeader>
        {cerrando && (
          <div className="space-y-1.5">
            <Label htmlFor="motivo-cierre">Motivo de cierre</Label>
            <Select value={motivo} onValueChange={(v) => setMotivo(v as MotivoCierre)}>
              <SelectTrigger id="motivo-cierre" data-testid="motivo-cierre">
                <SelectValue placeholder="Selecciona un motivo" />
              </SelectTrigger>
              <SelectContent>
                {MOTIVOS_CIERRE.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        {!cerrando && (
          <div className="space-y-1.5">
            <Label htmlFor="motivo-reapertura">Motivo de reapertura (opcional)</Label>
            <textarea
              id="motivo-reapertura"
              data-testid="motivo-reapertura"
              rows={2}
              maxLength={300}
              value={motivoReapertura}
              onChange={(e) => setMotivoReapertura(e.target.value)}
              placeholder="Por qué se reabre el caso"
              className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={cambiar.isPending}>
            Cancelar
          </Button>
          <Button
            onClick={confirmar}
            disabled={cambiar.isPending || (cerrando && !motivo)}
            variant={cerrando ? "destructive" : "default"}
          >
            {cerrando ? "Confirmar cierre" : "Confirmar reapertura"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
