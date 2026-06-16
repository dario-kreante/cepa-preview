import { cn } from "@/lib/utils"

export function Donut({
  value, size = 56, stroke = 6, color = "var(--primary)", trackColor = "var(--muted)", className,
  children,
}: {
  value: number // 0-100
  size?: number
  stroke?: number
  color?: string
  trackColor?: string
  className?: string
  children?: React.ReactNode
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const offset = c - (value / 100) * c

  return (
    <div className={cn("relative inline-grid place-items-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={trackColor} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      {children && (
        <div className="absolute inset-0 grid place-items-center text-[10.5px] font-bold mono">
          {children}
        </div>
      )}
    </div>
  )
}
