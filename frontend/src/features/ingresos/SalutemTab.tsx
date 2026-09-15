import { useState } from "react";
import { CloudDownload, Loader2, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useImportarSalutem } from "./hooks";
import type { FichaClinicaRead } from "./api";

function texto(v: unknown): string | null {
  return typeof v === "string" && v.trim() !== "" ? v : null;
}

/** "2025-01-22" → "22/01/2025"; cualquier otro formato se muestra tal cual. */
function fechaCorta(v: unknown): string {
  const s = texto(v);
  if (!s) return "Sin fecha";
  const [y, m, d] = s.slice(0, 10).split("-");
  return y && m && d ? `${d}/${m}/${y}` : s;
}

function mensajeImportacion(n: number): string {
  if (n === 0) return "SALUTEM no tiene atenciones nuevas para este ingreso.";
  if (n === 1) return "Se importó 1 atención desde SALUTEM.";
  return `Se importaron ${n} atenciones desde SALUTEM.`;
}

export interface SalutemTabProps {
  folio: string;
  fichas: FichaClinicaRead[];
  cargando: boolean;
  error: boolean;
  canWrite: boolean;
}

export function SalutemTab({ folio, fichas, cargando, error, canWrite }: SalutemTabProps) {
  const importar = useImportarSalutem(folio);
  const [resultado, setResultado] = useState<string | null>(null);

  function onImportar() {
    setResultado(null);
    importar.mutate(undefined, {
      onSuccess: (nuevas) => setResultado(mensajeImportacion(nuevas.length)),
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12px] text-muted-foreground max-w-md">
          Atenciones registradas en SALUTEM dentro del período de este ingreso. La consulta es de
          solo lectura: el CEPA nunca modifica datos en SALUTEM.
        </p>
        {canWrite && (
          <Button size="sm" onClick={onImportar} disabled={importar.isPending}>
            {importar.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <CloudDownload className="size-3.5" />
            )}
            Importar desde SALUTEM
          </Button>
        )}
      </div>

      {resultado && (
        <p role="status" className="rounded-md bg-muted px-3 py-2 text-[12.5px]">
          {resultado}
        </p>
      )}
      {importar.isError && (
        <p
          role="alert"
          className="rounded-md bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive"
        >
          {importar.error.message}
        </p>
      )}

      {cargando ? (
        <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
          <Loader2 className="size-4 animate-spin" />
          <span className="text-[13px]">Cargando…</span>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-[13px] text-destructive">
          No se pudieron cargar las atenciones de SALUTEM.
        </div>
      ) : fichas.length === 0 ? (
        <div className="text-center py-12 text-[13px] text-muted-foreground">
          Aún no hay atenciones importadas desde SALUTEM.
        </div>
      ) : (
        <div className="space-y-2">
          {fichas.map((f) => {
            const c = f.contenido;
            return (
              <Card key={f.id}>
                <CardContent className="p-4 flex items-center gap-4">
                  <div className="size-10 rounded-md bg-[oklch(0.94_0.05_230)] text-[oklch(0.42_0.12_230)] grid place-items-center shrink-0">
                    <Stethoscope className="size-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-[13px]">
                      {texto(c.especialidadNombre) ?? "Atención SALUTEM"}
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      {fechaCorta(c.citaFecha)}
                      {texto(c.profesionalNombre) ? ` · ${texto(c.profesionalNombre)}` : ""}
                      {texto(c.sucursalNombre) ? ` · ${texto(c.sucursalNombre)}` : ""}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
