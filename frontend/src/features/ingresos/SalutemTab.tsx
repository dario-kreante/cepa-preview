import { useState } from "react";
import { AlertTriangle, CheckCircle2, CloudDownload, FileText, Loader2, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AltaLicenciaDialog, type SugerenciaLicencia } from "@/features/licencias/AltaLicenciaDialog";
import { useImportarSalutem, useLicenciasSugeridas } from "./hooks";
import type { FichaClinicaRead, LicenciaSugeridaRead } from "./api";

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

function periodo(s: LicenciaSugeridaRead): string | null {
  if (s.fecha_inicio && s.fecha_termino) {
    return `Del ${fechaCorta(s.fecha_inicio)} al ${fechaCorta(s.fecha_termino)}`;
  }
  if (s.fecha_termino) return `Hasta el ${fechaCorta(s.fecha_termino)}`;
  if (s.fecha_inicio) return `Desde el ${fechaCorta(s.fecha_inicio)}`;
  return null;
}

/** Lo que la indicación dice pasa al alta; el reposo parte igual que la licencia. */
function aSugerencia(s: LicenciaSugeridaRead): SugerenciaLicencia {
  return {
    valores: {
      tipo_lm: s.tipo_lm ?? undefined,
      tipo_reposo: s.tipo_reposo ?? undefined,
      fecha_inicio: s.fecha_inicio ?? undefined,
      fecha_termino: s.fecha_termino ?? undefined,
      inicio_reposo: s.fecha_inicio ?? undefined,
      fin_reposo: s.fecha_termino ?? undefined,
      cantidad_dias: s.cantidad_dias ?? undefined,
      origen: s.origen,
    },
    avisos: s.avisos,
  };
}

function LicenciasDetectadas({
  folio,
  ingresoId,
  canWrite,
}: {
  folio: string;
  ingresoId: number;
  canWrite: boolean;
}) {
  const { data: sugerencias = [] } = useLicenciasSugeridas(folio);
  const [seleccionada, setSeleccionada] = useState<LicenciaSugeridaRead | null>(null);

  if (sugerencias.length === 0) return null;

  return (
    <section aria-labelledby="licencias-detectadas-titulo" className="space-y-2">
      <div>
        <h3 id="licencias-detectadas-titulo" className="text-[13px] font-semibold">
          Licencias detectadas en SALUTEM
        </h3>
        <p className="text-[11.5px] text-muted-foreground">
          Leídas de las indicaciones médicas. No se registran solas: revisa cada una antes de
          registrarla.
        </p>
      </div>
      <ul className="space-y-2">
        {sugerencias.map((s) => {
          const rango = periodo(s);
          return (
            <li key={`${s.ficha_clinica_id}-${s.fecha_inicio}-${s.fecha_termino}`}>
              <Card>
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-start gap-3">
                    <div className="size-9 rounded-md bg-muted grid place-items-center shrink-0">
                      <FileText className="size-4" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-0.5">
                      <div className="text-[13px] font-semibold">
                        {s.tipo_lm ? `Tipo ${s.tipo_lm}` : "Tipo sin identificar"}
                        {s.tipo_reposo ? ` · ${s.tipo_reposo === "total" ? "Total" : "Parcial"}` : ""}
                        {s.origen === "extra_sistema" ? " · Extra sistema" : ""}
                      </div>
                      <div className="text-[12px] flex flex-wrap gap-x-2">
                        {rango && <span>{rango}</span>}
                        {s.cantidad_dias != null && <span>{`${s.cantidad_dias} días`}</span>}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Atención del {fechaCorta(s.cita_fecha)}
                      </div>
                    </div>
                    {s.ya_registrada ? (
                      <span className="inline-flex items-center gap-1 text-[11.5px] text-emerald-700">
                        <CheckCircle2 className="size-3.5" /> Ya registrada
                      </span>
                    ) : (
                      canWrite && (
                        <Button size="sm" variant="outline" onClick={() => setSeleccionada(s)}>
                          Revisar y registrar
                        </Button>
                      )
                    )}
                  </div>
                  <blockquote className="border-l-2 pl-3 text-[11.5px] text-muted-foreground italic">
                    {s.texto}
                  </blockquote>
                  {s.avisos.map((a) => (
                    <div
                      key={a}
                      className="flex items-start gap-1.5 rounded-md bg-amber-50 px-2 py-1 text-[11.5px] text-amber-900"
                    >
                      <AlertTriangle className="size-3.5 mt-0.5 shrink-0" />
                      {a}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </li>
          );
        })}
      </ul>
      {canWrite && (
        <AltaLicenciaDialog
          folio={folio}
          ingresoId={ingresoId}
          open={seleccionada !== null}
          onOpenChange={(abierto) => {
            if (!abierto) setSeleccionada(null);
          }}
          sugerencia={seleccionada ? aSugerencia(seleccionada) : undefined}
        />
      )}
    </section>
  );
}

export interface SalutemTabProps {
  folio: string;
  ingresoId: number;
  fichas: FichaClinicaRead[];
  cargando: boolean;
  error: boolean;
  canWrite: boolean;
}

export function SalutemTab({ folio, ingresoId, fichas, cargando, error, canWrite }: SalutemTabProps) {
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

      <LicenciasDetectadas folio={folio} ingresoId={ingresoId} canWrite={canWrite} />

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
