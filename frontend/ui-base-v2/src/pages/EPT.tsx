import { useState } from "react"
import { Search, Mail, Download, Plus, Filter, Briefcase, AlertTriangle, Users, Send } from "lucide-react"
import { EPTS } from "@/data/seed"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

export function EPT() {
  const [q, setQ] = useState("")
  const filtered = EPTS.filter((e) =>
    !q ||
    e.numero.toLowerCase().includes(q.toLowerCase()) ||
    e.paciente.toLowerCase().includes(q.toLowerCase()) ||
    e.razonSocial.toLowerCase().includes(q.toLowerCase())
  )

  const kpis = [
    { label: "EPT en proceso", value: EPTS.length, icon: Briefcase, tone: "primary" },
    { label: "Pendientes ISL", value: EPTS.filter((e) => e.estadoEnvio !== "Enviado").length, icon: Send, tone: "warning" },
    { label: "Con testigos", value: EPTS.filter((e) => e.testigos).length, icon: Users, tone: "info" },
    { label: "Plazos excedidos", value: 2, icon: AlertTriangle, tone: "danger" },
  ]

  const tones: Record<string, string> = {
    primary: "bg-primary/10 text-primary",
    warning: "bg-[oklch(0.96_0.08_85)] text-[oklch(0.48_0.16_75)]",
    info: "bg-[oklch(0.94_0.04_230)] text-[oklch(0.42_0.14_230)]",
    danger: "bg-destructive/10 text-destructive",
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Seguimiento EPT</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Evaluaciones de Puesto de Trabajo · Gestión con empleadores e ISL
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Mail /> Plantillas correo</Button>
          <Button variant="outline" size="sm"><Download /> Reporte mensual</Button>
          <Button size="sm"><Plus /> Nueva EPT</Button>
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
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="EPT, paciente o empresa…" className="h-9 pl-8 text-[13px]" />
        </div>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>Tipo: Todos</option><option>EM</option><option>EPS</option><option>EM+EPS</option>
        </select>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>EPTista: Todos</option><option>Ps. Lorena Baeza</option><option>Ps. Tomás Jiménez</option><option>Ps. Sofía Retamal</option>
        </select>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>Estado ISL: Todos</option><option>Enviado</option><option>Pendiente</option>
        </select>
        <Button variant="outline" size="sm" className="h-9"><Filter /> Más filtros</Button>
        <Badge variant="neutral" className="ml-auto">{filtered.length} EPTs</Badge>
      </div>

      {/* Table */}
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/30 border-b text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="text-left px-4 py-3">Nº EPT</th>
                <th className="text-left px-4 py-3">Paciente</th>
                <th className="text-left px-4 py-3">Empresa</th>
                <th className="text-left px-4 py-3">Tipo</th>
                <th className="text-left px-4 py-3">EPTista</th>
                <th className="text-left px-4 py-3">Factor riesgo</th>
                <th className="text-left px-4 py-3">Entrevistas</th>
                <th className="text-left px-4 py-3">Plazos</th>
                <th className="text-left px-4 py-3">Envío ISL</th>
                <th className="text-left px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr key={e.folio} className="border-b hover:bg-muted/40 cursor-pointer transition-colors">
                  <td className="px-4 py-3">
                    <div className="mono font-semibold text-[12px]">{e.numero}</div>
                    <div className="text-[10.5px] text-muted-foreground mono">Folio {e.folio}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-[12.5px]">{e.paciente}</div>
                    <div className="text-[10.5px] text-muted-foreground mono">{e.rut}</div>
                  </td>
                  <td className="px-4 py-3 max-w-[200px]">
                    <div className="text-[12.5px] truncate">{e.razonSocial}</div>
                    <div className="text-[10.5px] text-muted-foreground truncate">{e.unidad} · {e.cargo}</div>
                  </td>
                  <td className="px-4 py-3"><Badge variant="info">{e.tipoEvaluacion}</Badge></td>
                  <td className="px-4 py-3 text-[12px]">{e.eptista}</td>
                  <td className="px-4 py-3 text-[12px]">{e.factorRiesgo}</td>
                  <td className="px-4 py-3 mono text-[12px]">
                    {e.nEntrevistas}{e.testigos && (
                      <span className="text-muted-foreground"> +{e.cantidadTestigos}t</span>
                    )}
                  </td>
                  <td className="px-4 py-3 mono text-[11px] text-muted-foreground">
                    <span className={cn(e.plazoPortalISL > 25 && "text-destructive font-semibold")}>
                      ISL {e.plazoPortalISL}d
                    </span>
                    {" · "}
                    <span>Inf {e.plazoInformeEPT}d</span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={e.estadoEnvio === "Enviado" ? "success" : e.estadoEnvio === "En revisión" ? "info" : "warning"}>
                      {e.estadoEnvio}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={e.estadoCaso === "Activo" ? "success" : e.estadoCaso === "En tratamiento" ? "info" : e.estadoCaso === "Cerrado" ? "neutral" : "warning"}>
                      {e.estadoCaso}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
