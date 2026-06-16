/**
 * BarSimple — single-series bar chart.
 * Supports vertical layout (carga por profesional) and horizontal (ingresos mensuales).
 * Mirrors both bar chart usages in v2 Dashboard + Reportes.
 */
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts"

export interface BarSimpleProps {
  data: Record<string, string | number>[]
  /** Key used as the category axis (names/labels) */
  categoryKey: string
  /** Key used as the value axis */
  valueKey: string
  /** "horizontal" = standard vertical bars; "vertical" = horizontal bars (rotated layout) */
  layout?: "horizontal" | "vertical"
  /** Bar fill color, defaults to var(--primary) */
  color?: string
  /** Optional bar size in px */
  barSize?: number
  /** Show value labels above/beside bars */
  showLabels?: boolean
  height?: number
  /** Width reserved for category labels when layout="vertical" */
  categoryWidth?: number
}

export function BarSimple({
  data,
  categoryKey,
  valueKey,
  layout = "horizontal",
  color = "var(--primary)",
  barSize,
  showLabels = false,
  height = 240,
  categoryWidth = 110,
}: BarSimpleProps) {
  const isVertical = layout === "vertical"

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout={isVertical ? "vertical" : "horizontal"}
          margin={{ top: showLabels ? 20 : 4, right: 10, left: isVertical ? 0 : -15, bottom: 0 }}
        >
          <defs>
            <linearGradient id="bar-simple-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={1} />
              <stop offset="100%" stopColor={color} stopOpacity={0.6} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            horizontal={!isVertical}
            vertical={isVertical}
          />
          {isVertical ? (
            <>
              <XAxis
                type="number"
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey={categoryKey}
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                axisLine={false}
                tickLine={false}
                width={categoryWidth}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey={categoryKey}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                axisLine={false}
                tickLine={false}
              />
            </>
          )}
          <Tooltip
            cursor={{ fill: "var(--muted)" }}
            contentStyle={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Bar
            dataKey={valueKey}
            fill={isVertical ? color : "url(#bar-simple-grad)"}
            radius={isVertical ? [0, 6, 6, 0] : [8, 8, 0, 0]}
            barSize={barSize ?? (isVertical ? 16 : 48)}
          >
            {showLabels && (
              <LabelList
                dataKey={valueKey}
                position={isVertical ? "right" : "top"}
                style={{ fontSize: 11, fontWeight: 600, fill: color }}
              />
            )}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
