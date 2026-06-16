/**
 * IslLicenciaDialog — updates the ISL tracking fields of a licencia médica.
 *
 * Fields:
 *   envio_isl     — required Select (EstadoEnvioISL: pendiente | enviado | rechazado)
 *   fecha_envio_isl — optional date Input
 *   eeag_gaf       — optional number Input, validated in range 1–100
 *   observaciones  — optional textarea
 *
 * On submit: PATCH /api/v1/licencias/{id}/isl { envio_isl, fecha_envio_isl?, eeag_gaf?, observaciones? }
 */
import { useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useActualizarISL } from "./hooks";
import type { LicenciaISLUpdate } from "./api";

// Real EstadoEnvioISL values from the OpenAPI spec
type EstadoEnvioISL = "pendiente" | "enviado" | "rechazado";

const ENVIO_ISL_OPTIONS: { value: EstadoEnvioISL; label: string }[] = [
  { value: "pendiente", label: "Pendiente" },
  { value: "enviado", label: "Enviado" },
  { value: "rechazado", label: "Rechazado" },
];

interface Props {
  licenciaId: number;
  folio: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormState {
  envio_isl: EstadoEnvioISL | "";
  fecha_envio_isl: string;
  eeag_gaf: string;
  observaciones: string;
}

const INITIAL_FORM: FormState = {
  envio_isl: "",
  fecha_envio_isl: "",
  eeag_gaf: "",
  observaciones: "",
};

export function IslLicenciaDialog({ licenciaId, folio, open, onOpenChange }: Props) {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [eeagError, setEeagError] = useState<string | null>(null);

  const islMutation = useActualizarISL(folio);

  function handleChange<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (key === "eeag_gaf") setEeagError(null);
  }

  function validate(): boolean {
    if (form.eeag_gaf !== "") {
      const n = Number(form.eeag_gaf);
      if (!Number.isInteger(n) || n < 1 || n > 100) {
        setEeagError("Debe estar entre 1 y 100");
        return false;
      }
    }
    return true;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const body: LicenciaISLUpdate = {
      envio_isl: form.envio_isl as EstadoEnvioISL,
      fecha_envio_isl: form.fecha_envio_isl || null,
      eeag_gaf: form.eeag_gaf !== "" ? Number(form.eeag_gaf) : null,
      observaciones: form.observaciones || null,
    };

    try {
      await islMutation.mutateAsync({ id: licenciaId, body });
      toast.success("Envío ISL actualizado");
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "No se pudo actualizar el ISL";
      toast.error(msg);
    }
  }

  const isSubmitting = islMutation.isPending;
  const canSubmit = form.envio_isl !== "" && !isSubmitting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Actualizar envío ISL</DialogTitle>
          <DialogDescription className="text-[12.5px]">
            Registra el estado de envío al ISL para esta licencia.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {/* envio_isl */}
          <div>
            <Label htmlFor="envio-isl-select">Estado de envío ISL</Label>
            <select
              id="envio-isl-select"
              value={form.envio_isl}
              onChange={(e) => handleChange("envio_isl", e.target.value as EstadoEnvioISL | "")}
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Seleccionar…</option>
              {ENVIO_ISL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* fecha_envio_isl */}
          <div>
            <Label htmlFor="fecha-envio-isl">
              Fecha de envío{" "}
              <span className="text-[11px] text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <Input
              id="fecha-envio-isl"
              type="date"
              value={form.fecha_envio_isl}
              onChange={(e) => handleChange("fecha_envio_isl", e.target.value)}
              className="mt-1"
            />
          </div>

          {/* eeag_gaf */}
          <div>
            <Label htmlFor="eeag-gaf">
              GAF/EEAG{" "}
              <span className="text-[11px] text-muted-foreground font-normal">(opcional, 1–100)</span>
            </Label>
            <Input
              id="eeag-gaf"
              aria-label="GAF/EEAG"
              type="number"
              value={form.eeag_gaf}
              onChange={(e) => handleChange("eeag_gaf", e.target.value)}
              placeholder="Ej. 75"
              className="mt-1"
            />
            {eeagError && (
              <p className="text-[11.5px] text-destructive mt-1">{eeagError}</p>
            )}
          </div>

          {/* observaciones */}
          <div>
            <Label htmlFor="isl-obs">
              Observaciones{" "}
              <span className="text-[11px] text-muted-foreground font-normal">(opcional)</span>
            </Label>
            <textarea
              id="isl-obs"
              value={form.observaciones}
              onChange={(e) => handleChange("observaciones", e.target.value)}
              rows={3}
              placeholder="Notas adicionales…"
              className="mt-1 flex w-full rounded-md border border-input bg-card px-3 py-2 text-[13px] shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {isSubmitting ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
