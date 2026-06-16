import { useState } from "react"
import { Calendar, Download, Plus, ChevronLeft, ChevronRight } from "lucide-react"
import { AGENDA_PROFESIONALES, AGENDA_SLOTS } from "@/data/seed"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const HORAS = ["08:30", "09:30", "10:30", "11:30", "12:30", "14:30", "15:30", "16:30", "17:30"]
const DIAS = ["L 14", "M 15", "X 16", "J 17", "V 18", "L 21", "M 22"]

export function Agenda() {
  const [diaSel, setDiaSel] = useState(4)
  const confirmadas = AGENDA_SLOTS.filter((s) => s.estado === "Confirmada").length
  const enEspera = AGENDA_SLOTS.filter((s) => s.estado === "En espera").length

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[22px] font-semibold tracking-tight">Agendamiento</h1>
            <Badge variant="default">Viernes 18 abril</Badge>
          </div>
          <p className="text-[13px] text-muted-foreground mt-1">
            Agenda multi-profesional · {AGENDA_PROFESIONALES.length} profesionales activos
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Calendar /> Vista semanal</Button>
          <Button variant="outline" size="sm"><Download /> Exportar iCal</Button>
          <Button size="sm"><Plus /> Nueva cita</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5">
        {/* Calendar */}
        <Card className="p-0 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b bg-card">
            <div>
              <h3 className="text-[14px] font-semibold tracking-tight">Agenda del día</h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">9 bloques horarios · {AGENDA_SLOTS.length} citas</p>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="icon-sm"><ChevronLeft /></Button>
              <div className="flex items-center gap-0.5 mx-1">
                {DIAS.map((d, i) => (
                  <button
                    key={d}
                    onClick={() => setDiaSel(i)}
                    className={cn(
                      "h-8 px-3 rounded-md text-[12px] font-semibold transition-colors cursor-pointer",
                      i === diaSel
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    )}
                  >
                    {d}
                  </button>
                ))}
              </div>
              <Button variant="outline" size="icon-sm"><ChevronRight /></Button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <div
              className="grid min-w-[900px]"
              style={{ gridTemplateColumns: `80px repeat(${AGENDA_PROFESIONALES.length}, minmax(140px, 1fr))` }}
            >
              {/* header */}
              <div className="bg-muted/30 border-b" />
              {AGENDA_PROFESIONALES.map((p) => (
                <div key={p.key} className="bg-muted/30 border-b border-l px-3 py-3 text-center">
                  <div className="inline-flex items-center gap-2">
                    <span className="size-2.5 rounded-full" style={{ background: p.color }} />
                    <span className="text-[11.5px] font-semibold">{p.nombre.split(" ").slice(0, 3).join(" ")}</span>
                  </div>
                </div>
              ))}

              {/* rows */}
              {HORAS.map((h) => (
                <>
                  <div key={`h-${h}`} className="bg-muted/10 border-b px-3 py-2 text-right text-[11px] font-semibold text-muted-foreground mono self-center">
                    {h}
                  </div>
                  {AGENDA_PROFESIONALES.map((p) => {
                    const slot = AGENDA_SLOTS.find((s) => s.profesional === p.key && s.hora === h)
                    return (
                      <div key={`${p.key}-${h}`} className="border-b border-l p-1.5 min-h-[64px]">
                        {slot && (
                          <button
                            className="w-full h-full text-left rounded-md px-2 py-1.5 transition-shadow hover:shadow-sm cursor-pointer"
                            style={{
                              background: `color-mix(in oklch, ${p.color} 12%, white)`,
                              borderLeft: `3px solid ${p.color}`,
                            }}
                          >
                            <div className="text-[11.5px] font-semibold leading-tight truncate" title={slot.paciente}>
                              {slot.paciente.split(" ").slice(0, 2).join(" ")}
                            </div>
                            <div className="flex items-center gap-1.5 mt-1">
                              <span className="text-[10px] text-muted-foreground truncate">{slot.tipo}</span>
                            </div>
                            <div className="mt-1">
                              <span className={cn(
                                "inline-block text-[9.5px] font-semibold px-1.5 py-0.5 rounded",
                                slot.estado === "Confirmada" && "bg-[oklch(0.94_0.05_155)] text-[oklch(0.36_0.12_155)]",
                                slot.estado === "En espera" && "bg-[oklch(0.96_0.08_85)] text-[oklch(0.48_0.16_75)]",
                                slot.estado === "Reagendada" && "bg-[oklch(0.94_0.04_230)] text-[oklch(0.42_0.14_230)]"
                              )}>
                                {slot.estado}
                              </span>
                            </div>
                          </button>
                        )}
                      </div>
                    )
                  })}
                </>
              ))}
            </div>
          </div>
        </Card>

        {/* Sidebar */}
        <div className="space-y-4">
          <Card className="p-5">
            <h3 className="text-[14px] font-semibold tracking-tight mb-3">Resumen del día</h3>
            <div className="grid grid-cols-2 gap-2">
              <Stat label="Citas" value={AGENDA_SLOTS.length} tone="primary" />
              <Stat label="Confirmadas" value={confirmadas} tone="success" />
              <Stat label="En espera" value={enEspera} tone="warning" />
              <Stat label="Slots libres" value={HORAS.length * AGENDA_PROFESIONALES.length - AGENDA_SLOTS.length} tone="neutral" />
            </div>
          </Card>

          <Card className="p-0 overflow-hidden">
            <div className="px-5 py-3 border-b">
              <h3 className="text-[14px] font-semibold tracking-tight">Profesionales</h3>
            </div>
            <div>
              {AGENDA_PROFESIONALES.map((p) => {
                const pSlots = AGENDA_SLOTS.filter((s) => s.profesional === p.key).length
                const pct = Math.round((pSlots / HORAS.length) * 100)
                return (
                  <div key={p.key} className="px-5 py-2.5 border-b last:border-b-0">
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <span className="size-2.5 rounded-full shrink-0" style={{ background: p.color }} />
                      <span className="text-[12.5px] font-semibold flex-1 truncate">{p.nombre}</span>
                      <span className="text-[11px] font-semibold mono" style={{ color: p.color }}>{pct}%</span>
                    </div>
                    <div className="h-1 rounded-full bg-muted overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: p.color }} />
                    </div>
                    <div className="text-[10.5px] text-muted-foreground mt-1">{pSlots} / {HORAS.length} citas</div>
                  </div>
                )
              })}
            </div>
          </Card>

          <Card className="p-5">
            <h3 className="text-[14px] font-semibold tracking-tight mb-2">Próximo disponible</h3>
            <div className="space-y-2">
              {[
                { n: "Dr. Álvaro Soto", w: "Hoy 13:30" },
                { n: "Ps. Camila Díaz", w: "Hoy 16:30" },
                { n: "Ps. Javiera Pinto", w: "Lun 21, 08:30" },
              ].map((x, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b last:border-b-0 border-dashed">
                  <div>
                    <div className="text-[12.5px] font-semibold">{x.n}</div>
                  </div>
                  <span className="text-[11px] text-muted-foreground mono">{x.w}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone: "primary" | "success" | "warning" | "neutral" }) {
  const styles: Record<string, string> = {
    primary: "bg-primary/10 text-primary",
    success: "bg-[oklch(0.94_0.05_155)] text-[oklch(0.36_0.12_155)]",
    warning: "bg-[oklch(0.96_0.08_85)] text-[oklch(0.48_0.16_75)]",
    neutral: "bg-muted text-muted-foreground",
  }
  return (
    <div className={cn("p-3 rounded-lg", styles[tone])}>
      <div className="text-[20px] font-bold leading-none">{value}</div>
      <div className="text-[11px] font-semibold mt-1 opacity-80">{label}</div>
    </div>
  )
}
