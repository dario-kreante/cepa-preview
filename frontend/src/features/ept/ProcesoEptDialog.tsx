/**
 * ProcesoEptDialog — create (POST) or edit (PATCH) the proceso EPT
 * for an active caso.
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
import { Checkbox } from "@/components/ui/checkbox";
import { procesoEptSchema, type ProcesoEptForm } from "./procesoEptSchema";
import { useCrearProceso, useActualizarProceso } from "./hooks";
import type { ProcesoEptRead } from "./api";

interface Props {
  casoId: number;
  proceso: ProcesoEptRead | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function toDefaultValues(proceso: ProcesoEptRead | null): ProcesoEptForm {
  if (!proceso) {
    return {
      plazo_evid_denunciante: undefined,
      plazo_insumos_empresa: undefined,
      hay_testigos: false,
      testigos_cantidad: 0,
      num_entrevistas: 0,
      insumos_eista: "",
      doc_incumplimiento: "",
      observaciones: "",
    };
  }
  return {
    plazo_evid_denunciante: proceso.plazo_evid_denunciante ?? undefined,
    plazo_insumos_empresa: proceso.plazo_insumos_empresa ?? undefined,
    hay_testigos: proceso.hay_testigos,
    testigos_cantidad: proceso.testigos_cantidad,
    num_entrevistas: proceso.num_entrevistas,
    insumos_eista: proceso.insumos_eista ?? "",
    doc_incumplimiento: proceso.doc_incumplimiento ?? "",
    observaciones: proceso.observaciones ?? "",
  };
}

export function ProcesoEptDialog({ casoId, proceso, open, onOpenChange }: Props) {
  const crearMutation = useCrearProceso();
  const actualizarMutation = useActualizarProceso();

  const isCreate = proceso === null;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProcesoEptForm>({
    resolver: zodResolver(procesoEptSchema),
    defaultValues: toDefaultValues(proceso),
  });

  const hayTestigos = watch("hay_testigos");

  // Reset form whenever the dialog opens/closes or proceso changes
  useEffect(() => {
    if (open) {
      reset(toDefaultValues(proceso));
    } else {
      reset(toDefaultValues(null));
    }
  }, [open, proceso, reset]);

  async function onSubmit(values: ProcesoEptForm) {
    // Coerce empty optional strings to null for the API
    const nullify = (v: string | undefined): string | null =>
      v === "" || v === undefined ? null : v;

    const body = {
      plazo_evid_denunciante: nullify(values.plazo_evid_denunciante),
      plazo_insumos_empresa: nullify(values.plazo_insumos_empresa),
      hay_testigos: values.hay_testigos,
      testigos_cantidad: values.testigos_cantidad,
      num_entrevistas: values.num_entrevistas,
      insumos_eista: nullify(values.insumos_eista),
      doc_incumplimiento: nullify(values.doc_incumplimiento),
      observaciones: nullify(values.observaciones),
    };

    try {
      if (isCreate) {
        await crearMutation.mutateAsync({
          casoId,
          body: { ...body, caso_ept_id: casoId },
        });
        toast.success("Proceso EPT registrado");
      } else {
        await actualizarMutation.mutateAsync({ casoId, body });
        toast.success("Proceso EPT actualizado");
      }
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Error al guardar el proceso EPT";
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
            {isCreate ? "Registrar proceso EPT" : "Editar proceso EPT"}
          </DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            {isCreate
              ? "Registra los datos del proceso EPT para este caso."
              : "Actualiza los datos del proceso EPT."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* Plazo evidencia denunciante */}
          <div>
            <Label htmlFor="plazo_evid_denunciante">
              Plazo evidencia denunciante
            </Label>
            <input
              id="plazo_evid_denunciante"
              type="date"
              {...register("plazo_evid_denunciante")}
              className={inputClass}
            />
            {errors.plazo_evid_denunciante && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.plazo_evid_denunciante.message}
              </p>
            )}
          </div>

          {/* Plazo insumos empresa */}
          <div>
            <Label htmlFor="plazo_insumos_empresa">
              Plazo insumos empresa
            </Label>
            <input
              id="plazo_insumos_empresa"
              type="date"
              {...register("plazo_insumos_empresa")}
              className={inputClass}
            />
            {errors.plazo_insumos_empresa && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.plazo_insumos_empresa.message}
              </p>
            )}
          </div>

          {/* Hay testigos */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="hay_testigos"
              checked={hayTestigos}
              onCheckedChange={(checked) =>
                setValue("hay_testigos", !!checked, { shouldValidate: true })
              }
              aria-label="Hay testigos"
            />
            <Label htmlFor="hay_testigos" className="mb-0 cursor-pointer">
              Hay testigos
            </Label>
          </div>

          {/* Testigos cantidad */}
          <div>
            <Label htmlFor="testigos_cantidad">Cantidad de testigos</Label>
            <input
              id="testigos_cantidad"
              type="number"
              {...register("testigos_cantidad", {
                setValueAs: (v: string) =>
                  v === "" ? 0 : parseInt(v, 10),
              })}
              className={inputClass}
            />
            {errors.testigos_cantidad && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.testigos_cantidad.message}
              </p>
            )}
          </div>

          {/* Num entrevistas */}
          <div>
            <Label htmlFor="num_entrevistas">N° de entrevistas</Label>
            <input
              id="num_entrevistas"
              type="number"
              {...register("num_entrevistas", {
                setValueAs: (v: string) =>
                  v === "" ? 0 : parseInt(v, 10),
              })}
              className={inputClass}
            />
            {errors.num_entrevistas && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.num_entrevistas.message}
              </p>
            )}
          </div>

          {/* Insumos EISTA */}
          <div>
            <Label htmlFor="insumos_eista">Insumos EISTA</Label>
            <input
              id="insumos_eista"
              type="text"
              {...register("insumos_eista")}
              className={inputClass}
            />
          </div>

          {/* Doc incumplimiento */}
          <div>
            <Label htmlFor="doc_incumplimiento">Doc. incumplimiento</Label>
            <input
              id="doc_incumplimiento"
              type="text"
              {...register("doc_incumplimiento")}
              className={inputClass}
            />
          </div>

          {/* Observaciones */}
          <div>
            <Label htmlFor="observaciones">Observaciones</Label>
            <textarea
              id="observaciones"
              {...register("observaciones")}
              rows={3}
              className="mt-1 flex w-full rounded-md border border-input bg-background px-3 py-2 text-[13px] shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
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
              {isSubmitting ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
