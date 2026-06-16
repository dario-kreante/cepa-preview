import { useState } from "react"
import { Search, Download, Share2, Filter } from "lucide-react"
import { AUDIT_ROWS } from "@/data/seed"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

function Dot({ state }: { state: string }) {
  const map: Record<string, string> = {
    "Realizada": "bg-[oklch(0.64_0.14_155)]",
    "Pendiente": "bg-[oklch(0.72_0.15_80)]",
    "En proceso": "bg-[oklch(0.56_0.14_230)]",
    "Enviado": "bg-[oklch(0.64_0.14_155)]",
    "Respondida": "bg-[oklch(0.64_0.14_155)]",
    "No aplica": "bg-muted-foreground",
    "Activo": "bg-[oklch(0.64_0.14_155)]",
    "En tratamiento": "bg-[oklch(0.56_0.14_230)]",
    "Cerrado": "bg-muted-foreground",
    "Derivado": "bg-[oklch(0.60_0.16_290)]",
    "Sí": "bg-[oklch(0.64_0.14_155)]",
    "No": "bg-muted-foreground",
  }
  const text: Record<string, string> = {
    "Realizada": "text-[oklch(0.36_0.12_155)]",
    "Pendiente": "text-[oklch(0.48_0.16_75)]",
    "En proceso": "text-[oklch(0.42_0.14_230)]",
    "Enviado": "text-[oklch(0.36_0.12_155)]",
    "Respondida": "text-[oklch(0.36_0.12_155)]",
    "No aplica": "text-muted-foreground",
    "Activo": "text-[oklch(0.36_0.12_155)]",
    "En tratamiento": "text-[oklch(0.42_0.14_230)]",
    "Cerrado": "text-muted-foreground",
    "Derivado": "text-[oklch(0.42_0.16_290)]",
    "Sí": "text-[oklch(0.36_0.12_155)]",
    "No": "text-muted-foreground",
  }
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-[11px] font-semibold whitespace-nowrap", text[state] || "")}>
      <span className={cn("size-1.5 rounded-full shrink-0", map[state] || "bg-muted-foreground")} />
      {state}
    </span>
  )
}

export function Auditoria() {
  const [q, setQ] = useState("")
  const filtered = AUDIT_ROWS.filter((r) =>
    !q || r.paciente.toLowerCase().includes(q.toLowerCase()) || r.rut.includes(q) || r.folio.includes(q)
  )

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Auditoría · Vista consolidada</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Trazabilidad del proceso completo por paciente · DIEP → Alta
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Filter /> Filtros</Button>
          <Button variant="outline" size="sm"><Download /> Exportar Excel</Button>
          <Button size="sm"><Share2 /> Compartir con ISL</Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-[280px]">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Paciente, RUT, folio…" className="h-9 pl-8 text-[13px]" />
        </div>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>Mes: Todos</option><option>Enero</option><option>Febrero</option><option>Marzo</option><option>Abril</option>
        </select>
        <select className="h-9 px-3 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer font-medium">
          <option>Estado: Todos</option><option>Activo</option><option>En tratamiento</option><option>Pendiente</option><option>Cerrado</option>
        </select>
        <Badge variant="neutral" className="ml-auto">{filtered.length} pacientes</Badge>
      </div>

      {/* Table */}
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto max-h-[calc(100vh-340px)]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card z-10 shadow-[0_1px_0_0_var(--border)]">
              <tr className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th rowSpan={2} className="text-left px-4 py-3 bg-muted/30 border-b">Folio</th>
                <th rowSpan={2} className="text-left px-4 py-3 bg-muted/30 border-b">Paciente</th>
                <th rowSpan={2} className="text-left px-4 py-3 bg-muted/30 border-b">RUT</th>
                <th rowSpan={2} className="text-left px-4 py-3 bg-muted/30 border-b">Mes</th>
                <th colSpan={3} className="text-center px-3 py-2 bg-primary/5 border-b border-l text-primary">Ingreso</th>
                <th colSpan={2} className="text-center px-3 py-2 bg-[oklch(0.94_0.04_230)]/40 border-b border-l text-[oklch(0.42_0.14_230)]">Evaluaciones</th>
                <th colSpan={3} className="text-center px-3 py-2 bg-[oklch(0.96_0.08_85)]/40 border-b border-l text-[oklch(0.48_0.16_75)]">Informe ISL</th>
                <th colSpan={2} className="text-center px-3 py-2 bg-[oklch(0.95_0.05_290)]/40 border-b border-l text-[oklch(0.42_0.16_290)]">RECA</th>
                <th colSpan={3} className="text-center px-3 py-2 bg-[oklch(0.94_0.05_155)]/40 border-b border-l text-[oklch(0.36_0.12_155)]">Cierre</th>
              </tr>
              <tr className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground border-b">
                <th className="text-left px-3 py-2 border-l">F. ingreso</th>
                <th className="text-left px-3 py-2">DIEP</th>
                <th className="text-left px-3 py-2">Acogida</th>
                <th className="text-left px-3 py-2 border-l">Médica</th>
                <th className="text-left px-3 py-2">Psi.</th>
                <th className="text-left px-3 py-2 border-l">Plazo</th>
                <th className="text-left px-3 py-2">Obstac.</th>
                <th className="text-left px-3 py-2">Envío</th>
                <th className="text-left px-3 py-2 border-l">Tipo</th>
                <th className="text-left px-3 py-2">N°</th>
                <th className="text-left px-3 py-2 border-l">Estado</th>
                <th className="text-left px-3 py-2">Alta</th>
                <th className="text-left px-3 py-2">Encuesta</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={r.folio} className={cn("border-b hover:bg-muted/40 cursor-pointer transition-colors", i % 2 === 1 && "bg-muted/10")}>
                  <td className="px-4 py-3 mono text-[12px] font-semibold text-muted-foreground">{r.folio}</td>
                  <td className="px-4 py-3 font-semibold text-[12.5px] whitespace-nowrap">{r.paciente}</td>
                  <td className="px-4 py-3 mono text-[11px]">{r.rut}</td>
                  <td className="px-4 py-3 text-[12px]">{r.mes}</td>
                  <td className="px-3 py-3 mono text-[11px] border-l text-muted-foreground">{r.fechaIngreso}</td>
                  <td className="px-3 py-3"><Dot state={r.diep} /></td>
                  <td className="px-3 py-3"><Dot state={r.acogida} /></td>
                  <td className="px-3 py-3 border-l"><Dot state={r.evalMed} /></td>
                  <td className="px-3 py-3"><Dot state={r.evalPsi} /></td>
                  <td className="px-3 py-3 mono text-[11px] border-l">
                    <span className={cn(r.plazoInforme > 28 && "text-destructive font-semibold")}>{r.plazoInforme}d</span>
                  </td>
                  <td className="px-3 py-3">
                    {r.obstaculizacion ? <Badge variant="destructive">Sí</Badge> : <Badge variant="neutral">No</Badge>}
                  </td>
                  <td className="px-3 py-3"><Dot state={r.envioInforme} /></td>
                  <td className="px-3 py-3 border-l"><Badge variant="purple">{r.recaTipo}</Badge></td>
                  <td className="px-3 py-3 mono text-[11px]">{r.recaNumero}</td>
                  <td className="px-3 py-3 border-l"><Dot state={r.estado} /></td>
                  <td className="px-3 py-3 text-[11.5px]">{r.tipoAlta}</td>
                  <td className="px-3 py-3"><Dot state={r.encuestaSatisfaccion} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
