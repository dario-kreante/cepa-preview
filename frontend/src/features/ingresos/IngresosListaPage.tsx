import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useBuscarPacientes } from "./hooks";
import type { components } from "@/types/api";

type PacienteRead = components["schemas"]["PacienteRead"];

const AVATAR_COLORS = [
  "from-[oklch(0.75_0.12_290)] to-[oklch(0.55_0.14_260)]",
  "from-[oklch(0.72_0.14_180)] to-[oklch(0.52_0.12_195)]",
  "from-[oklch(0.75_0.10_80)] to-[oklch(0.58_0.14_55)]",
  "from-[oklch(0.75_0.14_25)] to-[oklch(0.58_0.18_10)]",
  "from-[oklch(0.75_0.12_155)] to-[oklch(0.55_0.14_155)]",
  "from-[oklch(0.72_0.14_230)] to-[oklch(0.50_0.16_235)]",
];

function PatientAvatar({ p }: { p: PacienteRead }) {
  const inicial = p.nombre.trim().charAt(0).toUpperCase();
  const colorIdx = p.id % AVATAR_COLORS.length;
  const c = AVATAR_COLORS[colorIdx];
  return (
    <div
      className={cn(
        "size-9 rounded-full bg-gradient-to-br grid place-items-center text-white text-[11px] font-bold shrink-0 shadow-xs",
        c
      )}
    >
      {inicial}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider">
      <span className="inline-flex items-center gap-1.5">{children}</span>
    </th>
  );
}

const PER_PAGE = 10;

export function IngresosListaPage() {
  const navigate = useNavigate();
  const { rol } = useAuth();
  const puedeCrear = puedeEscribir(rol as Rol);

  const [inputQ, setInputQ] = useState("");
  const [q, setQ] = useState("");
  const [regionFilter, setRegionFilter] = useState("Todas");
  const [page, setPage] = useState(0);

  // 300ms debounce
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(inputQ.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(t);
  }, [inputQ]);

  const { data: results = [], isFetching } = useBuscarPacientes(q);

  // Client-side región filter
  const regions = Array.from(new Set(results.map((p) => p.region))).sort();
  const filtered =
    regionFilter === "Todas"
      ? results
      : results.filter((p) => p.region === regionFilter);

  const pages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const paged = filtered.slice(page * PER_PAGE, (page + 1) * PER_PAGE);

  // Page numbers with ellipsis (same logic as v2)
  const pageNumbers: (number | "…")[] = (() => {
    if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
    if (page < 3) return [1, 2, 3, 4, "…", pages - 1, pages];
    if (page >= pages - 4) return [1, 2, "…", pages - 3, pages - 2, pages - 1, pages];
    return [1, 2, "…", page, page + 1, page + 2, "…", pages];
  })();

  // Seam for Task 10 — swap to drawer open there
  function onOpenPatient(p: PacienteRead) {
    navigate(`/pacientes/${p.id}`);
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[22px] font-semibold tracking-tight">
              Ingresos y pacientes
            </h1>
            {q && !isFetching && (
              <Badge variant="default" className="text-[10.5px]">
                {filtered.length} resultado{filtered.length !== 1 ? "s" : ""}
              </Badge>
            )}
          </div>
          <p className="text-[13px] text-muted-foreground mt-1">
            Administra los pacientes del centro, su evaluación y estado clínico.
          </p>
        </div>
        {puedeCrear && (
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => navigate("/ingresos/nuevo")}>
              <Plus /> Nuevo ingreso
            </Button>
          </div>
        )}
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-[300px]">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input
            value={inputQ}
            onChange={(e) => setInputQ(e.target.value)}
            placeholder="Buscar por RUT, folio o nombre"
            className="h-9 pl-8 text-[13px]"
            aria-label="Buscar pacientes"
          />
        </div>
        {regions.length > 0 && (
          <div className="relative">
            <select
              value={regionFilter}
              onChange={(e) => {
                setRegionFilter(e.target.value);
                setPage(0);
              }}
              className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
            >
              {["Todas", ...regions].map((r) => (
                <option key={r} value={r}>
                  Región: {r}
                </option>
              ))}
            </select>
            <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
          </div>
        )}
      </div>

      {/* States: empty prompt / fetching / no results */}
      {!q && !isFetching && (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <Search className="mx-auto mb-3 size-8 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            Escribe un RUT, folio o nombre para buscar pacientes.
          </p>
        </div>
      )}

      {isFetching && (
        <p className="text-[13px] text-muted-foreground px-1">Buscando…</p>
      )}

      {q && !isFetching && filtered.length === 0 && (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">Sin resultados.</p>
        </div>
      )}

      {/* Table */}
      {!isFetching && filtered.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b text-[11px] font-semibold text-muted-foreground">
                  <Th>Paciente</Th>
                  <Th>RUT</Th>
                  <Th>Región</Th>
                  <Th>Comuna</Th>
                  <Th>Teléfono / Correo</Th>
                </tr>
              </thead>
              <tbody>
                {paged.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => onOpenPatient(p)}
                    className="border-b hover:bg-muted/40 cursor-pointer transition-colors"
                  >
                    {/* Paciente: avatar + nombre + edad·sexo·correo */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <PatientAvatar p={p} />
                        <div className="min-w-0">
                          <div className="font-semibold text-[13px] truncate">
                            {p.nombre}
                          </div>
                          <div className="text-[11.5px] text-muted-foreground truncate">
                            {p.edad} años · {p.sexo}
                            {p.correo ? ` · ${p.correo}` : ""}
                          </div>
                        </div>
                      </div>
                    </td>
                    {/* RUT — monospace */}
                    <td className="px-4 py-3 font-mono text-[12px]">{p.rut}</td>
                    {/* Región */}
                    <td className="px-4 py-3 text-[12.5px]">{p.region}</td>
                    {/* Comuna */}
                    <td className="px-4 py-3 text-[12.5px]">
                      {p.comuna ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    {/* Teléfono / Correo */}
                    <td className="px-4 py-3 text-[12px] text-muted-foreground">
                      {p.telefono ? (
                        <span className="font-mono">{p.telefono}</span>
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t bg-card">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                <ChevronLeft /> Anterior
              </Button>
              <div className="flex items-center gap-1">
                {pageNumbers.map((n, i) =>
                  n === "…" ? (
                    <span key={i} className="px-2 text-muted-foreground text-[12px]">
                      …
                    </span>
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
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
                disabled={page >= pages - 1}
              >
                Siguiente <ChevronRight />
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
