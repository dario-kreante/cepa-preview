/**
 * DonutChart — PieChart with innerRadius + Cell colors from CSS chart tokens.
 * Mirrors the "Distribución diagnóstica" usage in v2 Dashboard and Reportes.
 */
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts"

export interface DonutSlice {
  label: string
  value: number
  /** Optional explicit fill; defaults to var(--chart-N) cycling 1-5 */
  color?: string
}

export interface DonutChartProps {
  data: DonutSlice[]
  /** Text shown in center (e.g. total count) */
  centerLabel?: string
  /** Sub-text below center label */
  centerSub?: string
  innerRadius?: number
  outerRadius?: number
  height?: number
  /** Whether to show the legend list below the chart */
  showLegend?: boolean
}

export function DonutChart({
  data,
  centerLabel,
  centerSub,
  innerRadius = 44,
  outerRadius = 66,
  height = 220,
  showLegend = false,
}: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div>
      <div className="relative" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              dataKey="value"
              paddingAngle={2}
              stroke="none"
            >
              {data.map((slice, i) => (
                <Cell
                  key={`cell-${i}`}
                  fill={slice.color ?? `var(--chart-${(i % 5) + 1})`}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {(centerLabel != null || centerSub != null) && (
          <div className="absolute inset-0 grid place-items-center pointer-events-none">
            <div className="text-center">
              {centerLabel != null && (
                <div className="text-[18px] font-bold leading-none">{centerLabel}</div>
              )}
              {centerSub != null && (
                <div className="text-[9.5px] text-muted-foreground mt-0.5 uppercase tracking-wider">
                  {centerSub}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {showLegend && (
        <div className="space-y-1.5 mt-3">
          {data.map((slice, i) => (
            <div key={slice.label} className="flex items-center gap-2 text-[11px]">
              <span
                className="size-2 rounded-full shrink-0"
                style={{ background: slice.color ?? `var(--chart-${(i % 5) + 1})` }}
              />
              <span className="flex-1 truncate">{slice.label}</span>
              <span className="font-semibold font-mono text-muted-foreground">{slice.value}</span>
              {total > 0 && (
                <span className="font-mono text-muted-foreground w-10 text-right">
                  {Math.round((slice.value / total) * 100)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
