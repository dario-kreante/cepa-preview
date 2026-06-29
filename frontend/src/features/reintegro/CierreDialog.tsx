/**
 * CierreDialog — actualiza el estado de reintegro y registra el cierre (CEPA-042).
 * La coherencia (cierre total requiere alta, fechas) la valida el backend.
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
  cierreSchema,
  ESTADO_REINTEGRO_LABELS,
  ESTADO_REINTEGRO_VALUES,
  TIPO_ALTA_LABELS,
  TIPO_ALTA_VALUES,
  type CierreForm,
} from "./cierreSchema";
import { useRegistrarCierre } from "./hooks";
import type { CasoReintegroRead } from "./api";

interface Props {
  caso: CasoReintegroRead;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

export function CierreDialog({ caso, open, onOpenChange }: Props) {
  const cierreMutation = useRegistrarCierre();

  const initial: CierreForm = {
    estado_reintegro: caso.estado_reintegro,
    fecha_reintegro: caso.fecha_reintegro ?? "",
    remitido_isl: caso.remitido_isl,
    alta_medica: caso.alta_medica,
    fecha_alta_medica: caso.fecha_alta_medica ?? "",
    alta_psicologica: caso.alta_psicologica,
    fecha_alta_psico: caso.fecha_alta_psico ?? "",
    tipo_alta: caso.tipo_alta ?? "",
    observaciones: caso.observaciones ?? "",
  };

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CierreForm>({
    resolver: zodResolver(cierreSchema),
    defaultValues: initial,
  });

  const altaMedica = watch("alta_medica");
  const altaPsico = watch("alta_psicologica");

  useEffect(() => {
    if (open) reset(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, caso.id]);

  async function onSubmit(values: CierreForm) {
    try {
      await cierreMutation.mutateAsync({
        casoId: caso.id,
        body: {
          estado_reintegro: values.estado_reintegro,
          fecha_reintegro: values.fecha_reintegro || null,
          remitido_isl: values.remitido_isl,
          alta_medica: values.alta_medica,
          fecha_alta_medica: values.fecha_alta_medica || null,
          alta_psicologica: values.alta_psicologica,
          fecha_alta_psico: values.fecha_alta_psico || null,
          tipo_alta: values.tipo_alta ? values.tipo_alta : null,
          observaciones: values.observaciones || null,
        },
      });
      toast.success("Cierre de reintegro actualizado");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al registrar el cierre");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Reintegro y cierre del caso</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Estado de reintegro, altas y observaciones de cierre.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="estado_reintegro">Estado de reintegro</Label>
              <select
                id="estado_reintegro"
                className={selectCls}
                {...register("estado_reintegro")}
              >
                {ESTADO_REINTEGRO_VALUES.map((v) => (
                  <option key={v} value={v}>
                    {ESTADO_REINTEGRO_LABELS[v]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="fecha_reintegro">Fecha reintegro</Label>
              <Input
                id="fecha_reintegro"
                type="date"
                {...register("fecha_reintegro")}
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-[13px] font-medium">
            <input type="checkbox" {...register("remitido_isl")} />
            Remitido a ISL
          </label>

          {/* Alta médica */}
          <div className="space-y-2 rounded-md border border-border p-3">
            <label className="flex items-center gap-2 text-[13px] font-medium">
              <input type="checkbox" {...register("alta_medica")} />
              Alta médica
            </label>
            {altaMedica && (
              <div>
                <Label htmlFor="fecha_alta_medica">Fecha alta médica</Label>
                <Input
                  id="fecha_alta_medica"
                  type="date"
                  {...register("fecha_alta_medica")}
                />
              </div>
            )}
          </div>

          {/* Alta psicológica */}
          <div className="space-y-2 rounded-md border border-border p-3">
            <label className="flex items-center gap-2 text-[13px] font-medium">
              <input type="checkbox" {...register("alta_psicologica")} />
              Alta psicológica
            </label>
            {altaPsico && (
              <div>
                <Label htmlFor="fecha_alta_psico">Fecha alta psicológica</Label>
                <Input
                  id="fecha_alta_psico"
                  type="date"
                  {...register("fecha_alta_psico")}
                />
              </div>
            )}
          </div>

          <div>
            <Label htmlFor="tipo_alta">Tipo de alta (opcional)</Label>
            <select id="tipo_alta" className={selectCls} {...register("tipo_alta")}>
              <option value="">—</option>
              {TIPO_ALTA_VALUES.map((v) => (
                <option key={v} value={v}>
                  {TIPO_ALTA_LABELS[v]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="observaciones">Observaciones (opcional)</Label>
            <Input id="observaciones" {...register("observaciones")} />
          </div>

          {errors.estado_reintegro && (
            <p className="text-[11.5px] text-destructive">
              {errors.estado_reintegro.message}
            </p>
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
              {isSubmitting ? "Guardando…" : "Guardar cierre"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
