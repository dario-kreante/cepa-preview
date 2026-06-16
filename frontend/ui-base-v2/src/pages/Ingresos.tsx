import { useState } from "react"
import { Search, Download, Filter, Plus, ChevronLeft, ChevronRight, ArrowDown, HelpCircle, Edit3, Trash2, ArrowUpDown } from "lucide-react"
import { PATIENTS, type Patient } from "@/data/seed"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

const STATE_VARIANTS: Record<Patient["estado"], { dot: string; text: string }> = {
  "Activo":         { dot: "bg-[oklch(0.64_0.14_155)]", text: "text-[oklch(0.36_0.12_155)]" },
  "En tratamiento": { dot: "bg-[oklch(0.56_0.14_230)]", text: "text-[oklch(0.42_0.14_230)]" },
  "Pendiente":      { dot: "bg-[oklch(0.72_0.15_80)]",  text: "text-[oklch(0.48_0.16_75)]" },
  "Cerrado":        { dot: "bg-muted-foreground",       text: "text-muted-foreground" },
  "Derivado":       { dot: "bg-[oklch(0.60_0.16_290)]", text: "text-[oklch(0.42_0.16_290)]" },
}

function StateDot({ estado }: { estado: Patient["estado"] }) {
  const s = STATE_VARIANTS[estado]
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-background border text-[11px] font-semibold", s.text)}>
      <span className={cn("size-1.5 rounded-full", s.dot)} />
      {estado}
    </span>
  )
}

function PatientAvatar({ p }: { p: Patient }) {
  const colors = [
    "from-[oklch(0.75_0.12_290)] to-[oklch(0.55_0.14_260)]",
    "from-[oklch(0.72_0.14_180)] to-[oklch(0.52_0.12_195)]",
    "from-[oklch(0.75_0.10_80)] to-[oklch(0.58_0.14_55)]",
    "from-[oklch(0.75_0.14_25)] to-[oklch(0.58_0.18_10)]",
    "from-[oklch(0.75_0.12_155)] to-[oklch(0.55_0.14_155)]",
    "from-[oklch(0.72_0.14_230)] to-[oklch(0.50_0.16_235)]",
  ]
  const c = colors[parseInt(p.folio) % colors.length]
  return (
    <div className={cn("size-9 rounded-full bg-gradient-to-br grid place-items-center text-white text-[11px] font-bold shrink-0 shadow-xs", c)}>
      {p.inicial}
    </div>
  )
}

export function Ingresos({ onOpenPatient }: { onOpenPatient: (p: Patient) => void }) {
  const [q, setQ] = useState("")
  const [estado, setEstado] = useState("Todos")
  const [region, setRegion] = useState("Todas")
  const [derivacion, setDerivacion] = useState("Todas")
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const perPage = 10

  const filtered = PATIENTS.filter((p) => {
    if (estado !== "Todos" && p.estado !== estado) return false
    if (region !== "Todas" && p.region !== region) return false
    if (derivacion !== "Todas" && p.tipoDerivacion !== derivacion) return false
    if (q) {
      const qq = q.toLowerCase()
      return p.nombre.toLowerCase().includes(qq) || p.rut.includes(qq) || p.folio.includes(qq)
    }
    return true
  })

  const pages = Math.ceil(filtered.length / perPage)
  const paged = filtered.slice(page * perPage, (page + 1) * perPage)

  const regions = Array.from(new Set(PATIENTS.map((p) => p.region)))
  const derivs = Array.from(new Set(PATIENTS.map((p) => p.tipoDerivacion)))

  const toggleRow = (folio: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    const next = new Set(selected)
    if (next.has(folio)) next.delete(folio)
    else next.add(folio)
    setSelected(next)
  }
  const toggleAll = () => {
    if (selected.size === paged.length) setSelected(new Set())
    else setSelected(new Set(paged.map((p) => p.folio)))
  }

  const pageNumbers = (() => {
    if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
    if (page < 3) return [1, 2, 3, 4, "…", pages - 1, pages]
    if (page >= pages - 4) return [1, 2, "…", pages - 3, pages - 2, pages - 1, pages]
    return [1, 2, "…", page, page + 1, page + 2, "…", pages]
  })()

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[22px] font-semibold tracking-tight">Ingresos y pacientes</h1>
            <Badge variant="default" className="text-[10.5px]">
              {PATIENTS.length} registros
            </Badge>
          </div>
          <p className="text-[13px] text-muted-foreground mt-1">
            Administra los pacientes del centro, su evaluación y estado clínico.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Download /> Exportar</Button>
          <Button size="sm"><Plus /> Nuevo ingreso</Button>
        </div>
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-[280px]">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(0) }}
            placeholder="Buscar RUT, folio o nombre…"
            className="h-9 pl-8 text-[13px]"
          />
        </div>
        <Select label="Estado" value={estado} onChange={(v) => { setEstado(v); setPage(0) }}
          options={["Todos","Activo","En tratamiento","Pendiente","Cerrado","Derivado"]} />
        <Select label="Región" value={region} onChange={(v) => { setRegion(v); setPage(0) }}
          options={["Todas", ...regions]} />
        <Select label="Derivación" value={derivacion} onChange={(v) => { setDerivacion(v); setPage(0) }}
          options={["Todas", ...derivs]} />
        <Button variant="outline" size="sm" className="h-9"><Filter /> Más filtros</Button>
      </div>

      {/* Table */}
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/30 border-b text-[11px] font-semibold text-muted-foreground">
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.size > 0 && selected.size === paged.length}
                    onChange={toggleAll}
                    className="size-4 rounded border-border accent-primary cursor-pointer"
                  />
                </th>
                <Th>Folio <ArrowDown className="size-3" /></Th>
                <Th>Paciente</Th>
                <Th>Estado <ArrowUpDown className="size-3" /></Th>
                <Th>Diagnóstico <HelpCircle className="size-3" /></Th>
                <Th>RUT</Th>
                <Th>Región</Th>
                <Th>Derivación</Th>
                <Th>Ingreso</Th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {paged.map((p) => (
                <tr
                  key={p.folio}
                  onClick={() => onOpenPatient(p)}
                  className="border-b hover:bg-muted/40 cursor-pointer transition-colors group"
                >
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.has(p.folio)}
                      onChange={(e) => toggleRow(p.folio, e as any)}
                      className="size-4 rounded border-border accent-primary cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground font-medium">{p.folio}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <PatientAvatar p={p} />
                      <div className="min-w-0">
                        <div className="font-semibold text-[13px] truncate">{p.nombre}</div>
                        <div className="text-[11.5px] text-muted-foreground truncate">
                          {p.edad} años · {p.genero} · {p.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StateDot estado={p.estado} /></td>
                  <td className="px-4 py-3">
                    <div className="text-[12.5px] max-w-[200px] truncate">{p.diagnostico.split("(")[0].trim()}</div>
                    <div className="text-[10.5px] text-muted-foreground mono">{p.diagnostico.match(/\((.*?)\)/)?.[1]}</div>
                  </td>
                  <td className="px-4 py-3 mono text-[12px]">{p.rut}</td>
                  <td className="px-4 py-3 text-[12.5px]">{p.region}</td>
                  <td className="px-4 py-3">
                    <Badge variant="neutral">{p.tipoDerivacion}</Badge>
                  </td>
                  <td className="px-4 py-3 mono text-[12px] text-muted-foreground">{p.fechaIngreso}</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="size-7 rounded-md hover:bg-muted grid place-items-center text-muted-foreground hover:text-foreground cursor-pointer">
                        <Trash2 className="size-3.5" />
                      </button>
                      <button className="size-7 rounded-md hover:bg-muted grid place-items-center text-muted-foreground hover:text-foreground cursor-pointer">
                        <Edit3 className="size-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t bg-card">
          <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
            <ChevronLeft /> Anterior
          </Button>
          <div className="flex items-center gap-1">
            {pageNumbers.map((n, i) =>
              n === "…" ? (
                <span key={i} className="px-2 text-muted-foreground text-[12px]">…</span>
              ) : (
                <button
                  key={i}
                  onClick={() => setPage((n as number) - 1)}
                  className={cn(
                    "size-8 rounded-md text-[12.5px] font-semibold cursor-pointer",
                    page === (n as number) - 1
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  {n}
                </button>
              )
            )}
          </div>
          <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1}>
            Siguiente <ChevronRight />
          </Button>
        </div>
      </Card>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider">
      <span className="inline-flex items-center gap-1.5">{children}</span>
    </th>
  )
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {label}: {o}
          </option>
        ))}
      </select>
      <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
    </div>
  )
}
