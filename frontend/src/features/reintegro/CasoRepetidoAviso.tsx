/**
 * Aviso al crear un caso de reintegro para un paciente que ya tiene casos activos (QA-003).
 * No bloquea: se puede abrir uno de los casos existentes o continuar con el alta.
 */
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fmtDate } from "@/lib/utils";
import type { CasoReintegroRead } from "./api";
import { ESTADO_REINTEGRO_LABELS } from "./cierreSchema";

interface Props {
  casos: CasoReintegroRead[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAbrir: (casoId: number) => void;
  onContinuar: () => void;
}

export function CasoRepetidoAviso({ casos, open, onOpenChange, onAbrir, onContinuar }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Este paciente ya tiene casos activos</DialogTitle>
          <DialogDescription>
            Revisa si alguno de estos casos corresponde antes de crear uno nuevo. Puedes
            continuar de todos modos.
          </DialogDescription>
        </DialogHeader>

        <ul className="space-y-2 py-1">
          {casos.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
            >
              <div className="min-w-0 text-[13px]">
                <p className="font-semibold">Caso N° {c.id}</p>
                <p className="text-[12px] text-muted-foreground truncate">
                  {fmtDate(c.fecha_caso)} · {c.region}
                  {c.razon_social ? ` · ${c.razon_social}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge variant={c.estado_reintegro === "parcial" ? "warning" : "info"}>
                  {ESTADO_REINTEGRO_LABELS[c.estado_reintegro]}
                </Badge>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-[11.5px] px-2"
                  aria-label={`Abrir caso N° ${c.id}`}
                  onClick={() => onAbrir(c.id)}
                >
                  Abrir
                </Button>
              </div>
            </li>
          ))}
        </ul>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="button" onClick={onContinuar}>
            Continuar de todos modos
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
