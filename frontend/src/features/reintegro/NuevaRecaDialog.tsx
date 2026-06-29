/**
 * NuevaRecaDialog — registra (o edita) la RECA del caso de reintegro (CEPA-041).
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
  recaSchema,
  TIPO_RECA_LABELS,
  TIPO_RECA_VALUES,
  type RecaForm,
} from "./recaSchema";
import { useActualizarReca, useCrearReca } from "./hooks";
import type { RecaRead } from "./api";

interface Props {
  casoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialValues?: RecaForm;
  isEdit?: boolean;
}

const DEFAULT_VALUES: RecaForm = {
  fecha_reca: "",
  tipo_reca: "AT",
  numero_reca: "",
  razon_social: "",
  riesgos_calificados: "",
  solicita_medidas: false,
  detalle_medidas: "",
  fecha_medidas: "",
  verifica_medidas: false,
  detalle_verificacion: "",
  fecha_verificacion: "",
};

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

export function NuevaRecaDialog({
  casoId,
  open,
  onOpenChange,
  initialValues,
  isEdit = false,
}: Props) {
  const crearMutation = useCrearReca();
  const actualizarMutation = useActualizarReca();

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RecaForm>({
    resolver: zodResolver(recaSchema),
    defaultValues: initialValues ?? DEFAULT_VALUES,
  });

  const solicita = watch("solicita_medidas");
  const verifica = watch("verifica_medidas");

  useEffect(() => {
    reset(open ? (initialValues ?? DEFAULT_VALUES) : DEFAULT_VALUES);
  }, [open, initialValues, reset]);

  async function onSubmit(values: RecaForm) {
    const body = {
      fecha_reca: values.fecha_reca,
      tipo_reca: values.tipo_reca,
      numero_reca: values.numero_reca,
      razon_social: values.razon_social,
      riesgos_calificados: values.riesgos_calificados || null,
      solicita_medidas: values.solicita_medidas,
      detalle_medidas: values.detalle_medidas || null,
      fecha_medidas: values.fecha_medidas || null,
      verifica_medidas: values.verifica_medidas,
      detalle_verificacion: values.detalle_verificacion || null,
      fecha_verificacion: values.fecha_verificacion || null,
    };
    try {
      let reca: RecaRead;
      if (isEdit) {
        reca = await actualizarMutation.mutateAsync({ casoId, body });
        toast.success("RECA actualizada");
      } else {
        reca = await crearMutation.mutateAsync({ casoId, body });
        toast.success("RECA registrada");
      }
      void reca;
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar la RECA");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar RECA" : "Registrar RECA"}</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Resolución de Calificación y medidas correctivas.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="fecha_reca">Fecha RECA</Label>
              <Input id="fecha_reca" type="date" {...register("fecha_reca")} />
              {errors.fecha_reca && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.fecha_reca.message}
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="tipo_reca">Tipo RECA</Label>
              <select id="tipo_reca" className={selectCls} {...register("tipo_reca")}>
                {TIPO_RECA_VALUES.map((v) => (
                  <option key={v} value={v}>
                    {TIPO_RECA_LABELS[v]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="numero_reca">Número RECA</Label>
              <Input id="numero_reca" {...register("numero_reca")} />
              {errors.numero_reca && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.numero_reca.message}
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="razon_social">Razón social</Label>
              <Input id="razon_social" {...register("razon_social")} />
              {errors.razon_social && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.razon_social.message}
                </p>
              )}
            </div>
          </div>

          <div>
            <Label htmlFor="riesgos_calificados">
              Riesgos calificados (opcional)
            </Label>
            <Input
              id="riesgos_calificados"
              {...register("riesgos_calificados")}
            />
          </div>

          {/* Medidas */}
          <div className="space-y-2 rounded-md border border-border p-3">
            <label className="flex items-center gap-2 text-[13px] font-medium">
              <input type="checkbox" {...register("solicita_medidas")} />
              Solicita medidas correctivas
            </label>
            {solicita && (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <Label htmlFor="detalle_medidas">Detalle medidas</Label>
                  <Input id="detalle_medidas" {...register("detalle_medidas")} />
                  {errors.detalle_medidas && (
                    <p className="text-[11.5px] text-destructive mt-1">
                      {errors.detalle_medidas.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="fecha_medidas">Fecha medidas</Label>
                  <Input id="fecha_medidas" type="date" {...register("fecha_medidas")} />
                </div>
              </div>
            )}
          </div>

          {/* Verificación */}
          <div className="space-y-2 rounded-md border border-border p-3">
            <label className="flex items-center gap-2 text-[13px] font-medium">
              <input type="checkbox" {...register("verifica_medidas")} />
              Verifica medidas
            </label>
            {verifica && (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <Label htmlFor="detalle_verificacion">
                    Detalle verificación
                  </Label>
                  <Input
                    id="detalle_verificacion"
                    {...register("detalle_verificacion")}
                  />
                  {errors.detalle_verificacion && (
                    <p className="text-[11.5px] text-destructive mt-1">
                      {errors.detalle_verificacion.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="fecha_verificacion">Fecha verificación</Label>
                  <Input
                    id="fecha_verificacion"
                    type="date"
                    {...register("fecha_verificacion")}
                  />
                </div>
              </div>
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
              {isSubmitting ? "Guardando…" : isEdit ? "Actualizar RECA" : "Registrar RECA"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
