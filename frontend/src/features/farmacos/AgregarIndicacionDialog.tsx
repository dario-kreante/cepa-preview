/**
 * AgregarIndicacionDialog — form to add a new medication indication to the
 * esquema farmacológico of a given ingreso.
 *
 * The dialog trigger/button must be disabled or hidden when:
 *   - there is no registro (you can't add indicaciones without a registro)
 *   - the user is not a writer (!puedeEscribir)
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
import { Checkbox } from "@/components/ui/checkbox";
import {
  indicacionSchema,
  type IndicacionForm,
  FRECUENCIA_VALUES,
  FRECUENCIA_LABELS,
} from "./indicacionSchema";
import { useAgregarIndicacion } from "./hooks";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AgregarIndicacionDialog({ ingresoId, open, onOpenChange }: Props) {
  const agregarMutation = useAgregarIndicacion(ingresoId);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<IndicacionForm>({
    resolver: zodResolver(indicacionSchema),
    defaultValues: {
      medicamento: "",
      dosis: "",
      frecuencia: undefined,
      extra_sistema: false,
    },
  });

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset({
        medicamento: "",
        dosis: "",
        frecuencia: undefined,
        extra_sistema: false,
      });
    }
  }, [open, reset]);

  const extraSistemaValue = watch("extra_sistema");

  async function onSubmit(values: IndicacionForm) {
    try {
      await agregarMutation.mutateAsync({
        medicamento: values.medicamento,
        dosis: values.dosis,
        frecuencia: values.frecuencia,
        extra_sistema: values.extra_sistema,
      });
      toast.success("Indicación agregada al esquema");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al agregar la indicación";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Agregar indicación</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            La indicación se agregará al esquema farmacológico del ingreso.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Medicamento */}
          <div>
            <Label htmlFor="medicamento">Medicamento</Label>
            <Input
              id="medicamento"
              type="text"
              placeholder="Ej. Enalapril"
              {...register("medicamento")}
            />
            {errors.medicamento && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.medicamento.message}
              </p>
            )}
          </div>

          {/* Dosis */}
          <div>
            <Label htmlFor="dosis">Dosis</Label>
            <Input
              id="dosis"
              type="text"
              placeholder="Ej. 10 mg"
              {...register("dosis")}
            />
            {errors.dosis && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.dosis.message}
              </p>
            )}
          </div>

          {/* Frecuencia */}
          <div>
            <Label htmlFor="frecuencia">Frecuencia</Label>
            <select
              id="frecuencia"
              className="flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("frecuencia")}
            >
              <option value="">Seleccionar…</option>
              {FRECUENCIA_VALUES.map((v) => (
                <option key={v} value={v}>
                  {FRECUENCIA_LABELS[v]}
                </option>
              ))}
            </select>
            {errors.frecuencia && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.frecuencia.message}
              </p>
            )}
          </div>

          {/* Extra sistema */}
          <div className="flex items-center gap-3">
            <Checkbox
              id="extra_sistema"
              checked={extraSistemaValue}
              onCheckedChange={(checked) =>
                setValue("extra_sistema", checked === true)
              }
            />
            <Label htmlFor="extra_sistema" className="mb-0 cursor-pointer font-normal">
              Extra sistema
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
              {isSubmitting ? "Agregando…" : "Agregar indicación"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
