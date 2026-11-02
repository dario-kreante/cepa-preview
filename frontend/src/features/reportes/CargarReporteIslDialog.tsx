/**
 * CargarReporteIslDialog — carga del «Reporte Prestador» del portal ISL (QA-004).
 *
 * Flujo: elegir archivo → previsualizar (dry run, no guarda) → confirmar → resumen.
 * Solo para roles escritores (Administrativo, Coordinacion); el caller lo controla.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtDate } from "@/lib/utils";
import { useImportarReporteIsl } from "./hooks";
import type { OdaImportResumen } from "./api";

const MAX_BYTES = 10 * 1024 * 1024;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function Dato({ label, valor, testId }: { label: string; valor: number; testId: string }) {
  return (
    <div className="rounded-md border border-border px-3 py-2">
      <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="text-[18px] font-semibold tabular-nums" data-testid={testId}>
        {valor}
      </p>
    </div>
  );
}

function Resumen({ r }: { r: OdaImportResumen }) {
  return (
    <div className="space-y-3 text-[13px]" data-testid="resumen-importacion">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <Dato label="Filas leídas" valor={r.filas_leidas} testId="dato-filas" />
        <Dato label={r.dry_run ? "Se crearán" : "Creadas"} valor={r.creadas} testId="dato-creadas" />
        <Dato
          label={r.dry_run ? "Se actualizarán" : "Actualizadas"}
          valor={r.actualizadas}
          testId="dato-actualizadas"
        />
        <Dato label="Sin cambios" valor={r.sin_cambios} testId="dato-sin-cambios" />
        <Dato label="Sin paciente" valor={r.sin_paciente.length} testId="dato-sin-paciente" />
        <Dato label="Con error" valor={r.errores.length} testId="dato-errores" />
      </div>
      <p data-testid="por-vencer">
        <strong>{r.por_vencer_paciente_activo}</strong> ODA(S) de pacientes activos vencen en los
        próximos {r.ventana_dias} días.
      </p>
      {r.por_vencer.length > 0 && (
        <ul className="max-h-28 overflow-auto rounded-md border border-border px-3 py-2">
          {r.por_vencer.map((p) => (
            <li key={p.oda_id}>
              Folio {p.folio} · orden {p.numero_orden} · vence {fmtDate(p.fecha_vencimiento)}
            </li>
          ))}
        </ul>
      )}
      {r.sin_paciente.length > 0 && (
        <details>
          <summary className="cursor-pointer font-medium">
            Órdenes sin paciente en SIGE ({r.sin_paciente.length}): revisa el N° de siniestro
          </summary>
          <ul className="mt-1 max-h-40 overflow-auto rounded-md border border-border px-3 py-2">
            {r.sin_paciente.map((s) => (
              <li key={`${s.fila}-${s.numero_orden}`}>
                Fila {s.fila} · orden {s.numero_orden}
                {s.tipo_orden ? ` (${s.tipo_orden})` : ""} · siniestro {s.numero_siniestro ?? "—"}
              </li>
            ))}
          </ul>
        </details>
      )}
      {r.errores.length > 0 && (
        <details open>
          <summary className="cursor-pointer font-medium text-destructive">
            Filas con error ({r.errores.length})
          </summary>
          <ul className="mt-1 max-h-40 overflow-auto rounded-md border border-border px-3 py-2">
            {r.errores.map((e) => (
              <li key={e.fila}>
                Fila {e.fila}: {e.motivo}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export function CargarReporteIslDialog({ open, onOpenChange }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [preview, setPreview] = useState<OdaImportResumen | null>(null);
  const [final, setFinal] = useState<OdaImportResumen | null>(null);
  const m = useImportarReporteIsl();

  function cerrar(v: boolean) {
    if (!v) {
      setArchivo(null);
      setPreview(null);
      setFinal(null);
      m.reset();
    }
    onOpenChange(v);
  }

  function elegir(f: File | null) {
    setPreview(null);
    setFinal(null);
    if (f && f.size > MAX_BYTES) {
      toast.error("El archivo supera el máximo de 10 MB.");
      setArchivo(null);
      return;
    }
    setArchivo(f);
  }

  async function ejecutar(dryRun: boolean) {
    if (!archivo) return;
    try {
      const r = await m.mutateAsync({ file: archivo, dryRun });
      if (dryRun) setPreview(r);
      else {
        setFinal(r);
        toast.success("Reporte ISL cargado");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  const resumen = final ?? preview;

  return (
    <Dialog open={open} onOpenChange={cerrar}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Cargar reporte ISL</DialogTitle>
          <DialogDescription>
            Sube el «Reporte Prestador» (.xlsx) descargado del portal ISL. Cada orden se asocia al
            paciente por N° de siniestro (o RUT del trabajador) y actualiza la vigencia de su ODA.
            Las alertas de vencimiento solo consideran pacientes activos.
          </DialogDescription>
        </DialogHeader>

        {!final && (
          <div className="space-y-1.5">
            <Label htmlFor="archivo-isl">Archivo</Label>
            <Input
              id="archivo-isl"
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              data-testid="input-archivo-isl"
              onChange={(e) => elegir(e.target.files?.[0] ?? null)}
            />
          </div>
        )}

        {resumen && (
          <>
            <p className="text-[13px] font-medium" data-testid="estado-importacion">
              {final ? "Carga completada." : "Previsualización: aún no se ha guardado nada."}
            </p>
            <Resumen r={resumen} />
          </>
        )}

        <DialogFooter>
          {final ? (
            <Button onClick={() => cerrar(false)} data-testid="btn-cerrar-isl">
              Cerrar
            </Button>
          ) : preview ? (
            <>
              <Button variant="outline" onClick={() => setPreview(null)} disabled={m.isPending}>
                Volver
              </Button>
              <Button
                onClick={() => ejecutar(false)}
                disabled={m.isPending}
                data-testid="btn-confirmar-isl"
              >
                {m.isPending ? "Guardando…" : "Confirmar carga"}
              </Button>
            </>
          ) : (
            <Button
              onClick={() => ejecutar(true)}
              disabled={!archivo || m.isPending}
              data-testid="btn-previsualizar-isl"
            >
              <Upload className="size-3.5" />
              {m.isPending ? "Leyendo…" : "Previsualizar"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
