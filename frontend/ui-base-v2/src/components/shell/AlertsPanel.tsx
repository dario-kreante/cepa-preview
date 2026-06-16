import { useState } from "react"
import { AlertCircle, Clock, Bell, CheckCircle2, Plus, FileText, Pill } from "lucide-react"
import { ALERTS, type Alert } from "@/data/seed"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const ICONS = {
  danger: AlertCircle,
  warn: Clock,
  info: Bell,
  success: CheckCircle2,
}

const STYLES: Record<string, string> = {
  danger: "bg-destructive/10 text-destructive",
  warn: "bg-[oklch(0.96_0.08_85)] text-[oklch(0.52_0.16_75)]",
  info: "bg-[oklch(0.94_0.04_230)] text-[oklch(0.42_0.14_230)]",
  success: "bg-[oklch(0.94_0.05_155)] text-[oklch(0.40_0.12_155)]",
}

export function AlertsPanel({ onItemClick }: { onItemClick: (a: Alert) => void }) {
  const [tab, setTab] = useState<"todas" | "danger" | "warn" | "info">("todas")
  const filtered = tab === "todas" ? ALERTS : ALERTS.filter((a) => a.tipo === tab)
  const criticas = ALERTS.filter((a) => a.tipo === "danger").length

  return (
    <aside className="w-80 shrink-0 bg-card border-l flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-5 h-15 border-b">
        <Bell className="size-4 text-primary" />
        <h3 className="text-sm font-bold">Alertas y tareas</h3>
        <span className="ml-auto size-5 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold grid place-items-center">
          {criticas}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-2 border-b bg-muted/30">
        {(["todas", "danger", "warn", "info"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "flex-1 text-[11px] font-semibold py-1.5 rounded-md transition-colors cursor-pointer",
              tab === t ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
            )}
          >
            {t === "todas" ? "Todas" : t === "danger" ? "Críticas" : t === "warn" ? "Próximas" : "Info"}
          </button>
        ))}
      </div>

      {/* Date header */}
      <div className="px-5 py-2 bg-muted/40 border-b">
        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
          Hoy · Viernes 18 abr 2026
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto">
        {filtered.map((a) => {
          const Icon = ICONS[a.tipo]
          return (
            <button
              key={a.id}
              onClick={() => onItemClick(a)}
              className="w-full text-left px-5 py-3 border-b hover:bg-muted/50 transition-colors flex gap-3 cursor-pointer"
            >
              <div className={cn("size-8 rounded-lg grid place-items-center shrink-0", STYLES[a.tipo])}>
                <Icon className="size-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-semibold leading-tight mb-0.5">{a.titulo}</div>
                <div className="text-[11px] text-muted-foreground truncate">
                  {a.paciente} · Folio {a.folio}
                </div>
                <div className="flex items-center gap-1.5 mt-1 text-[10.5px] text-muted-foreground">
                  <span>{a.modulo}</span>
                  <span>•</span>
                  <span>{a.hora}</span>
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* Quick actions */}
      <div className="p-4 border-t bg-muted/30">
        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
          Accesos rápidos
        </div>
        <div className="flex flex-col gap-1">
          <Button variant="ghost" size="sm" className="justify-start h-8 text-[12px]">
            <Plus className="size-3.5" /> Nuevo ingreso
          </Button>
          <Button variant="ghost" size="sm" className="justify-start h-8 text-[12px]">
            <FileText className="size-3.5" /> Registrar licencia
          </Button>
          <Button variant="ghost" size="sm" className="justify-start h-8 text-[12px]">
            <Pill className="size-3.5" /> Nueva receta
          </Button>
        </div>
      </div>
    </aside>
  )
}
