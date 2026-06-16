import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/10 text-primary",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive/10 text-destructive",
        success: "border-transparent bg-[oklch(0.95_0.05_155)] text-[oklch(0.38_0.12_155)]",
        warning: "border-transparent bg-[oklch(0.96_0.08_85)] text-[oklch(0.42_0.14_75)]",
        info: "border-transparent bg-[oklch(0.95_0.05_230)] text-[oklch(0.40_0.14_230)]",
        purple: "border-transparent bg-[oklch(0.95_0.05_290)] text-[oklch(0.42_0.16_290)]",
        outline: "text-foreground",
        neutral: "border-transparent bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
