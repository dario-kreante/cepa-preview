import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useControl } from "@/features/controles/hooks";
import { DocumentosSalutem } from "@/features/controles/DocumentosSalutem";

interface Props {
  titulo: string;
  controlId: number | null;
  onOpenChange: (open: boolean) => void;
}

/** El control de una alerta de licencia o receta, con sus documentos de SALUTEM. */
export function DocumentosAlertaDialog({ titulo, controlId, onOpenChange }: Props) {
  const navigate = useNavigate();
  const { data: control, isLoading } = useControl(controlId ?? 0);

  return (
    <Dialog open={controlId !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>
            Revisa la indicación del médico y los documentos que subió a SALUTEM.
          </DialogDescription>
        </DialogHeader>
        {isLoading || !control ? (
          <p className="text-[13px] text-muted-foreground">Cargando control…</p>
        ) : (
          <div className="space-y-3 text-[13px]">
            <p>
              Control del {control.fecha_control.split("-").reverse().join("-")} ·{" "}
              {control.medico_tratante}
            </p>
            {control.resumen_termino_lm && (
              <p className="rounded-md bg-muted/40 p-2">{control.resumen_termino_lm}</p>
            )}
            <DocumentosSalutem controlId={control.id} tieneLicencia={control.tiene_licencia} />
          </div>
        )}
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              onOpenChange(false);
              navigate("/controles");
            }}
          >
            Ir a Controles
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
