import {
  LayoutDashboard, Users, FileText, Pill, Stethoscope, Briefcase,
  RefreshCw, ShieldCheck, Calendar, BarChart3, ChevronsLeft,
  Search, LifeBuoy, Settings, LogOut, X,
} from "lucide-react"
import { cn } from "@/lib/utils"

type NavKey =
  | "dashboard" | "ingresos" | "licencias" | "farmacos" | "controles"
  | "ept" | "reintegro" | "auditoria" | "agenda" | "reportes"

export const NAV_ITEMS: {
  key: NavKey
  label: string
  icon: React.ComponentType<{ className?: string }>
  badge?: number
  group: "general" | "clinico" | "operacion"
}[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, group: "general" },
  { key: "ingresos", label: "Ingresos y pacientes", icon: Users, group: "clinico" },
  { key: "licencias", label: "Licencias médicas", icon: FileText, badge: 4, group: "clinico" },
  { key: "farmacos", label: "Gestión de fármacos", icon: Pill, group: "clinico" },
  { key: "controles", label: "Controles médicos", icon: Stethoscope, group: "clinico" },
  { key: "ept", label: "Seguimiento EPT", icon: Briefcase, badge: 2, group: "clinico" },
  { key: "reintegro", label: "Seguimiento reintegro", icon: RefreshCw, group: "clinico" },
  { key: "auditoria", label: "Auditoría", icon: ShieldCheck, group: "clinico" },
  { key: "agenda", label: "Agendamiento", icon: Calendar, group: "operacion" },
  { key: "reportes", label: "Reportería", icon: BarChart3, group: "operacion" },
]

export function Sidebar({
  current, onNav, collapsed, onToggle,
}: {
  current: NavKey
  onNav: (k: NavKey) => void
  collapsed: boolean
  onToggle: () => void
}) {
  const groups: { label: string; key: string }[] = [
    { label: "General", key: "general" },
    { label: "Módulos clínicos", key: "clinico" },
    { label: "Operación", key: "operacion" },
  ]

  return (
    <aside
      className={cn(
        "bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col transition-all duration-300 shrink-0",
        collapsed ? "w-16" : "w-[260px]"
      )}
    >
      {/* Brand */}
      <div className={cn(
        "flex items-center gap-2.5 px-5 pt-5 pb-4",
        collapsed && "justify-center px-2"
      )}>
        <div className="relative size-8 rounded-lg bg-gradient-to-br from-primary to-[oklch(0.38_0.09_195)] grid place-items-center shadow-sm">
          <span className="text-primary-foreground font-bold text-[13px] tracking-tight">C</span>
        </div>
        {!collapsed && (
          <div className="flex flex-col leading-tight">
            <span className="text-foreground font-bold text-[14px] tracking-tight">CEPA</span>
            <span className="text-muted-foreground text-[10.5px]">Universidad de Talca</span>
          </div>
        )}
      </div>

      {/* Search */}
      {!collapsed && (
        <div className="px-4 pb-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 size-3.5 text-muted-foreground pointer-events-none" />
            <input
              placeholder="Buscar…"
              className="w-full h-8 pl-8 pr-2 text-[12.5px] bg-background border border-border rounded-md shadow-xs placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3">
        {groups.map((g) => (
          <div key={g.key} className="mb-3">
            {!collapsed && (
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70 px-2 py-1.5 font-semibold">
                {g.label}
              </div>
            )}
            <div className="space-y-0.5">
              {NAV_ITEMS.filter((it) => it.group === g.key).map((it) => {
                const active = current === it.key
                const Icon = it.icon
                return (
                  <button
                    key={it.key}
                    onClick={() => onNav(it.key)}
                    className={cn(
                      "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium transition-colors cursor-pointer",
                      collapsed && "justify-center px-0",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
                    )}
                  >
                    <Icon className={cn("size-[17px] shrink-0", active ? "text-primary" : "text-muted-foreground")} />
                    {!collapsed && (
                      <>
                        <span className="flex-1 text-left truncate">{it.label}</span>
                        {it.badge && (
                          <span className="bg-destructive/10 text-destructive text-[10px] font-semibold px-1.5 py-0.5 rounded-full min-w-4 text-center">
                            {it.badge}
                          </span>
                        )}
                      </>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom: Support + Settings */}
      <div className="px-3 pb-2 space-y-0.5">
        <button className={cn(
          "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors cursor-pointer",
          collapsed && "justify-center px-0"
        )}>
          <LifeBuoy className="size-[17px] text-muted-foreground shrink-0" />
          {!collapsed && <span>Ayuda y soporte</span>}
        </button>
        <button className={cn(
          "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors cursor-pointer",
          collapsed && "justify-center px-0"
        )}>
          <Settings className="size-[17px] text-muted-foreground shrink-0" />
          {!collapsed && <span>Configuración</span>}
        </button>
      </div>

      {/* Casos del mes card (Untitled UI style) */}
      {!collapsed && (
        <div className="mx-3 mb-3 p-3 rounded-lg bg-gradient-to-br from-primary/5 via-primary/5 to-[oklch(0.94_0.05_175)] border border-primary/15">
          <div className="flex items-start justify-between mb-2">
            <div className="text-[11.5px] font-semibold text-foreground">Casos del mes</div>
            <button className="text-muted-foreground hover:text-foreground cursor-pointer"><X className="size-3" /></button>
          </div>
          <div className="text-[10.5px] text-muted-foreground leading-snug mb-2">
            186 activos · 12 ingresos nuevos este mes.
          </div>
          <div className="h-1 rounded-full bg-primary/10 overflow-hidden mb-2">
            <div className="h-full bg-primary rounded-full" style={{ width: "72%" }} />
          </div>
          <div className="flex items-center justify-between">
            <button className="text-[10.5px] text-muted-foreground hover:text-foreground cursor-pointer">Ocultar</button>
            <button className="text-[10.5px] font-semibold text-primary hover:underline cursor-pointer">Ver reporte</button>
          </div>
        </div>
      )}

      {/* User profile */}
      <div className={cn(
        "border-t border-sidebar-border flex items-center gap-2.5 px-3 py-3",
        collapsed && "justify-center"
      )}>
        <div className="size-9 rounded-full bg-primary grid place-items-center text-primary-foreground text-[11px] font-bold shrink-0">
          MG
        </div>
        {!collapsed && (
          <>
            <div className="flex-1 min-w-0 leading-tight">
              <div className="text-[12.5px] font-semibold truncate">María García</div>
              <div className="text-[11px] text-muted-foreground truncate">maria.garcia@cepa.cl</div>
            </div>
            <button className="size-7 rounded-md hover:bg-sidebar-accent grid place-items-center text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
              <LogOut className="size-[15px]" />
            </button>
          </>
        )}
      </div>

      {/* Collapse toggle */}
      <div className="border-t border-sidebar-border p-2">
        <button
          onClick={onToggle}
          className={cn(
            "w-full flex items-center gap-2.5 px-2 py-1.5 text-[11.5px] text-muted-foreground hover:text-foreground hover:bg-sidebar-accent rounded-md cursor-pointer",
            collapsed && "justify-center"
          )}
        >
          <ChevronsLeft className={cn("size-4 transition-transform", collapsed && "rotate-180")} />
          {!collapsed && <span>Colapsar menú</span>}
        </button>
      </div>
    </aside>
  )
}

export type { NavKey }
