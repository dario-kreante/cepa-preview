/**
 * LicenciaControlDialog — form to update licencia + GAF + RECA
 * for an existing control médico.
 *
 * Business rules (RN CEPA-062):
 *   - Cuando tiene_licencia es TRUE, cuatro campos son REQUERIDOS.
 *   - Cuando tiene_licencia es FALSE, licencia fields se envían como null.
 *   - gaf: opcional 0..100.
 *   - estado_reca y observaciones: siempre opcionales.
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
import {
  licenciaControlSchema,
  type LicenciaControlForm,
} from "./licenciaControlSchema";
import { useActualizarLicencia } from "./hooks";
import type { ControlMedicoRead, TipoLicencia, TipoReposo, EstadoReca } from "./api";

// ── Friendly label maps (exhaustive) ─────────────────────────────────────────

export const TIPO_LICENCIA_LABELS: Record<TipoLicencia, string> = {
  "1": "Tipo 1",
  "5": "Tipo 5",
  "6": "Tipo 6",
  "3": "Tipo 3",
  "4": "Tipo 4",
  extra_sistema: "Extra sistema",
};

export const TIPO_REPOSO_LABELS: Record<TipoReposo, string> = {
  total: "Total",
  parcial: "Parcial",
};

export const ESTADO_RECA_LABELS: Record<EstadoReca, string> = {
  pendiente: "Pendiente",
  aprobado: "Aprobado",
  rechazado: "Rechazado",
  en_proceso: "En proceso",
  no_aplica: "No aplica",
};

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  control: ControlMedicoRead;
  ingresoId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function LicenciaControlDialog({
  control,
  ingresoId,
  open,
  onOpenChange,
}: Props) {
  const actualizarMutation = useActualizarLicencia(ingresoId);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LicenciaControlForm>({
    resolver: zodResolver(licenciaControlSchema),
    defaultValues: {
      tiene_licencia: control.tiene_licencia ?? false,
      resumen_termino_lm: control.resumen_termino_lm ?? "",
      total_dias_lm: control.total_dias_lm ?? null,
      tipo_licencia: control.tipo_licencia ?? null,
      tipo_reposo: control.tipo_reposo ?? null,
      gaf: control.gaf ?? null,
      estado_reca: control.estado_reca ?? null,
      observaciones: control.observaciones ?? "",
    },
  });

  const tieneLicencia = watch("tiene_licencia");

  // Reset with the current control's values when dialog opens (reset-on-open)
  useEffect(() => {
    if (open) {
      reset({
        tiene_licencia: control.tiene_licencia ?? false,
        resumen_termino_lm: control.resumen_termino_lm ?? "",
        total_dias_lm: control.total_dias_lm ?? null,
        tipo_licencia: control.tipo_licencia ?? null,
        tipo_reposo: control.tipo_reposo ?? null,
        gaf: control.gaf ?? null,
        estado_reca: control.estado_reca ?? null,
        observaciones: control.observaciones ?? "",
      });
    } else {
      reset({
        tiene_licencia: false,
        resumen_termino_lm: "",
        total_dias_lm: null,
        tipo_licencia: null,
        tipo_reposo: null,
        gaf: null,
        estado_reca: null,
        observaciones: "",
      });
    }
  }, [open, control, reset]);

  async function onSubmit(values: LicenciaControlForm) {
    // Coercion: when tiene_licencia is false, send licencia fields as null
    const licenciaFields = values.tiene_licencia
      ? {
          resumen_termino_lm: values.resumen_termino_lm?.trim() || null,
          total_dias_lm: values.total_dias_lm ?? null,
          tipo_licencia: values.tipo_licencia ?? null,
          tipo_reposo: values.tipo_reposo ?? null,
        }
      : {
          resumen_termino_lm: null,
          total_dias_lm: null,
          tipo_licencia: null,
          tipo_reposo: null,
        };

    try {
      await actualizarMutation.mutateAsync({
        controlId: control.id,
        body: {
          tiene_licencia: values.tiene_licencia,
          ...licenciaFields,
          // Always optional — coerce empty/NaN to null
          gaf: values.gaf != null && !isNaN(values.gaf) ? values.gaf : null,
          estado_reca: values.estado_reca ?? null,
          observaciones: values.observaciones?.trim() || null,
        },
      });
      toast.success("Licencia y RECA actualizados");
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Error al actualizar la licencia del control";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Licencia / RECA</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">
            Registra la licencia médica, GAF y estado RECA del control.
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* tiene_licencia */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="tiene_licencia"
              checked={tieneLicencia}
              onCheckedChange={(checked) =>
                setValue("tiene_licencia", !!checked, { shouldValidate: true })
              }
              aria-label="Tiene licencia médica"
            />
            <Label htmlFor="tiene_licencia" className="mb-0 cursor-pointer">
              Tiene licencia médica
            </Label>
          </div>

          {/* resumen_termino_lm */}
          <div>
            <Label htmlFor="resumen_termino_lm">
              Resumen término licencia médica{" "}
              {tieneLicencia && (
                <span className="text-destructive text-[11px]">*requerido</span>
              )}
            </Label>
            <textarea
              id="resumen_termino_lm"
              rows={2}
              placeholder="Describe el término de la licencia médica"
              {...register("resumen_termino_lm")}
              className="mt-1 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.resumen_termino_lm && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.resumen_termino_lm.message}
              </p>
            )}
          </div>

          {/* total_dias_lm */}
          <div>
            <Label htmlFor="total_dias_lm">
              Total días licencia médica{" "}
              {tieneLicencia && (
                <span className="text-destructive text-[11px]">*requerido</span>
              )}
            </Label>
            <input
              id="total_dias_lm"
              type="number"
              min={1}
              step={1}
              placeholder="Ej: 15"
              {...register("total_dias_lm", {
                setValueAs: (v) => {
                  if (v === "" || v === null || v === undefined) return null;
                  const n = Number(v);
                  return isNaN(n) ? null : n;
                },
              })}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.total_dias_lm && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.total_dias_lm.message}
              </p>
            )}
          </div>

          {/* tipo_licencia */}
          <div>
            <Label htmlFor="tipo_licencia">
              Tipo de licencia{" "}
              {tieneLicencia && (
                <span className="text-destructive text-[11px]">*requerido</span>
              )}
            </Label>
            <select
              id="tipo_licencia"
              {...register("tipo_licencia", {
                setValueAs: (v) => (v === "" ? null : v),
              })}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none"
            >
              <option value="">Selecciona un tipo</option>
              {(
                Object.entries(TIPO_LICENCIA_LABELS) as [
                  TipoLicencia,
                  string,
                ][]
              ).map(([val, label]) => (
                <option key={val} value={val}>
                  {label}
                </option>
              ))}
            </select>
            {errors.tipo_licencia && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.tipo_licencia.message}
              </p>
            )}
          </div>

          {/* tipo_reposo */}
          <div>
            <Label htmlFor="tipo_reposo">
              Tipo de reposo{" "}
              {tieneLicencia && (
                <span className="text-destructive text-[11px]">*requerido</span>
              )}
            </Label>
            <select
              id="tipo_reposo"
              {...register("tipo_reposo", {
                setValueAs: (v) => (v === "" ? null : v),
              })}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none"
            >
              <option value="">Selecciona un tipo</option>
              {(
                Object.entries(TIPO_REPOSO_LABELS) as [TipoReposo, string][]
              ).map(([val, label]) => (
                <option key={val} value={val}>
                  {label}
                </option>
              ))}
            </select>
            {errors.tipo_reposo && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.tipo_reposo.message}
              </p>
            )}
          </div>

          {/* gaf — validate range in zod only; no blocking HTML max */}
          <div>
            <Label htmlFor="gaf">
              GAF{" "}
              <span className="text-muted-foreground font-normal">(opcional, 0–100)</span>
            </Label>
            <input
              id="gaf"
              type="number"
              min={0}
              step={1}
              placeholder="Ej: 65"
              {...register("gaf", {
                setValueAs: (v) => {
                  if (v === "" || v === null || v === undefined) return null;
                  const n = Number(v);
                  return isNaN(n) ? null : n;
                },
              })}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.gaf && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.gaf.message}
              </p>
            )}
          </div>

          {/* estado_reca */}
          <div>
            <Label htmlFor="estado_reca">
              Estado RECA{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <select
              id="estado_reca"
              {...register("estado_reca", {
                setValueAs: (v) => (v === "" ? null : v),
              })}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-[13px] shadow-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none"
            >
              <option value="">Sin estado</option>
              {(
                Object.entries(ESTADO_RECA_LABELS) as [EstadoReca, string][]
              ).map(([val, label]) => (
                <option key={val} value={val}>
                  {label}
                </option>
              ))}
            </select>
            {errors.estado_reca && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.estado_reca.message}
              </p>
            )}
          </div>

          {/* observaciones */}
          <div>
            <Label htmlFor="observaciones">
              Observaciones{" "}
              <span className="text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <textarea
              id="observaciones"
              rows={3}
              placeholder="Observaciones adicionales"
              {...register("observaciones")}
              className="mt-1 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-[13px] ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {errors.observaciones && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.observaciones.message}
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
              {isSubmitting ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
