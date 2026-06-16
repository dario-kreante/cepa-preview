import { Bell, HelpCircle } from "lucide-react"
import { DASHBOARD_KPIS } from "@/data/seed"

export function Topbar({
  title, crumbs, onToggleAlerts, alertsHidden,
}: {
  title: string
  crumbs: string
  onToggleAlerts: () => void
  alertsHidden: boolean
}) {
  return (
    <header className="h-14 bg-card border-b flex items-center px-6 gap-3 sticky top-0 z-20">
      <div>
        <h1 className="text-[15px] font-semibold tracking-tight leading-none">{title}</h1>
        <p className="text-[11px] text-muted-foreground mt-1">{crumbs}</p>
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-2 bg-[oklch(0.96_0.05_155)] text-[oklch(0.38_0.12_155)] border border-[oklch(0.88_0.05_155)] px-2.5 py-1 rounded-full text-[11px] font-semibold">
        <span className="size-1.5 rounded-full bg-[oklch(0.64_0.14_155)]" />
        {DASHBOARD_KPIS.pacientesActivos} activos
      </div>
      <div className="flex items-center gap-2 bg-destructive/10 text-destructive border border-destructive/20 px-2.5 py-1 rounded-full text-[11px] font-semibold">
        <span className="size-1.5 rounded-full bg-destructive animate-pulse" />
        {DASHBOARD_KPIS.alertasCriticas} críticas
      </div>

      <div className="w-px h-6 bg-border mx-1" />

      <button className="size-9 rounded-md grid place-items-center hover:bg-muted transition-colors cursor-pointer text-muted-foreground hover:text-foreground">
        <HelpCircle className="size-[18px]" />
      </button>

      <button
        onClick={onToggleAlerts}
        className="size-9 rounded-md grid place-items-center hover:bg-muted transition-colors relative cursor-pointer text-muted-foreground hover:text-foreground"
      >
        <Bell className="size-[18px]" />
        {!alertsHidden && (
          <span className="absolute top-2 right-2 size-1.5 bg-destructive rounded-full ring-2 ring-card" />
        )}
      </button>
    </header>
  )
}
