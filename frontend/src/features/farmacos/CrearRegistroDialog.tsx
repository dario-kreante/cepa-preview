/**
 * CrearRegistroDialog — form to create a nuevo registro farmacológico
 * for an ingreso that does not yet have one.
 *
 * Gate (must be enforced by the caller):
 *   - registro === null  (no registro yet)
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
  registroSchema,
  type RegistroForm,
  ESTADO_VALUES,
  ESTADO_LABELS,
} from "./registroSchema";
import { useCrearRegistro } from "./hooks";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CrearRegistroDialog({ ingresoId, open, onOpenChange }: Props) {
  const crearMutation = useCrearRegistro();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RegistroForm>({
    resolver: zodResolver(registroSchema),
    defaultValues: {
      medico_tratante: "",
      estado_farmacologico: "activo",
      antecedentes_previos: "",
      tratamiento_previo: "",
    },
  });

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset({
        medico_tratante: "",
        estado_farmacologico: "activo",
        antecedentes_previos: "",
        tratamiento_previo: "",
      });
    }
  }, [open, reset]);

  async function onSubmit(values: RegistroForm) {
    try {
      await crearMutation.mutateAsync({
        ingreso_id: ingresoId,
        medico_tratante: values.medico_tratante,
        estado_farmacologico: values.estado_farmacologico,
        antecedentes_previos: values.antecedentes_previos || null,
        tratamiento_previo: values.tratamiento_previo || null,
      });
      toast.success("Registro farmacológico creado");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al crear el registro";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Crear registro farmacológico</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Se creará un nuevo registro farmacológico para este ingreso.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Médico tratante */}
          <div>
            <Label htmlFor="medico_tratante">Médico tratante</Label>
            <Input
              id="medico_tratante"
              type="text"
              placeholder="Ej. Dra. Carmen López"
              {...register("medico_tratante")}
            />
            {errors.medico_tratante && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.medico_tratante.message}
              </p>
            )}
          </div>

          {/* Estado farmacológico */}
          <div>
            <Label htmlFor="estado_farmacologico">Estado farmacológico</Label>
            <select
              id="estado_farmacologico"
              className="flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("estado_farmacologico")}
            >
              <option value="">Seleccionar…</option>
              {ESTADO_VALUES.map((v) => (
                <option key={v} value={v}>
                  {ESTADO_LABELS[v]}
                </option>
              ))}
            </select>
            {errors.estado_farmacologico && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.estado_farmacologico.message}
              </p>
            )}
          </div>

          {/* Antecedentes previos (optional) */}
          <div>
            <Label htmlFor="antecedentes_previos">
              Antecedentes previos{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input
              id="antecedentes_previos"
              type="text"
              placeholder="Ej. Hipertensión arterial"
              {...register("antecedentes_previos")}
            />
            {errors.antecedentes_previos && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.antecedentes_previos.message}
              </p>
            )}
          </div>

          {/* Tratamiento previo (optional) */}
          <div>
            <Label htmlFor="tratamiento_previo">
              Tratamiento previo{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input
              id="tratamiento_previo"
              type="text"
              placeholder="Ej. Enalapril 10mg"
              {...register("tratamiento_previo")}
            />
            {errors.tratamiento_previo && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.tratamiento_previo.message}
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
              {isSubmitting ? "Creando…" : "Crear registro"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
