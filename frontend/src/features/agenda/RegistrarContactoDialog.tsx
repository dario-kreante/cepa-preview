import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { RESULTADO_LABELS, type ResultadoGestion } from "./api";
import { useRegistrarGestion } from "./hooks";

const NOTA_MAX = 300;

const fieldCls =
  "flex w-full rounded-md border border-input bg-transparent px-3 py-1.5 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

export interface PacienteContacto {
  paciente_id: number;
  nombre: string;
}

function Formulario({
  paciente,
  profesionalId,
  onClose,
}: {
  paciente: PacienteContacto;
  profesionalId: number;
  onClose: () => void;
}) {
  const registrar = useRegistrarGestion();
  const [resultado, setResultado] = useState<ResultadoGestion | "">("");
  const [nota, setNota] = useState("");

  async function guardar() {
    if (!resultado) return;
    try {
      await registrar.mutateAsync({
        pacienteId: paciente.paciente_id,
        body: {
          profesional_id: profesionalId,
          resultado,
          nota: nota.trim() ? nota.trim() : null,
        },
      });
      toast.success("Contacto registrado");
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al registrar");
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Registrar contacto</DialogTitle>
        <DialogDescription>{paciente.nombre}</DialogDescription>
      </DialogHeader>
      <div className="space-y-3">
        <div>
          <Label htmlFor="resultado-gestion">Resultado</Label>
          <select
            id="resultado-gestion"
            className={cn(fieldCls, "h-9")}
            value={resultado}
            onChange={(e) =>
              setResultado(e.target.value as ResultadoGestion | "")
            }
          >
            <option value="">Selecciona un resultado</option>
            {(Object.keys(RESULTADO_LABELS) as ResultadoGestion[]).map((r) => (
              <option key={r} value={r}>
                {RESULTADO_LABELS[r]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="nota-gestion">Nota (opcional)</Label>
          <textarea
            id="nota-gestion"
            rows={3}
            maxLength={NOTA_MAX}
            className={fieldCls}
            value={nota}
            onChange={(e) => setNota(e.target.value)}
          />
          <p className="mt-1 text-right text-[11px] text-muted-foreground">
            {nota.length}/{NOTA_MAX}
          </p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Cancelar
        </Button>
        <Button onClick={guardar} disabled={!resultado || registrar.isPending}>
          {registrar.isPending ? "Guardando…" : "Guardar"}
        </Button>
      </DialogFooter>
    </>
  );
}

export function RegistrarContactoDialog({
  paciente,
  profesionalId,
  onClose,
}: {
  paciente: PacienteContacto | null;
  profesionalId: number;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={paciente !== null}
      onOpenChange={(open) => !open && onClose()}
    >
      <DialogContent>
        {paciente && (
          <Formulario
            key={paciente.paciente_id}
            paciente={paciente}
            profesionalId={profesionalId}
            onClose={onClose}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
