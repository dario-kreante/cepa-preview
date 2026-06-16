/**
 * PlazosEptDialog — create (POST) or edit (PATCH) plazos EPT for an active caso.
 *
 * Gate: callers must only render this when canWrite === true.
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
import { plazosEptSchema, type PlazosEptForm } from "./plazosEptSchema";
import { useCrearPlazos, useActualizarPlazos } from "./hooks";
import type { PlazoEptRead } from "./api";

interface Props {
  casoId: number;
  plazos: PlazoEptRead | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function toDefaultValues(plazos: PlazoEptRead | null): PlazosEptForm {
  if (!plazos) {
    return {
      plazo_informe_ept: undefined,
      plazo_portal_isl: undefined,
      fecha_entrega_isl: undefined,
      fecha_envio: undefined,
    };
  }
  return {
    plazo_informe_ept: plazos.plazo_informe_ept ?? undefined,
    plazo_portal_isl: plazos.plazo_portal_isl ?? undefined,
    fecha_entrega_isl: plazos.fecha_entrega_isl ?? undefined,
    fecha_envio: plazos.fecha_envio ?? undefined,
  };
}

export function PlazosEptDialog({ casoId, plazos, open, onOpenChange }: Props) {
  const crearMutation = useCrearPlazos();
  const actualizarMutation = useActualizarPlazos();

  const isCreate = plazos === null;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PlazosEptForm>({
    resolver: zodResolver(plazosEptSchema),
    defaultValues: toDefaultValues(plazos),
  });

  // Reset form whenever the dialog opens/closes or plazos changes
  useEffect(() => {
    if (open) {
      reset(toDefaultValues(plazos));
    } else {
      reset(toDefaultValues(null));
    }
  }, [open, plazos, reset]);

  async function onSubmit(values: PlazosEptForm) {
    // Coerce undefined optional dates to null for the API
    const nullify = (v: string | undefined): string | null =>
      v === undefined || v === "" ? null : v;

    try {
      if (isCreate) {
        const body = {
          caso_ept_id: casoId,
          plazo_informe_ept: nullify(values.plazo_informe_ept),
          plazo_portal_isl: nullify(values.plazo_portal_isl),
          fecha_entrega_isl: nullify(values.fecha_entrega_isl),
        };
        await crearMutation.mutateAsync({ casoId, body });
        toast.success("Plazos EPT registrados");
      } else {
        const body = {
          plazo_informe_ept: nullify(values.plazo_informe_ept),
          plazo_portal_isl: nullify(values.plazo_portal_isl),
          fecha_entrega_isl: nullify(values.fecha_entrega_isl),
          fecha_envio: nullify(values.fecha_envio),
        };
        await actualizarMutation.mutateAsync({ casoId, body });
        toast.success("Plazos EPT actualizados");
      }
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al guardar los plazos EPT";
      toast.error(msg);
    }
  }

  const inputClass =
    "mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isCreate ? "Registrar plazos EPT" : "Editar plazos EPT"}
          </DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {isCreate
              ? "Registra los plazos EPT para este caso."
              : "Actualiza los plazos EPT."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Plazo informe EPT */}
          <div>
            <Label htmlFor="plazo_informe_ept">Plazo informe EPT</Label>
            <input
              id="plazo_informe_ept"
              type="date"
              {...register("plazo_informe_ept")}
              className={inputClass}
            />
            {errors.plazo_informe_ept && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.plazo_informe_ept.message}
              </p>
            )}
          </div>

          {/* Plazo portal ISL */}
          <div>
            <Label htmlFor="plazo_portal_isl">Plazo portal ISL</Label>
            <input
              id="plazo_portal_isl"
              type="date"
              {...register("plazo_portal_isl")}
              className={inputClass}
            />
            {errors.plazo_portal_isl && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.plazo_portal_isl.message}
              </p>
            )}
          </div>

          {/* Fecha entrega ISL */}
          <div>
            <Label htmlFor="fecha_entrega_isl">Fecha entrega ISL</Label>
            <input
              id="fecha_entrega_isl"
              type="date"
              {...register("fecha_entrega_isl")}
              className={inputClass}
            />
            {errors.fecha_entrega_isl && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_entrega_isl.message}
              </p>
            )}
          </div>

          {/* Fecha envío (only on edit — not in PlazoEptCreate) */}
          {!isCreate && (
            <div>
              <Label htmlFor="fecha_envio">Fecha envío</Label>
              <input
                id="fecha_envio"
                type="date"
                {...register("fecha_envio")}
                className={inputClass}
              />
              {errors.fecha_envio && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.fecha_envio.message}
                </p>
              )}
            </div>
          )}

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
