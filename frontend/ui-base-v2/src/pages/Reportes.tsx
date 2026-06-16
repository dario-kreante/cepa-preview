import { Download, Share2, Filter } from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Cell,
  PieChart, Pie,
} from "recharts"
import { SERIE_INGRESOS, PATIENTS } from "@/data/seed"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const DIST_DX = [
  { t: "Trast. adaptativo", n: 8, c: "var(--chart-1)" },
  { t: "Depresión", n: 6, c: "var(--chart-2)" },
  { t: "Ansiedad generalizada", n: 5, c: "var(--chart-3)" },
  { t: "Burnout", n: 3, c: "var(--chart-4)" },
  { t: "TEPT", n: 2, c: "var(--chart-5)" },
  { t: "Otros", n: 1, c: "var(--muted-foreground)" },
]
const TOT_DX = DIST_DX.reduce((s, x) => s + x.n, 0)

const TIPOS_DERIVACION = Array.from(new Set(PATIENTS.map((p) => p.tipoDerivacion)))

const KPI_OPS = [
  { t: "Tasa de cierre", v: "68%", sub: "+4 pts vs. trim. ant.", tone: "success" },
  { t: "Inasistencia promedio", v: "11.2%", sub: "dentro de rango", tone: "neutral" },
  { t: "Tiempo medio tratamiento", v: "84 días", sub: "meta: 90 días", tone: "info" },
  { t: "Satisfacción (CSAT)", v: "4.6/5", sub: "n=42 encuestas", tone: "success" },
  { t: "Derivación oportuna", v: "92%", sub: "dentro de plazo ISL", tone: "primary" },
  { t: "RECA promedio", v: "37 días", sub: "desde solicitud", tone: "warning" },
]

const TONES: Record<string, { bg: string; fg: string; sub: string }> = {
  primary: { bg: "bg-primary/8", fg: "text-primary", sub: "text-primary/80" },
  success: { bg: "bg-[oklch(0.95_0.05_155)]", fg: "text-[oklch(0.32_0.12_155)]", sub: "text-[oklch(0.42_0.12_155)]" },
  info: { bg: "bg-[oklch(0.94_0.04_230)]", fg: "text-[oklch(0.38_0.14_230)]", sub: "text-[oklch(0.48_0.12_230)]" },
  warning: { bg: "bg-[oklch(0.96_0.08_85)]", fg: "text-[oklch(0.44_0.16_75)]", sub: "text-[oklch(0.52_0.14_75)]" },
  neutral: { bg: "bg-muted", fg: "text-foreground", sub: "text-muted-foreground" },
}

export function Reportes() {
  const distDerivacion = TIPOS_DERIVACION
    .map((t) => ({ tipo: t, count: PATIENTS.filter((p) => p.tipoDerivacion === t).length }))
    .filter((x) => x.count > 0)
    .sort((a, b) => b.count - a.count)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Reportería</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Indicadores operativos, tendencias y reportes ISL
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Filter /> Últimos 6 meses</Button>
          <Button variant="outline" size="sm"><Share2 /> Compartir</Button>
          <Button size="sm"><Download /> Exportar PDF</Button>
        </div>
      </div>

      {/* Row 1: Ingresos mensuales + Distribución diagnósticos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between p-5 pb-2">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Ingresos mensuales</h3>
              <p className="text-[11.5px] text-muted-foreground mt-0.5">Evolución en los últimos 6 meses</p>
            </div>
            <Button variant="ghost" size="sm">Ver detalle →</Button>
          </div>
          <CardContent className="pt-0">
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={SERIE_INGRESOS} margin={{ top: 20, right: 10, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="bar-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--primary)" stopOpacity={1} />
                      <stop offset="100%" stopColor="var(--primary)" stopOpacity={0.6} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="mes" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "var(--muted)" }} contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="value" fill="url(#bar-grad)" radius={[8, 8, 0, 0]} barSize={48} label={{ position: "top", fontSize: 11, fontWeight: 600, fill: "var(--primary)" }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <div className="p-5 pb-2">
            <h3 className="text-[14px] font-semibold tracking-tight">Distribución diagnósticos</h3>
            <p className="text-[11.5px] text-muted-foreground mt-0.5">{TOT_DX} casos totales</p>
          </div>
          <CardContent>
            <div className="relative h-[160px]">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={DIST_DX} dataKey="n" innerRadius={50} outerRadius={70} paddingAngle={2} stroke="none">
                    {DIST_DX.map((d, i) => <Cell key={i} fill={d.c} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 grid place-items-center pointer-events-none">
                <div className="text-center">
                  <div className="text-[22px] font-bold leading-none">{TOT_DX}</div>
                  <div className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">casos</div>
                </div>
              </div>
            </div>
            <div className="space-y-1.5 mt-3">
              {DIST_DX.map((d, i) => (
                <div key={i} className="flex items-center gap-2 text-[11.5px]">
                  <span className="size-2 rounded-full shrink-0" style={{ background: d.c }} />
                  <span className="flex-1 truncate">{d.t}</span>
                  <span className="mono font-semibold">{d.n}</span>
                  <span className="mono text-muted-foreground w-10 text-right">{Math.round((d.n / TOT_DX) * 100)}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Derivación + KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <div className="p-5 pb-3">
            <h3 className="text-[14px] font-semibold tracking-tight">Tipo de derivación</h3>
            <p className="text-[11.5px] text-muted-foreground mt-0.5">Distribución por origen</p>
          </div>
          <CardContent className="space-y-3">
            {distDerivacion.map((d) => {
              const pct = Math.round((d.count / PATIENTS.length) * 100)
              return (
                <div key={d.tipo}>
                  <div className="flex items-center justify-between text-[12.5px] mb-1">
                    <span className="font-semibold">{d.tipo}</span>
                    <div className="flex items-center gap-2">
                      <span className="mono font-semibold">{d.count}</span>
                      <span className="text-[11px] text-muted-foreground mono">{pct}%</span>
                    </div>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        <Card>
          <div className="p-5 pb-3">
            <h3 className="text-[14px] font-semibold tracking-tight">KPIs operativos</h3>
            <p className="text-[11.5px] text-muted-foreground mt-0.5">Indicadores clave del trimestre</p>
          </div>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {KPI_OPS.map((k) => {
                const t = TONES[k.tone]
                return (
                  <div key={k.t} className={cn("p-3.5 rounded-lg border border-border/50", t.bg)}>
                    <div className={cn("text-[10.5px] font-bold uppercase tracking-wider mb-1.5", t.sub)}>{k.t}</div>
                    <div className={cn("text-[22px] font-bold tracking-tight leading-none", t.fg)}>{k.v}</div>
                    <div className={cn("text-[11px] mt-1.5", t.sub)}>{k.sub}</div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Resumen ejecutivo */}
      <Card>
        <div className="p-5 pb-3 flex items-center justify-between">
          <div>
            <h3 className="text-[14px] font-semibold tracking-tight">Resumen ejecutivo · Abril 2026</h3>
            <p className="text-[11.5px] text-muted-foreground mt-0.5">Indicadores consolidados del mes</p>
          </div>
          <Badge variant="success">Actualizado hoy 10:42</Badge>
        </div>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-[13px]">
            <Summary label="Ingresos del mes" v="12" d="+20% vs. marzo" />
            <Summary label="Altas otorgadas" v="8" d="terapéuticas y médicas" />
            <Summary label="EPT completadas" v="9" d="3 con envío ISL" />
            <Summary label="Reintegros efectivos" v="5" d="3 con alta laboral" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function Summary({ label, v, d }: { label: string; v: string; d: string }) {
  return (
    <div className="border-l-2 border-primary pl-4">
      <div className="text-[11.5px] text-muted-foreground">{label}</div>
      <div className="text-[26px] font-bold tracking-tight leading-none mt-1">{v}</div>
      <div className="text-[11px] text-muted-foreground mt-1">{d}</div>
    </div>
  )
}
