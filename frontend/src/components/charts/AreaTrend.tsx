/**
 * AreaTrend — dual-series area chart with gradient fills.
 * Mirrors the "Atenciones vs. inasistencias" chart in v2 Dashboard.
 */
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

export interface AreaTrendSeries {
  /** Recharts dataKey for this series */
  key: string
  /** CSS color or var(), e.g. "var(--primary)" */
  color: string
  label: string
}

export interface AreaTrendProps {
  /** Array of data objects, each must have a label key + each series key */
  data: Record<string, string | number>[]
  /** Key in the data objects used for the X-axis labels */
  xKey?: string
  series: [AreaTrendSeries, AreaTrendSeries]
  height?: number
}

export function AreaTrend({ data, xKey = "mes", series, height = 260 }: AreaTrendProps) {
  const [s1, s2] = series
  const g1 = `area-grad-${s1.key}`
  const g2 = `area-grad-${s2.key}`

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
          <defs>
            <linearGradient id={g1} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s1.color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={s1.color} stopOpacity={0} />
            </linearGradient>
            <linearGradient id={g2} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s2.color} stopOpacity={0.18} />
              <stop offset="100%" stopColor={s2.color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
              boxShadow: "0 8px 24px -8px rgba(0,0,0,0.12)",
            }}
          />
          <Area
            type="monotone"
            dataKey={s1.key}
            stroke={s1.color}
            strokeWidth={2.5}
            fill={`url(#${g1})`}
            dot={{ r: 4, fill: s1.color, strokeWidth: 2, stroke: "var(--card)" }}
            activeDot={{ r: 6 }}
          />
          <Area
            type="monotone"
            dataKey={s2.key}
            stroke={s2.color}
            strokeWidth={2}
            fill={`url(#${g2})`}
            dot={{ r: 3, fill: s2.color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
