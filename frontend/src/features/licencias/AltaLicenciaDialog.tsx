/**
 * AltaLicenciaDialog — formulario de alta de licencia médica.
 *
 * ingreso_id / folio resolution
 * ─────────────────────────────
 * The backend `LicenciaCreate` requires `ingreso_id` (integer), not folio.
 * The page works folio-first; `ingreso_id` is resolved as follows:
 *   • `ingresoId` prop is set by the parent (LicenciasPage) when it already
 *     knows the id from the first full LicenciaRead row in the historial.
 *   • When no licencias exist yet for the folio (new case), `ingresoId` is
 *     undefined and the user must enter it in a visible text field.
 *
 * Enum values (backend exact literals):
 *   tipo_lm:     "1" | "5" | "6"
 *   tipo_reposo: "total" | "parcial"
 *   origen:      "sistema" | "extra_sistema"
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
import { licenciaSchema, type LicenciaForm, TIPO_LM_VALUES, TIPO_REPOSO_VALUES, ORIGEN_VALUES } from "./licenciaSchema";
import { useCrearLicencia } from "./hooks";
import type { LicenciaCreate } from "./api";

const TIPO_LM_LABELS: Record<string, string> = {
  "1": "Tipo 1",
  "5": "Tipo 5",
  "6": "Tipo 6",
};
const TIPO_REPOSO_LABELS: Record<string, string> = {
  total: "Total",
  parcial: "Parcial",
};
const ORIGEN_LABELS: Record<string, string> = {
  sistema: "Sistema (CEPA)",
  extra_sistema: "Extra-sistema",
};

interface Props {
  folio: string;
  /** Known ingreso_id from historial. Undefined when no prior licencias exist. */
  ingresoId?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AltaLicenciaDialog({ folio, ingresoId, open, onOpenChange }: Props) {
  const crearMutation = useCrearLicencia(folio);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LicenciaForm>({
    resolver: zodResolver(licenciaSchema),
    defaultValues: {
      ingreso_id: ingresoId,
      origen: "sistema",
    },
  });

  // Sync ingresoId prop into form when it changes (e.g. page resolves it asynchronously)
  useEffect(() => {
    if (ingresoId !== undefined) {
      setValue("ingreso_id", ingresoId);
    }
  }, [ingresoId, setValue]);

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      reset({ ingreso_id: ingresoId, origen: "sistema" });
    }
  }, [open, reset, ingresoId]);

  async function onSubmit(values: LicenciaForm) {
    // Coerce optional string fields to null for the backend contract
    const body: LicenciaCreate = {
      ingreso_id: values.ingreso_id,
      tipo_lm: values.tipo_lm,
      tipo_reposo: values.tipo_reposo,
      fecha_inicio: values.fecha_inicio,
      fecha_termino: values.fecha_termino,
      fecha_emision: values.fecha_emision,
      inicio_reposo: values.inicio_reposo,
      fin_reposo: values.fin_reposo,
      cantidad_dias: values.cantidad_dias,
      diagnostico: values.diagnostico,
      origen: values.origen,
      folio_lm: values.folio_lm?.trim() || undefined,
      indicacion_reposo: values.indicacion_reposo?.trim() || undefined,
    };

    try {
      await crearMutation.mutateAsync(body);
      toast.success("Licencia registrada correctamente");
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al registrar la licencia";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva licencia médica</DialogTitle>
          <p className="text-[12.5px] text-muted-foreground">Folio: {folio}</p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* ingreso_id — hidden when prop is known; visible otherwise */}
          <div>
            <Label htmlFor="ingreso_id">
              Ingreso ID{" "}
              {ingresoId === undefined && (
                <span className="text-[11px] text-muted-foreground font-normal">
                  (no encontrado en historial — ingresa manualmente)
                </span>
              )}
            </Label>
            <Input
              id="ingreso_id"
              type="number"
              readOnly={ingresoId !== undefined}
              className={ingresoId !== undefined ? "bg-muted/30 cursor-not-allowed" : ""}
              {...register("ingreso_id", { valueAsNumber: true })}
            />
            {errors.ingreso_id && (
              <p className="text-[11.5px] text-destructive mt-1">{errors.ingreso_id.message}</p>
            )}
          </div>

          {/* Row: tipo_lm + tipo_reposo */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="tipo_lm">Tipo de licencia</Label>
              <select
                id="tipo_lm"
                className="flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
                {...register("tipo_lm")}
              >
                <option value="">Seleccionar…</option>
                {TIPO_LM_VALUES.map((v) => (
                  <option key={v} value={v}>{TIPO_LM_LABELS[v]}</option>
                ))}
              </select>
              {errors.tipo_lm && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.tipo_lm.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="tipo_reposo">Tipo de reposo</Label>
              <select
                id="tipo_reposo"
                className="flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
                {...register("tipo_reposo")}
              >
                <option value="">Seleccionar…</option>
                {TIPO_REPOSO_VALUES.map((v) => (
                  <option key={v} value={v}>{TIPO_REPOSO_LABELS[v]}</option>
                ))}
              </select>
              {errors.tipo_reposo && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.tipo_reposo.message}</p>
              )}
            </div>
          </div>

          {/* Row: fecha_inicio + fecha_termino */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="fecha_inicio">Fecha inicio</Label>
              <Input id="fecha_inicio" type="date" {...register("fecha_inicio")} />
              {errors.fecha_inicio && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.fecha_inicio.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="fecha_termino">Fecha término</Label>
              <Input id="fecha_termino" type="date" {...register("fecha_termino")} />
              {errors.fecha_termino && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.fecha_termino.message}</p>
              )}
            </div>
          </div>

          {/* fecha_emision */}
          <div>
            <Label htmlFor="fecha_emision">Fecha emisión</Label>
            <Input id="fecha_emision" type="date" {...register("fecha_emision")} />
            {errors.fecha_emision && (
              <p className="text-[11.5px] text-destructive mt-1">{errors.fecha_emision.message}</p>
            )}
          </div>

          {/* Row: inicio_reposo + fin_reposo */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="inicio_reposo">Inicio reposo</Label>
              <Input id="inicio_reposo" type="date" {...register("inicio_reposo")} />
              {errors.inicio_reposo && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.inicio_reposo.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="fin_reposo">Fin reposo</Label>
              <Input id="fin_reposo" type="date" {...register("fin_reposo")} />
              {errors.fin_reposo && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.fin_reposo.message}</p>
              )}
            </div>
          </div>

          {/* Row: cantidad_dias + folio_lm */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="cantidad_dias">Cantidad de días</Label>
              <Input
                id="cantidad_dias"
                type="number"
                min={1}
                {...register("cantidad_dias", { valueAsNumber: true })}
              />
              {errors.cantidad_dias && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.cantidad_dias.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="folio_lm">
                Folio LM{" "}
                <span className="text-[11px] text-muted-foreground font-normal">(opcional)</span>
              </Label>
              <Input id="folio_lm" type="text" placeholder="Ej. LM-00123" {...register("folio_lm")} />
            </div>
          </div>

          {/* diagnostico */}
          <div>
            <Label htmlFor="diagnostico">Diagnóstico</Label>
            <Input id="diagnostico" type="text" {...register("diagnostico")} />
            {errors.diagnostico && (
              <p className="text-[11.5px] text-destructive mt-1">{errors.diagnostico.message}</p>
            )}
          </div>

          {/* indicacion_reposo (optional) */}
          <div>
            <Label htmlFor="indicacion_reposo">
              Indicación de reposo{" "}
              <span className="text-[11px] text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input id="indicacion_reposo" type="text" {...register("indicacion_reposo")} />
          </div>

          {/* origen */}
          <div>
            <Label htmlFor="origen">Origen</Label>
            <select
              id="origen"
              className="flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("origen")}
            >
              {ORIGEN_VALUES.map((v) => (
                <option key={v} value={v}>{ORIGEN_LABELS[v]}</option>
              ))}
            </select>
            {errors.origen && (
              <p className="text-[11.5px] text-destructive mt-1">{errors.origen.message}</p>
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
              {isSubmitting ? "Registrando…" : "Registrar licencia"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
