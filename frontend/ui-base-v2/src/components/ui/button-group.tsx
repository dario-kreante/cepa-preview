import { cn } from "@/lib/utils"

export function ButtonGroup<T extends string>({
  options, value, onChange, className,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
  className?: string
}) {
  return (
    <div className={cn("inline-flex items-center bg-card border rounded-lg shadow-xs p-0.5", className)}>
      {options.map((o, i) => {
        const active = o.value === value
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative px-3 h-7 text-[12px] font-semibold transition-colors rounded-md cursor-pointer",
              active
                ? "bg-muted text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
            style={{ zIndex: active ? 1 : 0 }}
          >
            {o.label}
            {i < options.length - 1 && !active && (
              <span className="absolute right-0 top-1/2 -translate-y-1/2 h-3 w-px bg-border" />
            )}
          </button>
        )
      })}
    </div>
  )
}
