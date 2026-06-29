/**
 * ProximoControlDialog — form to update the próximo control date + agendado flag
 * for an existing control médico.
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
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { proximoControlSchema, type ProximoControlForm } from "./proximoControlSchema";
import { useActualizarProximoControl } from "./hooks";
import type { ControlMedicoRead } from "./api";

interface Props {
  control: ControlMedicoRead;
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProximoControlDialog({
  control,
  ingresoId,
  open,
  onOpenChange,
}: Props) {
  const actualizarMutation = useActualizarProximoControl(ingresoId);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProximoControlForm>({
    resolver: zodResolver(proximoControlSchema),
    defaultValues: {
      proximo_control: control.proximo_control ?? "",
      proximo_agendado: control.proximo_agendado ?? false,
    },
  });

  const agendado = watch("proximo_agendado");

  // Reset form with current control values when dialog opens/closes
  useEffect(() => {
    if (open) {
      reset({
        proximo_control: control.proximo_control ?? "",
        proximo_agendado: control.proximo_agendado ?? false,
      });
    } else {
      reset({
        proximo_control: "",
        proximo_agendado: false,
      });
    }
  }, [open, control, reset]);

  async function onSubmit(values: ProximoControlForm) {
    try {
      await actualizarMutation.mutateAsync({
        controlId: control.id,
        body: {
          proximo_control: values.proximo_control,
          proximo_agendado: values.proximo_agendado,
        },
      });
      toast.success("Próximo control actualizado");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Error al actualizar el próximo control";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Próximo control</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Registra la fecha del próximo control y si ya está agendado.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Fecha próximo control */}
          <div>
            <Label htmlFor="proximo_control">Fecha del próximo control</Label>
            <input
              id="proximo_control"
              type="date"
              {...register("proximo_control")}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.proximo_control && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.proximo_control.message}
              </p>
            )}
          </div>

          {/* Próximo agendado */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="proximo_agendado"
              checked={agendado}
              onCheckedChange={(checked) =>
                setValue("proximo_agendado", !!checked, {
                  shouldValidate: true,
                })
              }
              aria-label="Próximo control agendado"
            />
            <Label htmlFor="proximo_agendado" className="mb-0 cursor-pointer">
              Próximo control agendado
            </Label>
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
