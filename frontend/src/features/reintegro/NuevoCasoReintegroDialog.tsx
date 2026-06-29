/**
 * NuevoCasoReintegroDialog — alta / edición de un caso de reintegro (CEPA-040).
 * Gate (caller): ingresoId definido + puedeEscribir(rol).
 * Con `initialValues` + `casoId` opera en modo edición (PATCH).
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
  casoReintegroSchema,
  SEXO_LABELS,
  SEXO_VALUES,
  TIPO_DERIVACION_VALUES,
  type CasoReintegroForm,
} from "./casoReintegroSchema";
import { useActualizarCaso, useCrearCaso } from "./hooks";
import type { CasoReintegroRead } from "./api";

interface Props {
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (caso: CasoReintegroRead) => void;
  /** Cuando se provee junto con casoId, el diálogo edita (PATCH). */
  initialValues?: CasoReintegroForm;
  casoId?: number;
}

const DEFAULT_VALUES: CasoReintegroForm = {
  rut: "",
  nombre: "",
  tipo_derivacion: "DIEP",
  fecha_caso: "",
  sexo: "F",
  edad: 1,
  region: "",
  comuna: "",
  rubro_empleador: "",
};

const selectCls =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-ring";

export function NuevoCasoReintegroDialog({
  ingresoId,
  open,
  onOpenChange,
  onSaved,
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
    formState: { errors, isSubmitting },
  } = useForm<CasoReintegroForm>({
    resolver: zodResolver(casoReintegroSchema),
    defaultValues: initialValues ?? DEFAULT_VALUES,
  });

  useEffect(() => {
    reset(open ? (initialValues ?? DEFAULT_VALUES) : DEFAULT_VALUES);
  }, [open, initialValues, reset]);

  async function onSubmit(values: CasoReintegroForm) {
    try {
      let caso: CasoReintegroRead;
      if (isEdit) {
        caso = await actualizarMutation.mutateAsync({
          casoId: casoId!,
          body: {
            nombre: values.nombre,
            tipo_derivacion: values.tipo_derivacion,
            fecha_caso: values.fecha_caso,
            sexo: values.sexo,
            edad: values.edad,
            region: values.region,
            comuna: values.comuna || null,
            rubro_empleador: values.rubro_empleador || null,
          },
        });
        toast.success("Caso de reintegro actualizado");
      } else {
        caso = await crearMutation.mutateAsync({
          ingreso_id: ingresoId,
          rut: values.rut,
          nombre: values.nombre,
          tipo_derivacion: values.tipo_derivacion,
          fecha_caso: values.fecha_caso,
          sexo: values.sexo,
          edad: values.edad,
          region: values.region,
          comuna: values.comuna || null,
          rubro_empleador: values.rubro_empleador || null,
        });
        toast.success("Caso de reintegro creado");
      }
      onSaved(caso);
      onOpenChange(false);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Error al guardar el caso",
      );
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Editar caso de reintegro" : "Nuevo caso de reintegro"}
          </DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {isEdit
              ? "Actualiza los datos del caso de reintegro."
              : "Registra un nuevo caso de seguimiento de reintegro laboral."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div>
            <Label htmlFor="rut">RUT</Label>
            <Input
              id="rut"
              placeholder="Ej. 12.345.678-9"
              disabled={isEdit}
              {...register("rut")}
            />
            {errors.rut && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.rut.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="nombre">Nombre</Label>
            <Input
              id="nombre"
              placeholder="Ej. María González"
              {...register("nombre")}
            />
            {errors.nombre && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.nombre.message}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="tipo_derivacion">Tipo de derivación</Label>
            <select
              id="tipo_derivacion"
              className={selectCls}
              {...register("tipo_derivacion")}
            >
              {TIPO_DERIVACION_VALUES.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
            {errors.tipo_derivacion && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.tipo_derivacion.message}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="fecha_caso">Fecha del caso</Label>
              <Input id="fecha_caso" type="date" {...register("fecha_caso")} />
              {errors.fecha_caso && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.fecha_caso.message}
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="edad">Edad</Label>
              <Input id="edad" type="number" min={1} max={130} {...register("edad")} />
              {errors.edad && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.edad.message}
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="sexo">Sexo</Label>
              <select id="sexo" className={selectCls} {...register("sexo")}>
                {SEXO_VALUES.map((v) => (
                  <option key={v} value={v}>
                    {SEXO_LABELS[v]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="region">Región</Label>
              <Input
                id="region"
                placeholder="Ej. Maule"
                {...register("region")}
              />
              {errors.region && (
                <p className="text-[11.5px] text-destructive mt-1">
                  {errors.region.message}
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="comuna">Comuna (opcional)</Label>
              <Input id="comuna" {...register("comuna")} />
            </div>
            <div>
              <Label htmlFor="rubro_empleador">Rubro empleador (opcional)</Label>
              <Input id="rubro_empleador" {...register("rubro_empleador")} />
            </div>
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
                  : "Crear caso"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
