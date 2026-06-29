/**
 * AuditoriaPage — módulo de Auditoría (EPIC-05). Solo lectura.
 *
 * RBAC (RN-2, D1): acceden Coordinacion y Auditor. Administrativo NO accede.
 * Dos vistas:
 *   1. Vista de caso (CEPA-050): búsqueda por RUT / folio / N° siniestro →
 *      vista consolidada de las 4 secciones del caso.
 *   2. Reportes (CEPA-051): filtros (período obligatorio) → tabla + descarga CSV.
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Search, ShieldCheck, Download, FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { normalizarRut } from "@/lib/rut";
import { useAuth } from "@/lib/auth/AuthContext";
import { type Rol } from "@/lib/rbac";
import { useBuscarCasos, useGenerarReporte } from "./hooks";
import { descargarReporteCsv } from "./api";
import { ConsolidadoView } from "./ConsolidadoView";
import { reporteSchema, type ReporteForm } from "./reporteSchema";
import type { CasoConsolidadoRead } from "./api";

type Tab = "casos" | "reportes";

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

// ── Vista de caso (CEPA-050) ──────────────────────────────────────────────────

function VistaCaso() {
  const [campo, setCampo] = useState<"rut" | "folio" | "numero_siniestro">(
    "rut",
  );
  const [valor, setValor] = useState("");
  const [query, setQuery] = useState<{
    rut?: string;
    folio?: string;
    numero_siniestro?: string;
  } | null>(null);
  const [seleccionado, setSeleccionado] = useState<CasoConsolidadoRead | null>(
    null,
  );

  const { data: casos = [], isFetching } = useBuscarCasos(
    query ?? {},
    query !== null,
  );

  function handleBuscar() {
    const v = valor.trim();
    if (!v) return;
    setSeleccionado(null);
    // El backend hace match exacto sobre el RUT normalizado (sin puntos/guion).
    setQuery({ [campo]: campo === "rut" ? normalizarRut(v) : v });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <Label htmlFor="campo">Buscar por</Label>
          <select
            id="campo"
            value={campo}
            onChange={(e) => setCampo(e.target.value as typeof campo)}
            className="flex h-9 w-[160px] rounded-md border border-input bg-transparent px-3 py-1 text-[13px] shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="rut">RUT</option>
            <option value="folio">Folio</option>
            <option value="numero_siniestro">N° siniestro</option>
          </select>
        </div>
        <div className="relative w-[260px]">
          <Search className="absolute left-2.5 top-[30px] size-3.5 text-muted-foreground pointer-events-none" />
          <Label htmlFor="valor">Valor</Label>
          <Input
            id="valor"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleBuscar();
            }}
            placeholder="Ej. 12.345.678-9"
            className="h-9 pl-8 text-[13px]"
            aria-label="Valor de búsqueda"
            data-testid="input-buscar"
          />
        </div>
        <Button
          size="sm"
          onClick={handleBuscar}
          disabled={!valor.trim()}
          data-testid="btn-buscar"
        >
          Buscar
        </Button>
      </div>

      {isFetching && (
        <p className="text-[13px] text-muted-foreground px-1">Buscando…</p>
      )}

      {query && !isFetching && casos.length === 0 && (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">Sin resultados.</p>
        </div>
      )}

      {!isFetching && casos.length > 0 && !seleccionado && (
        <Card className="overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/30 border-b">
                <Th>Folio</Th>
                <Th>Paciente</Th>
                <Th>RUT</Th>
                <Th>N° siniestro</Th>
              </tr>
            </thead>
            <tbody>
              {casos.map((c) => (
                <tr
                  key={c.ingreso_id}
                  onClick={() => setSeleccionado(c)}
                  className="border-b cursor-pointer hover:bg-muted/40 transition-colors"
                  data-testid={`row-caso-${c.ingreso_id}`}
                >
                  <td className="px-4 py-3 font-mono text-[12px]">
                    {c.datos_caso.folio}
                  </td>
                  <td className="px-4 py-3 font-semibold text-[13px]">
                    {c.datos_caso.nombre_completo}
                  </td>
                  <td className="px-4 py-3 font-mono text-[12px]">
                    {c.datos_caso.rut}
                  </td>
                  <td className="px-4 py-3 text-[12.5px]">
                    {c.datos_caso.numero_siniestro ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {seleccionado && (
        <div className="space-y-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSeleccionado(null)}
            data-testid="btn-volver"
          >
            ← Volver a resultados
          </Button>
          <ConsolidadoView caso={seleccionado} />
        </div>
      )}
    </div>
  );
}

// ── Reportes (CEPA-051) ────────────────────────────────────────────────────────

function Reportes() {
  const generar = useGenerarReporte();
  const [descargando, setDescargando] = useState(false);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<ReporteForm>({
    resolver: zodResolver(reporteSchema),
    defaultValues: {
      fecha_desde: "",
      fecha_hasta: "",
      diagnostico: "",
      profesional: "",
      estado_caso: "",
      region: "",
    },
  });

  function toFiltros(v: ReporteForm) {
    return {
      fecha_desde: v.fecha_desde,
      fecha_hasta: v.fecha_hasta,
      diagnostico: v.diagnostico || null,
      profesional: v.profesional || null,
      estado_caso: v.estado_caso || null,
      region: v.region || null,
    };
  }

  async function onSubmit(v: ReporteForm) {
    try {
      await generar.mutateAsync(toFiltros(v));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al generar reporte");
    }
  }

  async function onDescargar() {
    const v = getValues();
    const parsed = reporteSchema.safeParse(v);
    if (!parsed.success) {
      toast.error("Define un período válido antes de descargar.");
      return;
    }
    setDescargando(true);
    try {
      await descargarReporteCsv(toFiltros(parsed.data));
      toast.success("Descarga iniciada");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al descargar CSV");
    } finally {
      setDescargando(false);
    }
  }

  const reporte = generar.data;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="grid grid-cols-2 md:grid-cols-3 gap-3 items-end"
        >
          <div>
            <Label htmlFor="fecha_desde">Desde *</Label>
            <Input id="fecha_desde" type="date" {...register("fecha_desde")} />
            {errors.fecha_desde && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_desde.message}
              </p>
            )}
          </div>
          <div>
            <Label htmlFor="fecha_hasta">Hasta *</Label>
            <Input id="fecha_hasta" type="date" {...register("fecha_hasta")} />
            {errors.fecha_hasta && (
              <p className="text-[11.5px] text-destructive mt-1">
                {errors.fecha_hasta.message}
              </p>
            )}
          </div>
          <div>
            <Label htmlFor="estado_caso">Estado (opcional)</Label>
            <Input id="estado_caso" {...register("estado_caso")} />
          </div>
          <div>
            <Label htmlFor="diagnostico">Diagnóstico (opcional)</Label>
            <Input id="diagnostico" {...register("diagnostico")} />
          </div>
          <div>
            <Label htmlFor="region">Región (opcional)</Label>
            <Input id="region" {...register("region")} />
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={generar.isPending} data-testid="btn-generar">
              <FileText className="size-3.5" />
              {generar.isPending ? "Generando…" : "Generar"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onDescargar}
              disabled={descargando}
              data-testid="btn-descargar"
            >
              <Download className="size-3.5" />
              CSV
            </Button>
          </div>
        </form>
      </Card>

      {reporte && (
        <div className="space-y-2">
          <p className="text-[12.5px] text-muted-foreground px-1">
            {reporte.total} resultado(s) ·{" "}
            {reporte.filtros_aplicados.fecha_desde} a{" "}
            {reporte.filtros_aplicados.fecha_hasta}
          </p>
          {reporte.total === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
              <p className="text-[13.5px] text-muted-foreground">
                Sin casos para los filtros seleccionados.
              </p>
            </div>
          ) : (
            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/30 border-b">
                      <Th>Folio</Th>
                      <Th>Paciente</Th>
                      <Th>Estado</Th>
                      <Th>Dx inicial</Th>
                      <Th>Profesional</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {reporte.filas.map((f) => (
                      <tr key={f.ingreso_id} className="border-b">
                        <td className="px-4 py-3 font-mono text-[12px]">
                          {f.folio}
                        </td>
                        <td className="px-4 py-3 text-[13px]">
                          {f.nombre_completo}
                        </td>
                        <td className="px-4 py-3 text-[12.5px]">
                          {f.estado_caso ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-[12.5px]">
                          {f.diagnostico_inicial ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-[12.5px]">
                          {f.profesional ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function AuditoriaPage() {
  const { rol } = useAuth();
  const [tab, setTab] = useState<Tab>("casos");

  // RBAC: Administrativo no accede al módulo de auditoría (RN-2, D1).
  if ((rol as Rol) === "Administrativo") {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-16 text-center">
        <ShieldCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
        <p className="text-[13.5px] text-muted-foreground">
          El módulo de Auditoría está restringido a perfiles Coordinación y
          Auditor.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Auditoría</h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Vista consolidada de casos y reportes · solo lectura
        </p>
      </div>

      <div className="flex gap-1 border-b border-border">
        {(
          [
            ["casos", "Vista de caso"],
            ["reportes", "Reportes"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            data-testid={`tab-${key}`}
            className={cn(
              "px-4 py-2 text-[13px] font-medium border-b-2 -mb-px transition-colors",
              tab === key
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "casos" ? <VistaCaso /> : <Reportes />}
    </div>
  );
}
