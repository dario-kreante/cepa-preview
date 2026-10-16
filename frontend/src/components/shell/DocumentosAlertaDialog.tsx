import { useState } from "react";
import { CheckCircle2, FileText, Pill } from "lucide-react";
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
import { useContextoAlerta } from "@/features/alertas/hooks";
import { useLicenciasSugeridas } from "@/features/ingresos/hooks";
import type { LicenciaSugeridaRead } from "@/features/ingresos/api";
import { AltaLicenciaDialog } from "@/features/licencias/AltaLicenciaDialog";
import { aSugerencia } from "@/features/licencias/sugerencia";

/** Lo que se abre desde la alerta: un control, o una atención de SALUTEM que no es control. */
export type CasoAlerta = { tipo: "control"; id: number } | { tipo: "atencion"; id: number };

interface Props {
  titulo: string;
  caso: CasoAlerta | null;
  onOpenChange: (open: boolean) => void;
  /** La alerta abierta: con ella se busca el paciente y se ofrece gestionarla. */
  alertaId?: number | null;
  tipoAlerta?: string;
  pendiente?: boolean;
  /** Quien puede escribir: registra la licencia y resuelve la alerta. */
  puedeGestionar?: boolean;
  onResolver?: () => void;
  /** Navega (y cierra el panel de alertas). */
  onIr?: (ruta: string) => void;
}

function fecha(iso: string | null | undefined): string {
  return iso ? iso.split("-").reverse().join("-") : "—";
}

/** El control o la atención de una alerta de licencia o receta, con sus documentos de SALUTEM. */
export function DocumentosAlertaDialog({
  titulo,
  caso,
  onOpenChange,
  alertaId = null,
  tipoAlerta,
  pendiente = false,
  puedeGestionar = false,
  onResolver,
  onIr,
}: Props) {
  const esControl = caso?.tipo === "control";
  const cerrarEIr = (ruta: string) => {
    onOpenChange(false);
    onIr?.(ruta);
  };

  return (
    <Dialog open={caso !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>
            Revisa la indicación del médico y los documentos que subió a SALUTEM.
          </DialogDescription>
        </DialogHeader>
        {alertaId !== null && caso !== null && (
          <Gestion
            alertaId={alertaId}
            tipoAlerta={tipoAlerta}
            pendiente={pendiente}
            puedeGestionar={puedeGestionar}
            onResolver={onResolver}
            onIr={cerrarEIr}
          />
        )}
        {caso?.tipo === "control" && <DetalleControl controlId={caso.id} />}
        {caso?.tipo === "atencion" && <DetalleAtencion citaId={caso.id} />}
        <DialogFooter className="gap-2">
          {esControl && (
            <Button type="button" variant="outline" onClick={() => cerrarEIr("/controles")}>
              Ir a Controles
            </Button>
          )}
          {puedeGestionar && pendiente && onResolver && (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                onResolver();
                onOpenChange(false);
              }}
            >
              Marcar como resuelta
            </Button>
          )}
        </DialogFooter>
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

/**
 * Lo que la encargada puede hacer con la alerta sin salir del panel: registrar la licencia
 * que el médico indicó en esa atención (queda resuelta al guardarla), o ir a los fármacos
 * del paciente para registrar la receta.
 */
function Gestion({
  alertaId,
  tipoAlerta,
  pendiente,
  puedeGestionar,
  onResolver,
  onIr,
}: {
  alertaId: number;
  tipoAlerta?: string;
  pendiente: boolean;
  puedeGestionar: boolean;
  onResolver?: () => void;
  onIr: (ruta: string) => void;
}) {
  const { data: ctx, isLoading } = useContextoAlerta(alertaId);
  const esLicencia = tipoAlerta === "licencia_en_control";
  const { data: sugeridas = [] } = useLicenciasSugeridas(esLicencia && ctx?.folio ? ctx.folio : undefined);
  const [registrar, setRegistrar] = useState<{ sugerida: LicenciaSugeridaRead | null } | null>(null);

  if (isLoading) return <p className="text-[13px] text-muted-foreground">Cargando paciente…</p>;
  if (!ctx?.paciente_id) return null;

  const deEstaAtencion = sugeridas.filter((s) => ctx.cita_id != null && s.cita_id === ctx.cita_id);
  const porRegistrar = deEstaAtencion.filter((s) => !s.ya_registrada);

  return (
    <section aria-label="Gestionar alerta" className="space-y-2 rounded-md border p-3 text-[13px]">
      <p>
        Paciente <span className="font-semibold">{ctx.paciente_nombre}</span>
        {ctx.folio ? <span className="text-muted-foreground"> · Folio {ctx.folio}</span> : null}
      </p>

      {esLicencia && ctx.ingreso_id && ctx.folio && (
        <>
          {deEstaAtencion.length > 0 && porRegistrar.length === 0 ? (
            <p className="inline-flex items-center gap-1 text-emerald-700">
              <CheckCircle2 className="size-3.5" /> La licencia de esta atención ya está registrada.
            </p>
          ) : (
            puedeGestionar &&
            pendiente && (
              <div className="flex flex-wrap items-center gap-2">
                {(porRegistrar.length > 0 ? porRegistrar : [null]).map((s, i) => (
                  <Button
                    key={s ? `${s.ficha_clinica_id}-${i}` : "vacia"}
                    type="button"
                    size="sm"
                    onClick={() => setRegistrar({ sugerida: s })}
                  >
                    <FileText className="size-3.5" />
                    {s?.cantidad_dias ? `Registrar licencia (${s.cantidad_dias} días)` : "Registrar licencia"}
                  </Button>
                ))}
              </div>
            )
          )}
          <AltaLicenciaDialog
            folio={ctx.folio}
            ingresoId={ctx.ingreso_id}
            open={registrar !== null}
            onOpenChange={(abierto) => !abierto && setRegistrar(null)}
            sugerencia={registrar?.sugerida ? aSugerencia(registrar.sugerida) : undefined}
            onCreada={() => {
              if (pendiente) onResolver?.();
            }}
          />
        </>
      )}

      {tipoAlerta === "receta_en_control" && (
        <Button
          type="button"
          size="sm"
          variant={puedeGestionar && pendiente ? "default" : "outline"}
          onClick={() => onIr(`/farmacos?paciente=${ctx.paciente_id}`)}
        >
          <Pill className="size-3.5" /> Gestionar en Fármacos
        </Button>
      )}
    </section>
  );
}
