/**
 * EvaluacionControlDialog — edita la evaluación clínica de un control médico:
 * tiempo estimado de tratamiento, proyección de reintegro laboral y factores de
 * riesgo acogidos. En los controles de SALUTEM llegan precargados desde la ficha.
 *
 * Gate (must be enforced by the caller):
 *   - canWrite === true  (writers only)
 */
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  EVALUACION_LABELS,
  evaluacionControlSchema,
  type EvaluacionControlForm,
} from "./evaluacionControlSchema";
import { useActualizarEvaluacion } from "./hooks";
import type { ControlMedicoRead } from "./api";

interface Props {
  control: ControlMedicoRead;
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function valoresDe(control: ControlMedicoRead): EvaluacionControlForm {
  return {
    tiempo_estimado_tratamiento: control.tiempo_estimado_tratamiento ?? "",
    proyeccion_reintegro: control.proyeccion_reintegro ?? "",
    factores_riesgo: control.factores_riesgo ?? "",
  };
}

const VACIO: EvaluacionControlForm = {
  tiempo_estimado_tratamiento: "",
  proyeccion_reintegro: "",
  factores_riesgo: "",
};

export function EvaluacionControlDialog({
  control,
  ingresoId,
  open,
  onOpenChange,
}: Props) {
  const actualizarMutation = useActualizarEvaluacion(ingresoId);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EvaluacionControlForm>({
    resolver: zodResolver(evaluacionControlSchema),
    defaultValues: valoresDe(control),
  });

  // Reset with the current control's values when dialog opens (reset-on-open)
  useEffect(() => {
    reset(open ? valoresDe(control) : VACIO);
  }, [open, control, reset]);

  async function onSubmit(values: EvaluacionControlForm) {
    try {
      await actualizarMutation.mutateAsync({
        controlId: control.id,
        body: {
          tiempo_estimado_tratamiento: values.tiempo_estimado_tratamiento.trim() || null,
          proyeccion_reintegro: values.proyeccion_reintegro.trim() || null,
          factores_riesgo: values.factores_riesgo.trim() || null,
        },
      });
      toast.success("Evaluación actualizada");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al actualizar la evaluación";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Evaluación clínica</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {control.origen === "SALUTEM"
              ? "Datos leídos de la ficha en SALUTEM. Si la ficha cambia, el sync los vuelve a traer."
              : "Tiempo estimado de tratamiento, proyección de reintegro y factores de riesgo."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div>
            <Label htmlFor="tiempo_estimado_tratamiento">
              {EVALUACION_LABELS.tiempo_estimado_tratamiento}{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input
              id="tiempo_estimado_tratamiento"
              placeholder="Ej: 3 meses"
              {...register("tiempo_estimado_tratamiento")}
              className="mt-1 h-9 text-[13px]"
            />
            {errors.tiempo_estimado_tratamiento && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.tiempo_estimado_tratamiento.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="proyeccion_reintegro">
              {EVALUACION_LABELS.proyeccion_reintegro}{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input
              id="proyeccion_reintegro"
              placeholder="Ej: Más de 1 mes"
              {...register("proyeccion_reintegro")}
              className="mt-1 h-9 text-[13px]"
            />
            {errors.proyeccion_reintegro && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.proyeccion_reintegro.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="factores_riesgo">
              {EVALUACION_LABELS.factores_riesgo}{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <textarea
              id="factores_riesgo"
              rows={3}
              placeholder="Factores de riesgo psicosocial acogidos"
              {...register("factores_riesgo")}
              className="mt-1 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.factores_riesgo && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.factores_riesgo.message}
              </p>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
