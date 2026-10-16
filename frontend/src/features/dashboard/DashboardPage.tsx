/**
 * DashboardPage — dashboard operativo de inicio.
 *
 * Actividad del período desde la copia de SALUTEM (atenciones, inasistencias,
 * anulaciones, agenda próxima) y lo que hay que gestionar hoy en el SIGE
 * (licencias, ODAs, borradores sin folio, EPT, alertas). Solo lectura.
 *
 * Antes leía la tabla local `cita`, que no la llena ningún proceso: las cifras de
 * atenciones salían siempre en 0.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Ban,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  FileClock,
  FileText,
  UserPlus,
  UserRoundSearch,
  Users,
  UserX,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AreaTrend } from "@/components/charts/AreaTrend";
import { BarSimple } from "@/components/charts/BarSimple";
import { DonutChart } from "@/components/charts/DonutChart";
import { TIPO_LABELS } from "@/features/config-alertas/api";
import { useDashboardOperativo } from "./hooks";
import type { DashboardOperativo } from "./api";

type Conteo = DashboardOperativo["alertas_por_tipo"][number];

const ETIQUETAS_ALERTA: Record<string, string> = {
  ...TIPO_LABELS,
  paciente_pendiente_folio: "Paciente pendiente de folio",
};

const PRESETS = [
  { dias: 7, label: "7 días" },
  { dias: 30, label: "30 días" },
  { dias: 90, label: "90 días" },
];

function isoLocal(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function haceDias(dias: number): { fecha_desde: string; fecha_hasta: string } {
  const hasta = new Date();
  const desde = new Date();
  desde.setDate(hasta.getDate() - (dias - 1));
  return { fecha_desde: isoLocal(desde), fecha_hasta: isoLocal(hasta) };
}

/** "2026-10-12" → "12-10-2026" (o "12-10" corto). */
function fechaCl(iso: string, corta = false): string {
  const [a, m, d] = iso.split("-");
  return corta ? `${d}-${m}` : `${d}-${m}-${a}`;
}

function Kpi({
  label,
  value,
  icon: Icon,
  tone,
  detalle,
  to,
  destacar = false,
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  tone: string;
  detalle?: string;
  to?: string;
  destacar?: boolean;
}) {
  const contenido = (
    <Card
      className={`p-4 flex items-center gap-3 h-full ${to ? "hover:bg-muted/40 transition-colors" : ""} ${
        destacar ? "border-destructive/40" : ""
      }`}
    >
      <div className={`shrink-0 ${tone}`}>
        <Icon className="size-6" />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
          {label}
        </p>
        <p className="text-[22px] font-semibold leading-tight" data-testid={`kpi-${label}`}>
          {value}
        </p>
        {detalle && (
          <p className="text-[11px] text-muted-foreground truncate" title={detalle}>
            {detalle}
          </p>
        )}
      </div>
    </Card>
  );
  return to ? (
    <Link to={to} className="block">
      {contenido}
    </Link>
  ) : (
    contenido
  );
}

function Panel({ titulo, sub, children }: { titulo: string; sub?: string; children: React.ReactNode }) {
  return (
    <Card className="p-0 overflow-hidden">
      <div className="px-4 py-3 border-b">
        <h3 className="text-[14px] font-semibold">{titulo}</h3>
        {sub && <p className="text-[12px] text-muted-foreground">{sub}</p>}
      </div>
      <div className="p-4">{children}</div>
    </Card>
  );
}

function Vacio({ children }: { children: React.ReactNode }) {
  return <p className="text-[13px] text-muted-foreground py-6 text-center">{children}</p>;
}

function Ranking({ filas, vacio }: { filas: Conteo[]; vacio: string }) {
  if (filas.length === 0) return <Vacio>{vacio}</Vacio>;
  return (
    <BarSimple
      data={filas.map((f) => ({ etiqueta: f.etiqueta, total: f.total }))}
      categoryKey="etiqueta"
      valueKey="total"
      layout="vertical"
      showLabels
      categoryWidth={150}
      height={Math.max(120, filas.length * 34)}
    />
  );
}

export function DashboardPage() {
  const [periodo, setPeriodo] = useState(() => haceDias(30));
  const [preset, setPreset] = useState<number | null>(30);
  const [desde, setDesde] = useState(periodo.fecha_desde);
  const [hasta, setHasta] = useState(periodo.fecha_hasta);

  const { data, isLoading, isError, error } = useDashboardOperativo(periodo);

  function elegirPreset(dias: number) {
    const p = haceDias(dias);
    setPreset(dias);
    setDesde(p.fecha_desde);
    setHasta(p.fecha_hasta);
    setPeriodo(p);
  }

  function aplicar() {
    if (!desde || !hasta || desde > hasta) return;
    setPreset(null);
    setPeriodo({ fecha_desde: desde, fecha_hasta: hasta });
  }

  const d = data;
  // Sin datos (cargando o error) se muestra "—": un 0 se leería como dato real.
  const n = (v: number | undefined) => (v == null ? "—" : v.toLocaleString("es-CL"));
  const tendencia = (d?.tendencia_semanal ?? []).map((p) => ({
    semana: fechaCl(p.semana, true),
    atendidas: p.atendidas,
    inasistencias: p.inasistencias,
  }));
  const hayTendencia = tendencia.some((p) => p.atendidas + p.inasistencias > 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Dashboard operativo</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Atenciones registradas en SALUTEM y pendientes de gestión del SIGE
            {d && (
              <>
                {" · "}período {fechaCl(d.periodo_desde)} al {fechaCl(d.periodo_hasta)}
              </>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-2">
          <div className="flex gap-1" role="group" aria-label="Período rápido">
            {PRESETS.map((p) => (
              <Button
                key={p.dias}
                size="sm"
                variant={preset === p.dias ? "default" : "outline"}
                onClick={() => elegirPreset(p.dias)}
              >
                {p.label}
              </Button>
            ))}
          </div>
          <div>
            <Label htmlFor="desde" className="text-[11px]">Desde</Label>
            <Input id="desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="h-8" />
          </div>
          <div>
            <Label htmlFor="hasta" className="text-[11px]">Hasta</Label>
            <Input id="hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="h-8" />
          </div>
          <Button size="sm" variant="outline" onClick={aplicar} disabled={!desde || !hasta || desde > hasta} data-testid="btn-aplicar">
            Aplicar
          </Button>
        </div>
      </div>

      {isError && (
        <p className="text-[13px] text-destructive px-1">
          {error instanceof Error ? error.message : "Error al cargar"}
        </p>
      )}
      {isLoading && <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>}

      {/* Actividad del período */}
      <section className="space-y-2">
        <h2 className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
          Actividad del período
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 2xl:grid-cols-6 gap-3">
          <Kpi label="Atenciones" value={n(d?.atenciones)} icon={CheckCircle2} tone="text-[oklch(0.5_0.13_150)]" detalle="Citas atendidas en SALUTEM" />
          <Kpi
            label="Inasistencias"
            value={n(d?.inasistencias)}
            icon={UserX}
            tone="text-[oklch(0.55_0.15_60)]"
            detalle={d?.tasa_inasistencia != null ? `${d.tasa_inasistencia.toLocaleString("es-CL")}% de las citas` : "Sin citas con resultado"}
          />
          <Kpi label="Anulaciones" value={n(d?.anulaciones)} icon={Ban} tone="text-destructive" />
          <Kpi label="Ingresos" value={n(d?.ingresos_periodo)} icon={UserPlus} tone="text-[oklch(0.45_0.13_250)]" detalle={`${n(d?.altas_periodo)} altas en el período`} to="/ingresos" />
          <Kpi label="Controles médicos" value={n(d?.controles_periodo)} icon={ClipboardCheck} tone="text-[oklch(0.5_0.12_220)]" to="/controles" />
          <Kpi label="Agenda 7 días" value={n(d?.agendadas_proximas)} icon={CalendarClock} tone="text-[oklch(0.45_0.13_250)]" detalle="Citas vigentes desde hoy" to="/agenda" />
        </div>
      </section>

      {/* Por gestionar hoy */}
      <section className="space-y-2">
        <h2 className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
          Por gestionar hoy
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 2xl:grid-cols-6 gap-3">
          <Kpi label="Casos activos" value={n(d?.pacientes_activos)} icon={Users} tone="text-[oklch(0.45_0.13_250)]" to="/ingresos" />
          <Kpi label="Licencias vigentes" value={n(d?.licencias_activas)} icon={FileText} tone="text-[oklch(0.55_0.15_60)]" detalle={`${n(d?.licencias_pendientes_isl)} sin enviar al ISL`} to="/licencias" destacar={(d?.licencias_pendientes_isl ?? 0) > 0} />
          <Kpi label="ODA vencidas" value={n(d?.odas_vencidas)} icon={FileClock} tone="text-destructive" detalle={`${n(d?.odas_por_vencer)} vencen en 15 días`} to="/reportes" destacar={(d?.odas_vencidas ?? 0) > 0} />
          <Kpi label="Sin folio" value={n(d?.pacientes_pendientes_folio)} icon={UserRoundSearch} tone="text-[oklch(0.5_0.12_220)]" detalle="Atendidos en SALUTEM" to="/pendientes-folio" destacar={(d?.pacientes_pendientes_folio ?? 0) > 0} />
          <Kpi label="EPT abiertos" value={n(d?.ept_abiertos)} icon={BriefcaseBusiness} tone="text-[oklch(0.56_0.10_185)]" to="/ept" />
          <Kpi label="Alertas abiertas" value={n(d?.alertas_abiertas)} icon={AlertTriangle} tone="text-destructive" detalle="Pendientes o leídas" destacar={(d?.alertas_abiertas ?? 0) > 0} />
        </div>
      </section>

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Panel titulo="Atenciones vs. inasistencias" sub="Por semana (lunes a domingo), 8 semanas hasta el fin del período">
            {hayTendencia ? (
              <AreaTrend
                data={tendencia}
                xKey="semana"
                series={[
                  { key: "atendidas", label: "Atendidas", color: "var(--chart-1)" },
                  { key: "inasistencias", label: "Inasistencias", color: "var(--chart-4)" },
                ]}
              />
            ) : (
              <Vacio>Sin atenciones registradas en SALUTEM para estas semanas.</Vacio>
            )}
          </Panel>
        </div>

        <Panel titulo="Alertas abiertas por tipo">
          {d && d.alertas_por_tipo.length > 0 ? (
            <ul className="divide-y">
              {d.alertas_por_tipo.map((a) => (
                <li key={a.etiqueta} className="flex items-center justify-between py-2 text-[13px]">
                  <span>{ETIQUETAS_ALERTA[a.etiqueta] ?? a.etiqueta}</span>
                  <span className="font-semibold tabular-nums">{a.total}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Vacio>No hay alertas abiertas.</Vacio>
          )}
        </Panel>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Panel titulo="Atenciones por especialidad" sub="Top 8 del período">
          <Ranking filas={d?.atenciones_por_especialidad ?? []} vacio="Sin atenciones en el período." />
        </Panel>
        <Panel titulo="Atenciones por profesional" sub="Top 8 del período">
          <Ranking filas={d?.atenciones_por_profesional ?? []} vacio="Sin atenciones en el período." />
        </Panel>
        <Panel titulo="Casos activos por programa">
          {d && d.activos_por_programa.length > 0 ? (
            <DonutChart
              data={d.activos_por_programa.map((p) => ({ label: p.etiqueta, value: p.total }))}
              centerLabel={n(d.pacientes_activos)}
              centerSub="activos"
              showLegend
            />
          ) : (
            <Vacio>No hay casos activos.</Vacio>
          )}
        </Panel>
      </div>
    </div>
  );
}
