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
import { useAtencionSalutem, useControl } from "@/features/controles/hooks";
import { DocumentosSalutem } from "@/features/controles/DocumentosSalutem";

/** Lo que se abre desde la alerta: un control, o una atención de SALUTEM que no es control. */
export type CasoAlerta = { tipo: "control"; id: number } | { tipo: "atencion"; id: number };

interface Props {
  titulo: string;
  caso: CasoAlerta | null;
  onOpenChange: (open: boolean) => void;
}

function fecha(iso: string | null | undefined): string {
  return iso ? iso.split("-").reverse().join("-") : "—";
}

/** El control o la atención de una alerta de licencia o receta, con sus documentos de SALUTEM. */
export function DocumentosAlertaDialog({ titulo, caso, onOpenChange }: Props) {
  const navigate = useNavigate();
  const esControl = caso?.tipo === "control";

  return (
    <Dialog open={caso !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>
            Revisa la indicación del médico y los documentos que subió a SALUTEM.
          </DialogDescription>
        </DialogHeader>
        {caso?.tipo === "control" && <DetalleControl controlId={caso.id} />}
        {caso?.tipo === "atencion" && <DetalleAtencion citaId={caso.id} />}
        {esControl && (
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
        )}
      </DialogContent>
    </Dialog>
  );
}

function DetalleControl({ controlId }: { controlId: number }) {
  const { data: control, isLoading, isError } = useControl(controlId);
  if (isError)
    return (
      <p className="text-[13px] text-destructive">
        No se encontró el control (pudo ser anulado en SALUTEM).
      </p>
    );
  if (isLoading || !control)
    return <p className="text-[13px] text-muted-foreground">Cargando control…</p>;
  return (
    <div className="space-y-3 text-[13px]">
      <p>
        Control del {fecha(control.fecha_control)} · {control.medico_tratante}
      </p>
      {control.resumen_termino_lm && (
        <p className="rounded-md bg-muted/40 p-2">{control.resumen_termino_lm}</p>
      )}
      <DocumentosSalutem controlId={control.id} />
    </div>
  );
}

function DetalleAtencion({ citaId }: { citaId: number }) {
  const { data: atencion, isLoading, isError } = useAtencionSalutem(citaId);
  if (isError)
    return (
      <p className="text-[13px] text-destructive">
        No se encontró la atención (pudo ser anulada en SALUTEM).
      </p>
    );
  if (isLoading || !atencion)
    return <p className="text-[13px] text-muted-foreground">Cargando atención…</p>;
  return (
    <div className="space-y-3 text-[13px]">
      <p>
        {atencion.especialidad ?? "Atención"} del {fecha(atencion.fecha)}
        {atencion.profesional ? ` · ${atencion.profesional}` : ""}
      </p>
      {atencion.indicacion_licencia && (
        <p className="rounded-md bg-muted/40 p-2">{atencion.indicacion_licencia}</p>
      )}
      <DocumentosSalutem citaId={atencion.cita_id} />
    </div>
  );
}
