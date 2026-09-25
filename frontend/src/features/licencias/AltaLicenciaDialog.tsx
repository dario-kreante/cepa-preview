/**
 * AltaLicenciaDialog — formulario de alta de licencia médica.
 *
 * ingreso_id / folio resolution
 * ─────────────────────────────
 * The backend `LicenciaCreate` requires `ingreso_id` (integer), not folio.
 * The page works folio-first; `ingreso_id` is resolved as follows:
 *   • `ingresoId` prop is set by the parent (LicenciasPage) when it already
 *     knows the id from the ingreso_id returned by the folio listing.
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

/** Valores leídos de una indicación de SALUTEM. Lo que no trae, lo completa el administrativo. */
export interface SugerenciaLicencia {
  valores: Partial<Omit<LicenciaForm, "ingreso_id">>;
  avisos: string[];
}

interface Props {
  folio: string;
  /** Known ingreso_id from historial. Undefined when no prior licencias exist. */
  ingresoId?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Si viene, el formulario abre precargado y avisa que los datos son sugeridos. */
  sugerencia?: SugerenciaLicencia;
}

export function AltaLicenciaDialog({ folio, ingresoId, open, onOpenChange, sugerencia }: Props) {
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

  // Al abrir con una sugerencia, precarga lo leído; al cerrar, vuelve al formulario vacío.
  useEffect(() => {
    if (open && sugerencia) {
      reset({ ingreso_id: ingresoId, origen: "sistema", ...sugerencia.valores });
    }
    if (!open) {
      reset({ ingreso_id: ingresoId, origen: "sistema" });
    }
  }, [open, reset, ingresoId, sugerencia]);

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
          {sugerencia && (
            <div
              role="note"
              className="rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-[12px] text-amber-900"
            >
              <p className="font-medium">
                Datos sugeridos desde SALUTEM: revisa y completa antes de registrar.
              </p>
              {sugerencia.avisos && sugerencia.avisos.length > 0 && (
                <ul className="mt-1 list-disc pl-4 space-y-0.5">
                  {sugerencia.avisos.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* ingreso_id — hidden when prop is known; visible otherwise */}
          <div>
            <Label htmlFor="ingreso_id">
              N.º de ingreso del paciente{" "}
              {ingresoId === undefined && (
                <span className="text-[11px] text-muted-foreground font-normal">
                  (no se encontró en el historial — ingrésalo manualmente)
                </span>
              )}
            </Label>
            <p className="text-[11.5px] text-muted-foreground mb-1">
              Identificador interno del ingreso al que se asocia esta licencia. No es el RUT ni el
              folio de la licencia médica.
            </p>
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

          {/* Fechas de la licencia — agrupadas para no confundirlas con las del reposo (BUG-2608-04) */}
          <fieldset className="rounded-md border border-border/70 p-3 space-y-3">
            <legend className="px-1 text-[11.5px] font-medium uppercase tracking-wide text-muted-foreground">
              Fechas de la licencia
            </legend>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="fecha_inicio">Fecha inicio de la licencia</Label>
              <Input id="fecha_inicio" type="date" {...register("fecha_inicio")} />
              {errors.fecha_inicio && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.fecha_inicio.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="fecha_termino">Fecha término de la licencia</Label>
              <Input id="fecha_termino" type="date" {...register("fecha_termino")} />
              {errors.fecha_termino && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.fecha_termino.message}</p>
              )}
            </div>
          </div>

          {/* fecha_emision */}
          <div>
            <Label htmlFor="fecha_emision">Fecha de emisión de la licencia</Label>
            <Input id="fecha_emision" type="date" {...register("fecha_emision")} />
            {errors.fecha_emision && (
              <p className="text-[11.5px] text-destructive mt-1">{errors.fecha_emision.message}</p>
            )}
          </div>
          </fieldset>

          {/* Fechas del reposo — par distinto del anterior (BUG-2608-04) */}
          <fieldset className="rounded-md border border-border/70 p-3 space-y-3">
            <legend className="px-1 text-[11.5px] font-medium uppercase tracking-wide text-muted-foreground">
              Fechas del reposo
            </legend>
            <p className="text-[11.5px] text-muted-foreground">
              El período de reposo indicado en la licencia. Puede no coincidir con las fechas de la
              licencia.
            </p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="inicio_reposo">Inicio del reposo</Label>
              <Input id="inicio_reposo" type="date" {...register("inicio_reposo")} />
              {errors.inicio_reposo && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.inicio_reposo.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="fin_reposo">Fin del reposo</Label>
              <Input id="fin_reposo" type="date" {...register("fin_reposo")} />
              {errors.fin_reposo && (
                <p className="text-[11.5px] text-destructive mt-1">{errors.fin_reposo.message}</p>
              )}
            </div>
          </div>
          </fieldset>

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
