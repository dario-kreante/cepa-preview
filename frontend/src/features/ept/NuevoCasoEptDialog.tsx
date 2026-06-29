/**
 * NuevoCasoEptDialog — form to create (or edit) a caso EPT.
 *
 * Gate (enforced by the caller):
 *   - ingresoId !== undefined  (a paciente with a resolved ingreso must be selected)
 *   - puedeEscribirEpt(rol)    (Administrativo only)
 *
 * When `initialValues` is provided the dialog operates in edit mode and calls
 * useActualizarCaso instead of useCrearCaso.
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
  casoEptSchema,
  FACTOR_RIESGO_LABELS,
  type CasoEptForm,
  type FactorRiesgo,
} from "./casoEptSchema";
import { useCrearCaso, useActualizarCaso } from "./hooks";
import type { CasoEptRead } from "./api";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (caso: CasoEptRead) => void;
  /** When provided, the dialog is in edit mode (PATCH). */
  initialValues?: CasoEptForm;
  casoId?: number;
}

const DEFAULT_VALUES: CasoEptForm = {
  mes: "",
  fecha_ingreso_ept: "",
  nombre_trabajador: "",
  rut_trabajador: "",
  region_trabajador: "",
  eista: "",
  factor_riesgo: "carga",
  corresponde_ept: true,
  razon_social: "",
  unidad_cargo_horario: "",
};

export function NuevoCasoEptDialog({
  ingresoId,
  open,
  onOpenChange,
  onCreated,
  initialValues,
  casoId,
}: Props) {
  const isEdit = !!initialValues && !!casoId;
  const crearMutation = useCrearCaso();
  const actualizarMutation = useActualizarCaso();

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<CasoEptForm>({
    resolver: zodResolver(casoEptSchema),
    defaultValues: initialValues ?? DEFAULT_VALUES,
  });

  const correspondeEpt = watch("corresponde_ept");

  // Reset form when dialog closes or initialValues change
  useEffect(() => {
    if (open) {
      reset(initialValues ?? DEFAULT_VALUES);
    } else {
      reset(DEFAULT_VALUES);
    }
  }, [open, initialValues, reset]);

  async function onSubmit(values: CasoEptForm) {
    try {
      let caso: CasoEptRead;
      if (isEdit) {
        caso = await actualizarMutation.mutateAsync({
          casoId: casoId!,
          body: {
            mes: values.mes,
            fecha_ingreso_ept: values.fecha_ingreso_ept,
            nombre_trabajador: values.nombre_trabajador,
            rut_trabajador: values.rut_trabajador,
            region_trabajador: values.region_trabajador,
            eista: values.eista,
            factor_riesgo: values.factor_riesgo,
            corresponde_ept: values.corresponde_ept,
            razon_social: values.razon_social || null,
            unidad_cargo_horario: values.unidad_cargo_horario || null,
          },
        });
        toast.success("Caso EPT actualizado");
      } else {
        caso = await crearMutation.mutateAsync({
          ingreso_id: ingresoId,
          mes: values.mes,
          fecha_ingreso_ept: values.fecha_ingreso_ept,
          nombre_trabajador: values.nombre_trabajador,
          rut_trabajador: values.rut_trabajador,
          region_trabajador: values.region_trabajador,
          eista: values.eista,
          factor_riesgo: values.factor_riesgo,
          corresponde_ept: values.corresponde_ept,
          razon_social: values.razon_social || null,
          unidad_cargo_horario: values.unidad_cargo_horario || null,
        });
        toast.success("Caso EPT creado");
      }
      onCreated(caso);
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al guardar el caso EPT";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Editar caso EPT" : "Nuevo caso EPT"}
          </DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {isEdit
              ? "Actualiza los datos del caso EPT."
              : "Registra un nuevo caso de Evaluación de Puesto de Trabajo."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Mes */}
          <div>
            <Label htmlFor="mes">Mes</Label>
            <Input
              id="mes"
              type="text"
              placeholder="Ej. Enero 2026"
              {...register("mes")}
            />
            {errors.mes && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.mes.message}
              </p>
            )}
          </div>

          {/* Fecha ingreso EPT */}
          <div>
            <Label htmlFor="fecha_ingreso_ept">Fecha de ingreso EPT</Label>
            <Input
              id="fecha_ingreso_ept"
              type="date"
              {...register("fecha_ingreso_ept")}
            />
            {errors.fecha_ingreso_ept && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_ingreso_ept.message}
              </p>
            )}
          </div>

          {/* Nombre trabajador */}
          <div>
            <Label htmlFor="nombre_trabajador">Nombre del trabajador</Label>
            <Input
              id="nombre_trabajador"
              type="text"
              placeholder="Ej. María González"
              {...register("nombre_trabajador")}
            />
            {errors.nombre_trabajador && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.nombre_trabajador.message}
              </p>
            )}
          </div>

          {/* RUT trabajador */}
          <div>
            <Label htmlFor="rut_trabajador">RUT del trabajador</Label>
            <Input
              id="rut_trabajador"
              type="text"
              placeholder="Ej. 12.345.678-9"
              {...register("rut_trabajador")}
            />
            {errors.rut_trabajador && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.rut_trabajador.message}
              </p>
            )}
          </div>

          {/* Región trabajador */}
          <div>
            <Label htmlFor="region_trabajador">Región del trabajador</Label>
            <Input
              id="region_trabajador"
              type="text"
              placeholder="Ej. Metropolitana"
              {...register("region_trabajador")}
            />
            {errors.region_trabajador && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.region_trabajador.message}
              </p>
            )}
          </div>

          {/* EISTA */}
          <div>
            <Label htmlFor="eista">EISTA</Label>
            <Input
              id="eista"
              type="text"
              placeholder="Ej. EISTA-001"
              {...register("eista")}
            />
            {errors.eista && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.eista.message}
              </p>
            )}
          </div>

          {/* Factor de riesgo */}
          <div>
            <Label htmlFor="factor_riesgo">Factor de riesgo</Label>
            <select
              id="factor_riesgo"
              {...register("factor_riesgo")}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {(Object.keys(FACTOR_RIESGO_LABELS) as FactorRiesgo[]).map(
                (key) => (
                  <option key={key} value={key}>
                    {FACTOR_RIESGO_LABELS[key]}
                  </option>
                )
              )}
            </select>
            {errors.factor_riesgo && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.factor_riesgo.message}
              </p>
            )}
          </div>

          {/* Corresponde EPT — checkbox */}
          <div className="flex items-center gap-2">
            <input
              id="corresponde_ept"
              type="checkbox"
              checked={correspondeEpt}
              onChange={(e) => setValue("corresponde_ept", e.target.checked)}
              className="h-4 w-4 rounded border-input"
            />
            <Label htmlFor="corresponde_ept" className="mb-0 cursor-pointer">
              Corresponde EPT
            </Label>
          </div>

          {/* Razón social (optional) */}
          <div>
            <Label htmlFor="razon_social">Razón social (opcional)</Label>
            <Input
              id="razon_social"
              type="text"
              placeholder="Nombre de la empresa"
              {...register("razon_social")}
            />
          </div>

          {/* Unidad / Cargo / Horario (optional) */}
          <div>
            <Label htmlFor="unidad_cargo_horario">
              Unidad / Cargo / Horario (opcional)
            </Label>
            <Input
              id="unidad_cargo_horario"
              type="text"
              placeholder="Ej. Bodega · Operario · Turno mañana"
              {...register("unidad_cargo_horario")}
            />
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
              {isSubmitting
                ? "Guardando…"
                : isEdit
                ? "Actualizar caso"
                : "Crear caso EPT"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
