import { useEffect, useState } from "react";
import { Search, Plus, Stethoscope, ChevronRight, CalendarCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useBuscarPacientes, useVista360 } from "@/features/ingresos/hooks";
import { useControlesPorIngreso } from "./hooks";
import type { ControlMedicoRead, EstadoReca, TipoReposo } from "./api";
import type { components } from "@/types/api";

type PacienteRead = components["schemas"]["PacienteRead"];

// NOTE: There is NO global controles list — the backend only exposes
// GET /api/v1/controles-medicos/por-ingreso/{ingreso_id}, so filters are
// ingreso-scoped (client-side only). There is also NO reca_fecha in the
// ControlMedicoRead contract (only estado_reca) — known backend gaps.

// ── Friendly label maps (exhaustive) ────────────────────────────────────────

const ESTADO_RECA_LABELS: Record<EstadoReca, string> = {
  pendiente: "Pendiente",
  aprobado: "Aprobado",
  rechazado: "Rechazado",
  en_proceso: "En proceso",
  no_aplica: "No aplica",
};

const TIPO_REPOSO_LABELS: Record<TipoReposo, string> = {
  total: "Total",
  parcial: "Parcial",
};

// ── Sub-components ───────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function ControlRow({ control }: { control: ControlMedicoRead }) {
  return (
    <tr className="border-b hover:bg-muted/40 transition-colors">
      {/* Fecha control */}
      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">
        {fmtDate(control.fecha_control)}
      </td>

      {/* Próximo control */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[12px] text-muted-foreground">
            {control.proximo_control ? fmtDate(control.proximo_control) : "—"}
          </span>
          {control.proximo_agendado && (
            <Badge variant="success" className="gap-1">
              <CalendarCheck className="size-2.5" />
              Agendado
            </Badge>
          )}
        </div>
      </td>

      {/* Semana */}
      <td className="px-4 py-3 text-[13px] font-medium">
        {control.semana_control}
      </td>

      {/* Días LM */}
      <td className="px-4 py-3 text-[13px] text-muted-foreground">
        {control.total_dias_lm ?? "—"}
      </td>

      {/* Reposo */}
      <td className="px-4 py-3">
        {control.tipo_reposo ? (
          <Badge variant={control.tipo_reposo === "total" ? "info" : "warning"}>
            {TIPO_REPOSO_LABELS[control.tipo_reposo]}
          </Badge>
        ) : (
          <span className="text-[13px] text-muted-foreground">—</span>
        )}
      </td>

      {/* GAF — mini horizontal bar 0-100 */}
      <td className="px-4 py-3">
        {control.gaf != null ? (
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.max(0, Math.min(100, control.gaf))}%` }}
              />
            </div>
            <span className="text-[12px] font-mono text-muted-foreground">
              {control.gaf}
            </span>
          </div>
        ) : (
          <span className="text-[13px] text-muted-foreground">—</span>
        )}
      </td>

      {/* RECA */}
      <td className="px-4 py-3">
        {control.estado_reca ? (
          <Badge
            variant={
              control.estado_reca === "aprobado"
                ? "success"
                : control.estado_reca === "rechazado"
                ? "destructive"
                : control.estado_reca === "en_proceso"
                ? "info"
                : "neutral"
            }
          >
            {ESTADO_RECA_LABELS[control.estado_reca]}
          </Badge>
        ) : (
          <span className="text-[13px] text-muted-foreground">—</span>
        )}
      </td>

      {/* Médico */}
      <td className="px-4 py-3 text-[12.5px]">{control.medico_tratante}</td>
    </tr>
  );
}

// ── Controles panel ──────────────────────────────────────────────────────────

function ControlesPanel({ ingresoId }: { ingresoId: number }) {
  const {
    data: controles = [],
    isLoading,
    isError,
  } = useControlesPorIngreso(ingresoId);

  // Client-side filters (ingreso-scoped)
  const [recaFilter, setRecaFilter] = useState<EstadoReca | "Todos">("Todos");
  const [reposoFilter, setReposoFilter] = useState<TipoReposo | "Todos">("Todos");
  const [licenciaFilter, setLicenciaFilter] = useState<"todos" | "con" | "sin">("todos");

  const filtered = controles.filter((c) => {
    if (recaFilter !== "Todos" && c.estado_reca !== recaFilter) return false;
    if (reposoFilter !== "Todos" && c.tipo_reposo !== reposoFilter) return false;
    if (licenciaFilter === "con" && !c.tiene_licencia) return false;
    if (licenciaFilter === "sin" && c.tiene_licencia) return false;
    return true;
  });

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando controles…
      </p>
    );
  }
  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 text-[13px] text-destructive">
        No se pudieron cargar los controles médicos.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters bar */}
      {controles.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {/* RECA filter */}
          <div className="relative">
            <select
              value={recaFilter}
              onChange={(e) =>
                setRecaFilter(e.target.value as EstadoReca | "Todos")
              }
              className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
              aria-label="Filtrar por RECA"
            >
              <option value="Todos">RECA: Todos</option>
              <option value="pendiente">Pendiente</option>
              <option value="aprobado">Aprobado</option>
              <option value="rechazado">Rechazado</option>
              <option value="en_proceso">En proceso</option>
              <option value="no_aplica">No aplica</option>
            </select>
            <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
          </div>

          {/* Reposo filter */}
          <div className="relative">
            <select
              value={reposoFilter}
              onChange={(e) =>
                setReposoFilter(e.target.value as TipoReposo | "Todos")
              }
              className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
              aria-label="Filtrar por tipo de reposo"
            >
              <option value="Todos">Reposo: Todos</option>
              <option value="total">Total</option>
              <option value="parcial">Parcial</option>
            </select>
            <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
          </div>

          {/* Licencia filter */}
          <div className="relative">
            <select
              value={licenciaFilter}
              onChange={(e) =>
                setLicenciaFilter(e.target.value as "todos" | "con" | "sin")
              }
              className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
              aria-label="Filtrar por licencia"
            >
              <option value="todos">Licencia: Todos</option>
              <option value="con">Con licencia</option>
              <option value="sin">Sin licencia</option>
            </select>
            <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
          </div>

          <Badge variant="neutral" className="ml-auto">
            {filtered.length} control{filtered.length !== 1 ? "es" : ""}
          </Badge>
        </div>
      )}

      {controles.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
          <Stethoscope className="mx-auto mb-3 size-7 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            No hay controles médicos registrados para este ingreso.
          </p>
        </div>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Fecha control</Th>
                  <Th>Próximo control</Th>
                  <Th>Semana</Th>
                  <Th>Días LM</Th>
                  <Th>Reposo</Th>
                  <Th>GAF</Th>
                  <Th>RECA</Th>
                  <Th>Médico</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-4 py-8 text-center text-[13px] text-muted-foreground"
                    >
                      Sin controles para los filtros seleccionados.
                    </td>
                  </tr>
                ) : (
                  filtered.map((c) => <ControlRow key={c.id} control={c} />)
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export function ControlesPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);

  // Search state — 300ms debounce (mirrors FarmacosPage)
  const [inputQ, setInputQ] = useState("");
  const [q, setQ] = useState("");

  // Selected paciente — cleared whenever the debounced query changes
  const [selectedPaciente, setSelectedPaciente] = useState<PacienteRead | null>(
    null
  );

  useEffect(() => {
    const t = setTimeout(() => {
      setQ(inputQ.trim());
      setSelectedPaciente(null);
    }, 300);
    return () => clearTimeout(t);
  }, [inputQ]);

  const { data: pacientes = [], isFetching } = useBuscarPacientes(q);

  // Resolve ingreso_id via vista-360 — same pattern as FarmacosPage
  const { data: vista, isLoading: vistaLoading } = useVista360(
    selectedPaciente?.id ?? null
  );
  const ingresoId: number | undefined = vista?.ingresos?.[0]?.id;

  // KPI counts from the controles query (React Query deduplicates via cache key)
  const { data: controlesForKpi = [] } = useControlesPorIngreso(ingresoId ?? 0);
  const totalControles = controlesForKpi.length;
  const conLicencia = controlesForKpi.filter((c) => c.tiene_licencia).length;
  const proximoAgendado = controlesForKpi.filter(
    (c) => c.proximo_agendado
  ).length;

  const hasSearched = q.length > 0;

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">
            Controles médicos
          </h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            {ingresoId && !vistaLoading
              ? `${totalControles} control${totalControles !== 1 ? "es" : ""}${conLicencia > 0 ? ` · ${conLicencia} con licencia` : ""}${proximoAgendado > 0 ? ` · ${proximoAgendado} con próximo agendado` : ""}`
              : selectedPaciente
              ? "Cargando ingreso…"
              : "Busca un paciente para ver sus controles médicos."}
          </p>
        </div>

        {/* "Nuevo control" — hidden for Auditor */}
        {canWrite && (
          <Button
            size="sm"
            aria-label="Nuevo control"
            data-testid="btn-nuevo-control"
            disabled
          >
            <Plus /> Nuevo control
          </Button>
        )}
      </div>

      {/* ── Search bar ── */}
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
      </div>

      {/* ── Initial empty state ── */}
      {!hasSearched && !isFetching && (
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

      {hasSearched && !isFetching && pacientes.length === 0 && (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">Sin resultados.</p>
        </div>
      )}

      {/* ── Paciente list — selectable ── */}
      {!isFetching && pacientes.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b text-[11px] font-semibold text-muted-foreground">
                  <Th>Paciente</Th>
                  <Th>RUT</Th>
                  <Th>Región</Th>
                </tr>
              </thead>
              <tbody>
                {pacientes.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => setSelectedPaciente(p)}
                    className={cn(
                      "border-b cursor-pointer transition-colors",
                      selectedPaciente?.id === p.id
                        ? "bg-primary/5 hover:bg-primary/10"
                        : "hover:bg-muted/40"
                    )}
                    aria-selected={selectedPaciente?.id === p.id}
                    role="row"
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-[13px]">{p.nombre}</div>
                      <div className="text-[11.5px] text-muted-foreground">
                        {p.edad} años · {p.sexo}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px]">{p.rut}</td>
                    <td className="px-4 py-3 text-[12.5px]">{p.region}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── Patient detail: controles ── */}
      {selectedPaciente && (
        <div className="space-y-4">
          {/* Vista-360 loading */}
          {vistaLoading && (
            <p className="text-[13px] text-muted-foreground px-1">
              Cargando ingreso de {selectedPaciente.nombre}…
            </p>
          )}

          {/* No ingreso found */}
          {!vistaLoading && !ingresoId && (
            <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-8 text-center">
              <p className="text-[13.5px] text-muted-foreground">
                Este paciente no tiene ingresos registrados.
              </p>
            </div>
          )}

          {/* Controles table */}
          {ingresoId && (
            <div className="space-y-2">
              <h2 className="text-[14px] font-semibold px-0.5">
                Controles médicos
              </h2>
              <ControlesPanel ingresoId={ingresoId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
