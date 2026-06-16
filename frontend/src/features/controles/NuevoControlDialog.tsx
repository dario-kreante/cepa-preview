/**
 * NuevoControlDialog — form to register a new control médico for an ingreso.
 *
 * Gate (must be enforced by the caller):
 *   - ingresoId !== undefined  (a paciente with a resolved ingreso must be selected)
 *   - canWrite === true        (writers only)
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
import { controlSchema, type ControlForm } from "./controlSchema";
import { useCrearControl } from "./hooks";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NuevoControlDialog({ ingresoId, open, onOpenChange }: Props) {
  const crearMutation = useCrearControl();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ControlForm>({
    resolver: zodResolver(controlSchema),
    defaultValues: {
      fecha_control: "",
      medico_tratante: "",
      region_derivacion: "",
    },
  });

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset({
        fecha_control: "",
        medico_tratante: "",
        region_derivacion: "",
      });
    }
  }, [open, reset]);

  async function onSubmit(values: ControlForm) {
    try {
      await crearMutation.mutateAsync({
        ingreso_id: ingresoId,
        fecha_control: values.fecha_control,
        medico_tratante: values.medico_tratante.trim(),
        region_derivacion: values.region_derivacion.trim(),
      });
      toast.success("Control médico registrado");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al registrar el control médico";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nuevo control médico</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            La semana del control se calculará automáticamente según la fecha de ingreso.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Fecha control */}
          <div>
            <Label htmlFor="fecha_control">Fecha del control</Label>
            <Input
              id="fecha_control"
              type="date"
              {...register("fecha_control")}
            />
            {errors.fecha_control && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_control.message}
              </p>
            )}
          </div>

          {/* Médico tratante */}
          <div>
            <Label htmlFor="medico_tratante">Médico tratante</Label>
            <Input
              id="medico_tratante"
              type="text"
              placeholder="Ej. Dr. Juan Martínez"
              {...register("medico_tratante")}
            />
            {errors.medico_tratante && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.medico_tratante.message}
              </p>
            )}
          </div>

          {/* Región de derivación */}
          <div>
            <Label htmlFor="region_derivacion">Región de derivación</Label>
            <Input
              id="region_derivacion"
              type="text"
              placeholder="Ej. Metropolitana"
              {...register("region_derivacion")}
            />
            {errors.region_derivacion && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.region_derivacion.message}
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
              {isSubmitting ? "Guardando…" : "Guardar control"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
