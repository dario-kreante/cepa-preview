/**
 * ReportesPage — Reportería operativa (EPIC-09): reportes operativos (CEPA-091),
 * cumplimiento por convenio (CEPA-092), carga laboral (CEPA-093), licencias
 * acumuladas (CEPA-094) y ODAS vencidas (CEPA-097). Solo lectura.
 */
import { useState } from "react";
import { toast } from "sonner";
import { BarChart3, FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn, fmtDate } from "@/lib/utils";
import {
  useReporteCargaLaboral,
  useReporteConvenio,
  useReporteLicencias,
  useReporteOdasVencidas,
  useReporteOperativo,
} from "./hooks";

type Tab = "operativo" | "convenio" | "carga" | "licencias" | "odas";

const TABS: [Tab, string][] = [
  ["operativo", "Operativo"],
  ["convenio", "Convenio"],
  ["carga", "Carga laboral"],
  ["licencias", "Licencias"],
  ["odas", "ODAS vencidas"],
];

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function RangoFiltro({
  desde,
  hasta,
  setDesde,
  setHasta,
  onGenerar,
  pending,
  extra,
}: {
  desde: string;
  hasta: string;
  setDesde: (v: string) => void;
  setHasta: (v: string) => void;
  onGenerar: () => void;
  pending: boolean;
  extra?: React.ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <Label htmlFor="r-desde">Desde *</Label>
          <Input
            id="r-desde"
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="h-9"
          />
        </div>
        <div>
          <Label htmlFor="r-hasta">Hasta *</Label>
          <Input
            id="r-hasta"
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="h-9"
          />
        </div>
        {extra}
        <Button
          size="sm"
          onClick={onGenerar}
          disabled={pending || !desde || !hasta}
          data-testid="btn-generar-reporte"
        >
          <FileText className="size-3.5" />
          {pending ? "Generando…" : "Generar"}
        </Button>
      </div>
    </Card>
  );
}

function Tabla({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: (string | number)[][];
  empty: string;
}) {
  if (rows.length === 0)
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
        <p className="text-[13.5px] text-muted-foreground">{empty}</p>
      </div>
    );
  return (
    <Card className="overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/30 border-b">
              {headers.map((h) => (
                <Th key={h}>{h}</Th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b">
                {r.map((c, j) => (
                  <td key={j} className="px-4 py-2.5 text-[13px]">
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Tab: Operativo ─────────────────────────────────────────────────────────────

function OperativoTab() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const m = useReporteOperativo();

  async function gen() {
    try {
      await m.mutateAsync({ fecha_desde: desde, fecha_hasta: hasta });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-3">
      <RangoFiltro
        desde={desde}
        hasta={hasta}
        setDesde={setDesde}
        setHasta={setHasta}
        onGenerar={gen}
        pending={m.isPending}
      />
      {m.data && (
        <Tabla
          headers={["Fecha", "Programa", "Citas", "Realizadas", "Inasist.", "Anuladas", "Agendadas"]}
          rows={m.data.items.map((it) => [
            fmtDate(it.fecha),
            it.programa ?? "—",
            it.total_citas,
            it.realizadas,
            it.inasistencias,
            it.anuladas,
            it.agendadas,
          ])}
          empty="Sin movimientos en el período."
        />
      )}
    </div>
  );
}

// ── Tab: Convenio ──────────────────────────────────────────────────────────────

function ConvenioTab() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [convenio, setConvenio] = useState("");
  const m = useReporteConvenio();

  async function gen() {
    if (!convenio.trim()) {
      toast.error("Indica el tipo de convenio.");
      return;
    }
    try {
      await m.mutateAsync({
        fecha_desde: desde,
        fecha_hasta: hasta,
        tipo_convenio: convenio.trim(),
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-3">
      <RangoFiltro
        desde={desde}
        hasta={hasta}
        setDesde={setDesde}
        setHasta={setHasta}
        onGenerar={gen}
        pending={m.isPending}
        extra={
          <div>
            <Label htmlFor="convenio">Tipo convenio *</Label>
            <Input
              id="convenio"
              value={convenio}
              onChange={(e) => setConvenio(e.target.value)}
              placeholder="Ej. FONASA"
              className="h-9 w-[160px]"
            />
          </div>
        }
      />
      {m.data && (
        <Tabla
          headers={["Período", "Atenciones", "Inasistencias", "Anulaciones"]}
          rows={m.data.items.map((it) => [
            it.periodo,
            it.total_atenciones,
            it.total_inasistencias,
            it.total_anulaciones,
          ])}
          empty="Sin datos para el convenio en el período."
        />
      )}
    </div>
  );
}

// ── Tab: Carga laboral ─────────────────────────────────────────────────────────

function CargaTab() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const m = useReporteCargaLaboral();

  async function gen() {
    try {
      await m.mutateAsync({ fecha_desde: desde, fecha_hasta: hasta });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-3">
      <RangoFiltro
        desde={desde}
        hasta={hasta}
        setDesde={setDesde}
        setHasta={setHasta}
        onGenerar={gen}
        pending={m.isPending}
      />
      {m.data && (
        <Tabla
          headers={["Profesional", "Especialidad", "Casos", "Atenciones"]}
          rows={m.data.items.map((it) => [
            it.nombre_profesional ?? `N° ${it.profesional_id}`,
            it.especialidad ?? "—",
            it.total_casos,
            it.total_atenciones,
          ])}
          empty="Sin carga registrada en el período."
        />
      )}
    </div>
  );
}

// ── Tab: Licencias ─────────────────────────────────────────────────────────────

function LicenciasTab() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const m = useReporteLicencias();

  async function gen() {
    try {
      await m.mutateAsync({ fecha_desde: desde, fecha_hasta: hasta });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-3">
      <RangoFiltro
        desde={desde}
        hasta={hasta}
        setDesde={setDesde}
        setHasta={setHasta}
        onGenerar={gen}
        pending={m.isPending}
      />
      {m.data && (
        <Tabla
          headers={["Folio", "RUT", "Días acumulados", "Internas", "Externas"]}
          rows={m.data.items.map((it) => [
            it.folio_id,
            it.rut_paciente ?? "—",
            it.total_dias_acumulados,
            it.licencias_internas,
            it.licencias_externas,
          ])}
          empty="Sin licencias acumuladas en el período."
        />
      )}
    </div>
  );
}

// ── Tab: ODAS vencidas ──────────────────────────────────────────────────────────

function OdasTab() {
  const m = useReporteOdasVencidas();

  async function gen() {
    try {
      await m.mutateAsync();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <p className="text-[13px] text-muted-foreground">
            ODAS con fecha de vencimiento pasada a hoy.
          </p>
          <Button size="sm" onClick={gen} disabled={m.isPending} data-testid="btn-generar-reporte">
            <FileText className="size-3.5" />
            {m.isPending ? "Consultando…" : "Consultar"}
          </Button>
        </div>
      </Card>
      {m.data && (
        <Tabla
          headers={["ODA", "Folio", "Registro", "Vencimiento", "Programa", "Región"]}
          rows={m.data.items.map((it) => [
            it.id,
            it.folio_id,
            it.fecha_registro ? fmtDate(it.fecha_registro) : "—",
            fmtDate(it.fecha_vencimiento),
            it.programa ?? "—",
            it.region ?? "—",
          ])}
          empty="No hay ODAS vencidas."
        />
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ReportesPage() {
  const [tab, setTab] = useState<Tab>("operativo");

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <BarChart3 className="size-5 text-muted-foreground" />
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Reportería</h1>
          <p className="text-[13px] text-muted-foreground">
            Reportes operativos y de cumplimiento · solo lectura
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-border">
        {TABS.map(([key, label]) => (
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

      {tab === "operativo" && <OperativoTab />}
      {tab === "convenio" && <ConvenioTab />}
      {tab === "carga" && <CargaTab />}
      {tab === "licencias" && <LicenciasTab />}
      {tab === "odas" && <OdasTab />}
    </div>
  );
}
