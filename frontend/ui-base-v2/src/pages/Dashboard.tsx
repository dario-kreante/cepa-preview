import { useState } from "react"
import {
  Users, UserPlus, FileText, Stethoscope, Pill, Briefcase, RefreshCw, AlertTriangle,
  ArrowUpRight, ArrowDownRight, MoreHorizontal, Download, Filter, Plus, CheckCircle2, Clock,
} from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip,
  PieChart, Pie, Cell, AreaChart, Area,
} from "recharts"
import {
  DASHBOARD_KPIS, SERIE_ATENCIONES, CARGA_PROFESIONAL, DIAG_DISTRIBUTION, ALERTS,
} from "@/data/seed"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ButtonGroup } from "@/components/ui/button-group"
import { Donut } from "@/components/ui/donut"
import { cn } from "@/lib/utils"

type Range = "12m" | "30d" | "7d" | "24h"

const PRIMARY_KPIS = [
  { key: "pacientesActivos", label: "Pacientes activos", donut: 72, delta: "+12%", dir: "up" as const, sub: "186 / 258 capacidad" },
  { key: "licenciasActivas", label: "Licencias activas", donut: 58, delta: "+8%", dir: "up" as const, sub: "46 vigentes · 12 por vencer" },
]

const SECONDARY_KPIS = [
  { key: "ingresosMes", label: "Ingresos", icon: UserPlus, delta: "+3", dir: "up" as const, tone: "info" },
  { key: "controlesEstaSemana", label: "Controles / semana", icon: Stethoscope, delta: "−2", dir: "down" as const, tone: "success" },
  { key: "recetasActivas", label: "Recetas vigentes", icon: Pill, delta: "+5", dir: "up" as const, tone: "purple" },
  { key: "eptEnProceso", label: "EPT en proceso", icon: Briefcase, delta: "=", dir: "flat" as const, tone: "teal" },
  { key: "reintegrosProceso", label: "Reintegros", icon: RefreshCw, delta: "+2", dir: "up" as const, tone: "primary" },
  { key: "alertasCriticas", label: "Alertas críticas", icon: AlertTriangle, delta: "Atención", dir: "alert" as const, tone: "danger" },
]

const TONE_STYLES: Record<string, { bg: string; fg: string }> = {
  primary: { bg: "bg-primary/10", fg: "text-primary" },
  info: { bg: "bg-[oklch(0.95_0.05_230)]", fg: "text-[oklch(0.42_0.14_230)]" },
  success: { bg: "bg-[oklch(0.94_0.05_155)]", fg: "text-[oklch(0.40_0.12_155)]" },
  purple: { bg: "bg-[oklch(0.95_0.05_290)]", fg: "text-[oklch(0.42_0.16_290)]" },
  teal: { bg: "bg-[oklch(0.94_0.05_175)]", fg: "text-[oklch(0.42_0.14_175)]" },
  danger: { bg: "bg-destructive/10", fg: "text-destructive" },
}

function Delta({ dir, children }: { dir: "up" | "down" | "flat" | "alert"; children: React.ReactNode }) {
  const cls =
    dir === "up" ? "text-[oklch(0.38_0.12_155)]"
    : dir === "down" ? "text-destructive"
    : dir === "alert" ? "text-destructive"
    : "text-muted-foreground"
  const Icon = dir === "up" ? ArrowUpRight : dir === "down" || dir === "alert" ? ArrowDownRight : null
  return (
    <span className={cn("inline-flex items-center gap-0.5 text-[11.5px] font-semibold", cls)}>
      {Icon && <Icon className="size-3" />}
      {children}
    </span>
  )
}

const TAREAS = [
  { id: 1, titulo: "Revisar LM-10003", desc: "Vence mañana", pri: "Urgente", done: false },
  { id: 2, titulo: "Reagendar control · Folio 012", desc: "Paciente no asistió", pri: "Alta", done: false },
  { id: 3, titulo: "Firmar receta · Sertralina 50mg", desc: "Solicitada por Ps. Pinto", pri: "Media", done: false },
  { id: 4, titulo: "Enviar RECA · Folio 015", desc: "Pendiente desde ayer", pri: "Alta", done: false },
  { id: 5, titulo: "Actualizar EPT · Folio 022", desc: "Reevaluación", pri: "Media", done: false },
  { id: 6, titulo: "Validar consentimiento · Folio 010", desc: "Faltan firmas", pri: "Baja", done: true },
  { id: 7, titulo: "Exportar reporte ISL", desc: "Auto · lunes", pri: "Baja", done: true },
]

export function Dashboard({ onOpenPatient: _onOpenPatient }: { onOpenPatient: (folio: string) => void }) {
  const [range, setRange] = useState<Range>("30d")
  const topAlerts = ALERTS.slice(0, 5)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h1 className="text-[22px] font-semibold tracking-tight text-foreground">
              Buenos días, María
            </h1>
            <p className="text-[13px] text-muted-foreground mt-1">
              Panel operativo del Sistema CEPA · Actualizado 10:42
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm"><Filter /> Filtros</Button>
            <Button variant="outline" size="sm"><Download /> Exportar</Button>
            <Button size="sm"><Plus /> Nuevo ingreso</Button>
          </div>
        </div>

        {/* Filter pill group */}
        <div className="flex items-center gap-3">
          <ButtonGroup<Range>
            options={[
              { value: "12m", label: "12 meses" },
              { value: "30d", label: "30 días" },
              { value: "7d", label: "7 días" },
              { value: "24h", label: "24 horas" },
            ]}
            value={range}
            onChange={setRange}
          />
          <div className="text-[11.5px] text-muted-foreground">
            Comparado con período anterior
          </div>
        </div>
      </div>

      {/* Primary KPIs with donuts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PRIMARY_KPIS.map((k) => (
          <Card key={k.key} className="hover:shadow-sm transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="text-[13px] font-semibold text-muted-foreground">{k.label}</div>
                <button className="size-6 rounded-md hover:bg-muted grid place-items-center text-muted-foreground cursor-pointer">
                  <MoreHorizontal className="size-4" />
                </button>
              </div>
              <div className="flex items-center gap-5">
                <Donut value={k.donut} size={88} stroke={8} color="var(--primary)" trackColor="oklch(0.92_0.02_195)" />
                <div className="flex-1">
                  <div className="text-[11px] text-muted-foreground mb-1">Total actual</div>
                  <div className="flex items-baseline gap-2">
                    <div className="text-[30px] font-bold tracking-tight leading-none">
                      {(DASHBOARD_KPIS as any)[k.key]}
                    </div>
                    <Delta dir={k.dir}>{k.delta}</Delta>
                  </div>
                  <div className="text-[11.5px] text-muted-foreground mt-1.5">{k.sub}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {SECONDARY_KPIS.map((k) => {
          const tone = TONE_STYLES[k.tone]
          const Icon = k.icon
          return (
            <Card key={k.key} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-4">
                <div className={cn("size-8 rounded-lg grid place-items-center mb-3", tone.bg)}>
                  <Icon className={cn("size-[15px]", tone.fg)} />
                </div>
                <div className="text-[22px] font-bold leading-none tracking-tight mb-1">
                  {(DASHBOARD_KPIS as any)[k.key]}
                </div>
                <div className="text-[11px] text-muted-foreground mb-2">{k.label}</div>
                <Delta dir={k.dir}>{k.delta}</Delta>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Chart + Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-start justify-between p-5 pb-2">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Atenciones vs. inasistencias</h3>
              <p className="text-[11.5px] text-muted-foreground mt-0.5">Últimos 7 meses · todas las unidades</p>
            </div>
            <div className="flex items-center gap-3">
              <Legend color="var(--primary)" label="Atenciones" />
              <Legend color="var(--destructive)" label="Inasistencias" />
              <button className="size-7 rounded-md hover:bg-muted grid place-items-center text-muted-foreground cursor-pointer">
                <MoreHorizontal className="size-4" />
              </button>
            </div>
          </div>
          <CardContent className="pb-2 pt-2">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={SERIE_ATENCIONES} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--destructive)" stopOpacity={0.18} />
                      <stop offset="100%" stopColor="var(--destructive)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="mes" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, boxShadow: "0 8px 24px -8px rgba(0,0,0,0.12)" }}
                  />
                  <Area type="monotone" dataKey="atenciones" stroke="var(--primary)" strokeWidth={2.5} fill="url(#g1)" dot={{ r: 4, fill: "var(--primary)", strokeWidth: 2, stroke: "var(--card)" }} activeDot={{ r: 6 }} />
                  <Area type="monotone" dataKey="inasistencias" stroke="var(--destructive)" strokeWidth={2} fill="url(#g2)" dot={{ r: 3, fill: "var(--destructive)" }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <div className="flex items-start justify-between p-5 pb-3">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Tareas del día</h3>
              <div className="flex items-center gap-2 mt-1.5">
                <Badge variant="warning">7 pendientes</Badge>
                <span className="text-[11px] text-muted-foreground">2 urgentes</span>
              </div>
            </div>
            <button className="size-7 rounded-md hover:bg-muted grid place-items-center text-muted-foreground cursor-pointer">
              <MoreHorizontal className="size-4" />
            </button>
          </div>
          <div className="max-h-[260px] overflow-y-auto">
            {TAREAS.map((t) => (
              <label
                key={t.id}
                className={cn(
                  "flex items-start gap-3 px-5 py-2.5 border-t hover:bg-muted/50 cursor-pointer transition-colors",
                  t.done && "opacity-60"
                )}
              >
                <div className="pt-0.5">
                  <input
                    type="checkbox"
                    defaultChecked={t.done}
                    className="size-4 rounded border-border accent-primary cursor-pointer"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className={cn("text-[12.5px] font-semibold leading-tight", t.done && "line-through")}>
                    {t.titulo}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{t.desc}</div>
                </div>
                <Badge variant={t.pri === "Urgente" ? "destructive" : t.pri === "Alta" ? "warning" : t.pri === "Media" ? "info" : "neutral"}>
                  {t.pri}
                </Badge>
              </label>
            ))}
          </div>
        </Card>
      </div>

      {/* Row 3: Carga + Diagnósticos + Alertas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-start justify-between p-5 pb-2">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Carga por profesional</h3>
              <p className="text-[11.5px] text-muted-foreground mt-0.5">Atenciones del mes</p>
            </div>
            <button className="size-7 rounded-md hover:bg-muted grid place-items-center text-muted-foreground cursor-pointer">
              <MoreHorizontal className="size-4" />
            </button>
          </div>
          <CardContent className="pt-0">
            <div className="h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={CARGA_PROFESIONAL} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="nombre" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} width={110} />
                  <Tooltip cursor={{ fill: "var(--muted)" }} contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="atenciones" fill="var(--primary)" radius={[0, 6, 6, 0]} barSize={16} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <div className="flex items-start justify-between p-5 pb-2">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Distribución diagnóstica</h3>
              <p className="text-[11.5px] text-muted-foreground mt-0.5">Últimos 30 días</p>
            </div>
            <button className="size-7 rounded-md hover:bg-muted grid place-items-center text-muted-foreground cursor-pointer">
              <MoreHorizontal className="size-4" />
            </button>
          </div>
          <CardContent className="pt-0">
            <div className="h-[220px] flex items-center">
              <div className="w-[140px] h-[140px] shrink-0 relative">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={DIAG_DISTRIBUTION}
                      innerRadius={44}
                      outerRadius={66}
                      dataKey="valor"
                      paddingAngle={2}
                      stroke="none"
                    >
                      {DIAG_DISTRIBUTION.map((_, i) => (
                        <Cell key={i} fill={`var(--chart-${(i % 5) + 1})`} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 grid place-items-center pointer-events-none">
                  <div className="text-center">
                    <div className="text-[18px] font-bold leading-none">128</div>
                    <div className="text-[9.5px] text-muted-foreground mt-0.5 uppercase tracking-wider">Total</div>
                  </div>
                </div>
              </div>
              <div className="flex-1 pl-3 space-y-1.5">
                {DIAG_DISTRIBUTION.map((d, i) => (
                  <div key={d.label} className="flex items-center gap-2 text-[11px]">
                    <span className="size-2 rounded-full shrink-0" style={{ background: `var(--chart-${(i % 5) + 1})` }} />
                    <span className="flex-1 truncate">{d.label}</span>
                    <span className="font-semibold mono text-muted-foreground">{d.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <div className="flex items-start justify-between p-5 pb-3">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Alertas urgentes</h3>
              <p className="text-[11.5px] text-muted-foreground mt-0.5">Requieren acción</p>
            </div>
            <button className="text-[11.5px] font-semibold text-primary hover:underline cursor-pointer">
              Ver todas →
            </button>
          </div>
          <div>
            {topAlerts.map((a, i) => {
              const Icon = a.tipo === "danger" ? AlertTriangle : a.tipo === "warn" ? Clock : a.tipo === "success" ? CheckCircle2 : AlertTriangle
              return (
                <div
                  key={a.id}
                  className={cn(
                    "flex items-start gap-3 px-5 py-3 border-t first:border-t-0 hover:bg-muted/50 cursor-pointer transition-colors",
                    i === 0 && "bg-destructive/[0.03]"
                  )}
                >
                  <div className={cn(
                    "size-7 rounded-md grid place-items-center shrink-0",
                    a.tipo === "danger" ? "bg-destructive/15 text-destructive" :
                    a.tipo === "warn" ? "bg-[oklch(0.96_0.08_85)] text-[oklch(0.52_0.16_75)]" :
                    a.tipo === "success" ? "bg-[oklch(0.94_0.05_155)] text-[oklch(0.40_0.12_155)]" :
                    "bg-[oklch(0.94_0.04_230)] text-[oklch(0.42_0.14_230)]"
                  )}>
                    <Icon className="size-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12.5px] font-semibold leading-tight">{a.titulo}</div>
                    <div className="text-[11px] text-muted-foreground truncate mt-0.5">
                      {a.paciente} · Folio {a.folio}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11.5px] text-muted-foreground">
      <span className="size-2 rounded-full" style={{ background: color }} />
      {label}
    </div>
  )
}
