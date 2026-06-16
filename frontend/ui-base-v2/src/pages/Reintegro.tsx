import { useState } from "react"
import { Search, Download, Plus, RefreshCw, CheckCircle2, Clock, FileText } from "lucide-react"
import { REINTEGROS } from "@/data/seed"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

export function Reintegro() {
  const [q, setQ] = useState("")
  const filtered = REINTEGROS.filter((r) =>
    !q || r.paciente.toLowerCase().includes(q.toLowerCase()) || r.numeroRECA.toLowerCase().includes(q.toLowerCase())
  )

  const kpis = [
    { label: "En proceso", value: REINTEGROS.filter((r) => r.estadoReintegro === "En proceso").length, icon: RefreshCw, tone: "info" },
    { label: "Reintegrados", value: REINTEGROS.filter((r) => r.estadoReintegro === "Reintegrado").length, icon: CheckCircle2, tone: "success" },
    { label: "RECA pendientes", value: REINTEGROS.filter((r) => r.verificacion === "Pendiente").length, icon: Clock, tone: "warning" },
    { label: "Medidas verificadas", value: REINTEGROS.filter((r) => r.verificacion === "Verificada").length, icon: FileText, tone: "primary" },
  ]

  const tones: Record<string, string> = {
    primary: "bg-primary/10 text-primary",
    info: "bg-[oklch(0.94_0.04_230)] text-[oklch(0.42_0.14_230)]",
    success: "bg-[oklch(0.94_0.05_155)] text-[oklch(0.36_0.12_155)]",
    warning: "bg-[oklch(0.96_0.08_85)] text-[oklch(0.48_0.16_75)]",
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Seguimiento de reintegro</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            RECA, medidas correctivas, verificación y cierre de caso
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Download /> Exportar</Button>
          <Button size="sm"><Plus /> Solicitar RECA</Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {kpis.map((k) => (
          <Card key={k.label} className="hover:shadow-sm transition-shadow">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={cn("size-10 rounded-lg grid place-items-center shrink-0", tones[k.tone])}>
                <k.icon className="size-[18px]" />
              </div>
              <div>
                <div className="text-[22px] font-bold leading-none tracking-tight">{k.value}</div>
                <div className="text-[11.5px] text-muted-foreground mt-1">{k.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-[280px]">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Paciente, empresa, RECA…" className="h-9 pl-8 text-[13px]" />
        </div>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>Estado: Todos</option><option>En proceso</option><option>Reintegrado</option><option>Pendiente</option>
        </select>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>Tipo RECA: Todos</option><option>EP</option><option>EC</option>
        </select>
        <Badge variant="neutral" className="ml-auto">{filtered.length} casos</Badge>
      </div>

      {/* Table */}
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/30 border-b text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="text-left px-4 py-3">Paciente</th>
                <th className="text-left px-4 py-3">Derivación</th>
                <th className="text-left px-4 py-3">RECA</th>
                <th className="text-left px-4 py-3">Tipo</th>
                <th className="text-left px-4 py-3">Riesgos calificados</th>
                <th className="text-left px-4 py-3">Medidas</th>
                <th className="text-left px-4 py-3">Verificación</th>
                <th className="text-left px-4 py-3">Estado</th>
                <th className="text-left px-4 py-3">F. reintegro</th>
                <th className="text-left px-4 py-3">Alta</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.folio} className="border-b hover:bg-muted/40 cursor-pointer transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-[12.5px]">{r.paciente}</div>
                    <div className="text-[10.5px] text-muted-foreground mono">Folio {r.folio}</div>
                  </td>
                  <td className="px-4 py-3"><Badge variant="neutral">{r.tipoDerivacion}</Badge></td>
                  <td className="px-4 py-3">
                    <div className="mono text-[12px] font-semibold">{r.numeroRECA}</div>
                    <div className="text-[10.5px] text-muted-foreground mono">{r.fechaRECA}</div>
                  </td>
                  <td className="px-4 py-3"><Badge variant="purple">{r.tipoRECA}</Badge></td>
                  <td className="px-4 py-3 text-[12px]">{r.riesgosCalificados}</td>
                  <td className="px-4 py-3">
                    <Badge variant={r.medidasCorrectivas === "Implementadas" ? "success" : r.medidasCorrectivas === "Parciales" ? "info" : "warning"}>
                      {r.medidasCorrectivas}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={r.verificacion === "Verificada" ? "success" : r.verificacion === "En proceso" ? "info" : "warning"}>
                      {r.verificacion}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={r.estadoReintegro === "Reintegrado" ? "success" : r.estadoReintegro === "En proceso" ? "info" : "warning"}>
                      {r.estadoReintegro}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground">{r.fechaReintegro}</td>
                  <td className="px-4 py-3 text-[12px]">{r.tipoAlta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
