import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { LICENCIAS, RECETAS, CONTROLES } from "@/data/seed"
import { Download, Plus, Pill, Filter, Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useState } from "react"
import { cn } from "@/lib/utils"

function PageHeader({ title, subtitle, primaryLabel }: { title: string; subtitle: string; primaryLabel?: string }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">{title}</h1>
        <p className="text-[13px] text-muted-foreground mt-1">{subtitle}</p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm"><Download /> Exportar</Button>
        {primaryLabel && <Button size="sm"><Plus /> {primaryLabel}</Button>}
      </div>
    </div>
  )
}

function FiltersBar({ q, onQ, placeholder, count }: { q: string; onQ: (v: string) => void; placeholder: string; count: number }) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <div className="relative w-[280px]">
        <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
        <Input value={q} onChange={(e) => onQ(e.target.value)} placeholder={placeholder} className="h-9 pl-8 text-[13px]" />
      </div>
      <Button variant="outline" size="sm" className="h-9"><Filter /> Filtros</Button>
      <Badge variant="neutral" className="ml-auto">{count} registros</Badge>
    </div>
  )
}

export function Licencias() {
  const [q, setQ] = useState("")
  const filtered = LICENCIAS.filter((l) => !q || l.paciente.toLowerCase().includes(q.toLowerCase()) || l.numero.toLowerCase().includes(q.toLowerCase()))
  return (
    <div>
      <PageHeader
        title="Licencias médicas"
        subtitle={`${LICENCIAS.length} licencias registradas · ${LICENCIAS.filter((l) => l.estado === "Vigente").length} vigentes · ${LICENCIAS.reduce((s, l) => s + l.dias, 0)} días totales`}
        primaryLabel="Nueva licencia"
      />
      <FiltersBar q={q} onQ={setQ} placeholder="Buscar LM, paciente…" count={filtered.length} />
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/30 border-b text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Folio</th>
                <th className="text-left px-4 py-3">Paciente</th>
                <th className="text-left px-4 py-3">N° LM</th>
                <th className="text-left px-4 py-3">Tipo</th>
                <th className="text-left px-4 py-3">Inicio</th>
                <th className="text-left px-4 py-3">Fin</th>
                <th className="text-left px-4 py-3">Días</th>
                <th className="text-left px-4 py-3">Médico</th>
                <th className="text-left px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((l, i) => (
                <tr key={l.numero} className={cn("border-b hover:bg-muted/40 transition-colors cursor-pointer", i % 2 === 1 && "bg-muted/10")}>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground font-semibold">{l.folio}</td>
                  <td className="px-4 py-3 font-semibold text-[12.5px]">{l.paciente}</td>
                  <td className="px-4 py-3 mono text-[12px]">{l.numero}</td>
                  <td className="px-4 py-3"><Badge variant="info">{l.tipoLicencia}</Badge></td>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground">{l.inicio}</td>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground">{l.fin}</td>
                  <td className="px-4 py-3 mono text-[12px] font-semibold">{l.dias}</td>
                  <td className="px-4 py-3 text-[12px]">{l.medico}</td>
                  <td className="px-4 py-3"><Badge variant={l.estado === "Vigente" ? "success" : l.estado === "Rechazada" ? "destructive" : "neutral"}>{l.estado}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

export function Farmacos() {
  const [q, setQ] = useState("")
  const filtered = RECETAS.filter((r) => !q || r.paciente.toLowerCase().includes(q.toLowerCase()) || r.farmaco.toLowerCase().includes(q.toLowerCase()))
  return (
    <div>
      <PageHeader
        title="Gestión de fármacos"
        subtitle={`${RECETAS.length} recetas · ${RECETAS.filter((r) => r.estado === "Vigente").length} vigentes · ${RECETAS.filter((r) => r.estado === "Por vencer").length} por vencer`}
        primaryLabel="Nueva receta"
      />
      <FiltersBar q={q} onQ={setQ} placeholder="Paciente o fármaco…" count={filtered.length} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((r, i) => (
          <Card key={i} className="hover:shadow-sm transition-shadow">
            <CardContent className="p-4">
              <div className="flex items-start gap-3 mb-3">
                <div className="size-10 rounded-lg bg-[oklch(0.95_0.05_290)] text-[oklch(0.42_0.16_290)] grid place-items-center shrink-0">
                  <Pill className="size-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[13px] leading-tight">{r.farmaco}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{r.dosis}</div>
                </div>
                <Badge variant={r.estado === "Vigente" ? "success" : r.estado === "Por vencer" ? "warning" : "destructive"}>{r.estado}</Badge>
              </div>
              <div className="text-[12px] pt-3 border-t">
                <div className="font-semibold text-[12.5px] truncate">{r.paciente}</div>
                <div className="text-muted-foreground mono text-[10.5px] mt-1 flex items-center justify-between">
                  <span>Folio {r.folio}</span>
                  <span>{r.vigenciaHasta}</span>
                </div>
                <div className="text-muted-foreground text-[11px] mt-1">{r.medico}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function Controles() {
  const [q, setQ] = useState("")
  const filtered = CONTROLES.filter((c) => !q || c.paciente.toLowerCase().includes(q.toLowerCase()))
  return (
    <div>
      <PageHeader
        title="Controles médicos"
        subtitle={`${CONTROLES.length} controles · ${CONTROLES.filter((c) => c.estado === "Agendado").length} agendados · ${CONTROLES.filter((c) => c.estado === "No asistió").length} no asistieron`}
        primaryLabel="Nuevo control"
      />
      <FiltersBar q={q} onQ={setQ} placeholder="Buscar paciente, profesional…" count={filtered.length} />
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/30 border-b text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Folio</th>
                <th className="text-left px-4 py-3">Paciente</th>
                <th className="text-left px-4 py-3">Tipo</th>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-left px-4 py-3">Hora</th>
                <th className="text-left px-4 py-3">Profesional</th>
                <th className="text-left px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={i} className={cn("border-b hover:bg-muted/40 transition-colors cursor-pointer", i % 2 === 1 && "bg-muted/10")}>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground font-semibold">{c.folio}</td>
                  <td className="px-4 py-3 font-semibold text-[12.5px]">{c.paciente}</td>
                  <td className="px-4 py-3 text-[12px]">{c.tipo}</td>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground">{c.fecha}</td>
                  <td className="px-4 py-3 mono text-[12px] font-semibold">{c.hora}</td>
                  <td className="px-4 py-3 text-[12px]">{c.profesional}</td>
                  <td className="px-4 py-3"><Badge variant={c.estado === "Realizado" ? "success" : c.estado === "No asistió" ? "destructive" : c.estado === "Reagendado" ? "warning" : "info"}>{c.estado}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
