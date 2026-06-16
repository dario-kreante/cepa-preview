/**
 * NuevoSeguimientoDialog — form to add a seguimiento de tratamiento.
 *
 * Gate (must be enforced by the caller):
 *   - registro !== null  (registro must already exist)
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
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { seguimientoSchema, type SeguimientoForm } from "./seguimientoSchema";
import { useCrearSeguimiento } from "./hooks";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NuevoSeguimientoDialog({ ingresoId, open, onOpenChange }: Props) {
  const crearMutation = useCrearSeguimiento(ingresoId);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SeguimientoForm>({
    resolver: zodResolver(seguimientoSchema),
    defaultValues: {
      disminucion_farmacos: false,
      plan_disminucion: "",
      cambio_esquema: false,
      detalle_cambio: "",
      observaciones: "",
    },
  });

  const disminucion = watch("disminucion_farmacos");
  const cambioEsquema = watch("cambio_esquema");

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset({
        disminucion_farmacos: false,
        plan_disminucion: "",
        cambio_esquema: false,
        detalle_cambio: "",
        observaciones: "",
      });
    }
  }, [open, reset]);

  async function onSubmit(values: SeguimientoForm) {
    try {
      await crearMutation.mutateAsync({
        disminucion_farmacos: values.disminucion_farmacos,
        plan_disminucion: values.plan_disminucion?.trim() || null,
        cambio_esquema: values.cambio_esquema,
        detalle_cambio: values.detalle_cambio?.trim() || null,
        observaciones: values.observaciones?.trim() || null,
      });
      toast.success("Seguimiento registrado");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al registrar el seguimiento";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nuevo seguimiento de tratamiento</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Registra el estado del tratamiento farmacológico del ingreso.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Disminución de fármacos */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Checkbox
                id="disminucion_farmacos"
                checked={disminucion}
                onCheckedChange={(checked) =>
                  setValue("disminucion_farmacos", !!checked, { shouldValidate: true })
                }
                aria-label="Disminución de fármacos"
              />
              <Label htmlFor="disminucion_farmacos" className="cursor-pointer">
                Disminución de fármacos
              </Label>
            </div>

            {/* Plan de disminución — always rendered; required when flag is true */}
            <div className="pl-6">
              <Label htmlFor="plan_disminucion">
                Plan de disminución{" "}
                {disminucion && (
                  <span className="text-destructive text-[11px]">*requerido</span>
                )}
              </Label>
              <textarea
                id="plan_disminucion"
                rows={2}
                placeholder="Describe el plan de disminución"
                {...register("plan_disminucion")}
                className="mt-1 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
              {errors.plan_disminucion && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.plan_disminucion.message}
                </p>
              )}
            </div>
          </div>

          {/* Cambio de esquema */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Checkbox
                id="cambio_esquema"
                checked={cambioEsquema}
                onCheckedChange={(checked) =>
                  setValue("cambio_esquema", !!checked, { shouldValidate: true })
                }
                aria-label="Cambio de esquema"
              />
              <Label htmlFor="cambio_esquema" className="cursor-pointer">
                Cambio de esquema
              </Label>
            </div>

            {/* Detalle del cambio — always rendered; required when flag is true */}
            <div className="pl-6">
              <Label htmlFor="detalle_cambio">
                Detalle del cambio{" "}
                {cambioEsquema && (
                  <span className="text-destructive text-[11px]">*requerido</span>
                )}
              </Label>
              <textarea
                id="detalle_cambio"
                rows={2}
                placeholder="Describe el cambio de esquema"
                {...register("detalle_cambio")}
                className="mt-1 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
              {errors.detalle_cambio && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.detalle_cambio.message}
                </p>
              )}
            </div>
          </div>

          {/* Observaciones (opcional) */}
          <div>
            <Label htmlFor="observaciones">
              Observaciones{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <textarea
              id="observaciones"
              rows={3}
              placeholder="Observaciones adicionales"
              {...register("observaciones")}
              className="mt-1 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.observaciones && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.observaciones.message}
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
              {isSubmitting ? "Guardando…" : "Guardar seguimiento"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
