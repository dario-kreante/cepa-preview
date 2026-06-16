/**
 * NuevaRecetaDialog — form to add a new receta to a registro farmacológico.
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
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { recetaSchema, type RecetaForm } from "./recetaSchema";
import { useCrearReceta } from "./hooks";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NuevaRecetaDialog({ ingresoId, open, onOpenChange }: Props) {
  const crearMutation = useCrearReceta(ingresoId);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RecetaForm>({
    resolver: zodResolver(recetaSchema),
    defaultValues: {
      fecha_emision: "",
      fecha_revision: "",
      fecha_envio: "",
      marca_medicamento: "",
    },
  });

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset({
        fecha_emision: "",
        fecha_revision: "",
        fecha_envio: "",
        marca_medicamento: "",
      });
    }
  }, [open, reset]);

  async function onSubmit(values: RecetaForm) {
    try {
      await crearMutation.mutateAsync({
        fecha_emision: values.fecha_emision,
        fecha_revision: values.fecha_revision,
        fecha_envio: values.fecha_envio || null,
        marca_medicamento: values.marca_medicamento,
      });
      toast.success("Receta registrada");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al registrar la receta";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nueva receta</DialogTitle>
          <DialogDescription className="text-[12.5px]">
            La receta se asociará al registro farmacológico del ingreso.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Marca medicamento */}
          <div>
            <Label htmlFor="marca_medicamento">Marca del medicamento</Label>
            <Input
              id="marca_medicamento"
              type="text"
              placeholder="Ej. Losartán 50mg"
              {...register("marca_medicamento")}
            />
            {errors.marca_medicamento && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.marca_medicamento.message}
              </p>
            )}
          </div>

          {/* Fecha emisión */}
          <div>
            <Label htmlFor="fecha_emision">Fecha de emisión</Label>
            <Input
              id="fecha_emision"
              type="date"
              {...register("fecha_emision")}
            />
            {errors.fecha_emision && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_emision.message}
              </p>
            )}
          </div>

          {/* Fecha revisión */}
          <div>
            <Label htmlFor="fecha_revision">Fecha de revisión</Label>
            <Input
              id="fecha_revision"
              type="date"
              {...register("fecha_revision")}
            />
            {errors.fecha_revision && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_revision.message}
              </p>
            )}
          </div>

          {/* Fecha envío (optional) */}
          <div>
            <Label htmlFor="fecha_envio">
              Fecha de envío al paciente{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input
              id="fecha_envio"
              type="date"
              {...register("fecha_envio")}
            />
            {errors.fecha_envio && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_envio.message}
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
              {isSubmitting ? "Guardando…" : "Guardar receta"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
