import { useEffect, useState } from "react";
import { Search, Plus, Pill, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useBuscarPacientes, useVista360 } from "@/features/ingresos/hooks";
import { useRegistro, useRecetas } from "./hooks";
import type { RecetaRead } from "./api";
import type { components } from "@/types/api";

type PacienteRead = components["schemas"]["PacienteRead"];

// ── Date helpers ─────────────────────────────────────────────────────────────

/**
 * Derive receta status from fecha_revision vs today.
 * 5-day window mirrors the backend alert rule.
 */
function recetaStatusInfo(fechaRevision: string | null): {
  label: string;
  variant: "destructive" | "warning" | "success";
} {
  if (!fechaRevision) return { label: "Sin revisión", variant: "warning" };
  // Compare yyyy-mm-dd strings directly (lexicographic == chronological for ISO dates)
  const todayStr = new Date().toISOString().split("T")[0];
  const in5Days = new Date();
  in5Days.setDate(in5Days.getDate() + 5);
  const in5DaysStr = in5Days.toISOString().split("T")[0];

  if (fechaRevision < todayStr) return { label: "Vencida", variant: "destructive" };
  if (fechaRevision <= in5DaysStr) return { label: "Por vencer", variant: "warning" };
  return { label: "Vigente", variant: "success" };
}

// ── Sub-components ───────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

// ── Receta row ───────────────────────────────────────────────────────────────

function RecetaRow({ receta }: { receta: RecetaRead }) {
  const status = recetaStatusInfo(receta.fecha_revision ?? null);
  return (
    <tr className="border-b hover:bg-muted/40 transition-colors">
      {/* Fármaco / marca */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="size-7 rounded-md bg-[oklch(0.95_0.05_290)] text-[oklch(0.42_0.16_290)] grid place-items-center shrink-0">
            <Pill className="size-3.5" />
          </div>
          <span className="font-semibold text-[13px]">
            {receta.marca_medicamento ?? <span className="text-muted-foreground">—</span>}
          </span>
        </div>
      </td>
      {/* Emisión */}
      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">
        {receta.fecha_emision ? fmtDate(receta.fecha_emision) : "—"}
      </td>
      {/* Revisión */}
      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">
        {receta.fecha_revision ? fmtDate(receta.fecha_revision) : "—"}
      </td>
      {/* Envío al paciente */}
      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">
        {receta.fecha_envio ? fmtDate(receta.fecha_envio) : "—"}
      </td>
      {/* Estado derivado */}
      <td className="px-4 py-3">
        <Badge variant={status.variant}>{status.label}</Badge>
      </td>
    </tr>
  );
}

// ── Registro panel ───────────────────────────────────────────────────────────

function RegistroPanel({
  ingresoId,
  canWrite,
}: {
  ingresoId: number;
  canWrite: boolean;
}) {
  const { data: registro, isLoading, isError } = useRegistro(ingresoId);

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">Cargando registro…</p>
    );
  }
  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 text-[13px] text-destructive">
        No se pudo cargar el registro farmacológico.
      </div>
    );
  }
  if (registro === null || registro === undefined) {
    return (
      <Card className="p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[13.5px] font-semibold">Sin registro farmacológico</p>
            <p className="text-[12.5px] text-muted-foreground mt-0.5">
              Este ingreso aún no tiene un registro farmacológico creado.
            </p>
          </div>
          {canWrite && (
            <Button
              size="sm"
              variant="outline"
              disabled
              aria-label="Crear registro farmacológico"
            >
              <Plus /> Crear registro
            </Button>
          )}
        </div>
      </Card>
    );
  }

  const ESTADO_LABELS: Record<string, string> = {
    sin_tratamiento: "Sin tratamiento",
    en_tratamiento: "En tratamiento",
    suspendido: "Suspendido",
    finalizado: "Finalizado",
  };

  return (
    <Card className="p-5 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-[14px] font-semibold">Registro farmacológico</h2>
        {registro.estado_farmacologico && (
          <Badge variant="info">
            {ESTADO_LABELS[registro.estado_farmacologico] ??
              registro.estado_farmacologico}
          </Badge>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12.5px]">
        {registro.medico_tratante && (
          <div>
            <span className="text-muted-foreground">Médico tratante</span>
            <p className="font-medium mt-0.5">{registro.medico_tratante}</p>
          </div>
        )}
        {registro.antecedentes_previos && (
          <div>
            <span className="text-muted-foreground">Antecedentes previos</span>
            <p className="font-medium mt-0.5">{registro.antecedentes_previos}</p>
          </div>
        )}
        {registro.tratamiento_previo && (
          <div className="sm:col-span-2">
            <span className="text-muted-foreground">Tratamiento previo</span>
            <p className="font-medium mt-0.5">{registro.tratamiento_previo}</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// ── Recetas panel ────────────────────────────────────────────────────────────

// NOTE: Recetas are scoped to a single ingreso_id (the patient's primary ingreso).
// The backend has no global receta list endpoint — cross-ingreso or cross-patient
// receta queries are not supported. This is a known gap.

function RecetasPanel({
  ingresoId,
  canWrite,
}: {
  ingresoId: number;
  canWrite: boolean;
}) {
  const { data: recetas = [], isLoading, isError } = useRecetas(ingresoId);

  // Filters — client-side over ingreso scope only
  const [statusFilter, setStatusFilter] = useState("Todos");
  const [marcaFilter, setMarcaFilter] = useState("Todas");

  const marcas = Array.from(
    new Set(recetas.map((r) => r.marca_medicamento).filter(Boolean))
  ).sort() as string[];

  const filtered = recetas.filter((r) => {
    const status = recetaStatusInfo(r.fecha_revision ?? null).label;
    if (statusFilter !== "Todos" && status !== statusFilter) return false;
    if (marcaFilter !== "Todas" && r.marca_medicamento !== marcaFilter) return false;
    return true;
  });

  if (isLoading) {
    return <p className="text-[13px] text-muted-foreground px-1">Cargando recetas…</p>;
  }
  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 text-[13px] text-destructive">
        No se pudieron cargar las recetas.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters bar — only shown when there's something to filter */}
      {recetas.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {/* Estado filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
              aria-label="Filtrar por estado"
            >
              <option value="Todos">Estado: Todos</option>
              <option value="Vigente">Vigente</option>
              <option value="Por vencer">Por vencer</option>
              <option value="Vencida">Vencida</option>
              <option value="Sin revisión">Sin revisión</option>
            </select>
            <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
          </div>

          {/* Marca filter */}
          {marcas.length > 0 && (
            <div className="relative">
              <select
                value={marcaFilter}
                onChange={(e) => setMarcaFilter(e.target.value)}
                className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
                aria-label="Filtrar por medicamento"
              >
                <option value="Todas">Medicamento: Todos</option>
                {marcas.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
            </div>
          )}

          <Badge variant="neutral" className="ml-auto">
            {filtered.length} receta{filtered.length !== 1 ? "s" : ""}
          </Badge>
        </div>
      )}

      {recetas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
          <Pill className="mx-auto mb-3 size-7 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            No hay recetas registradas para este ingreso.
          </p>
          {canWrite && (
            <Button
              size="sm"
              variant="outline"
              className="mt-3"
              disabled
              aria-label="Nueva receta"
            >
              <Plus /> Nueva receta
            </Button>
          )}
        </div>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Medicamento</Th>
                  <Th>Emisión</Th>
                  <Th>Revisión</Th>
                  <Th>Envío al paciente</Th>
                  <Th>Estado</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center text-[13px] text-muted-foreground"
                    >
                      Sin recetas para los filtros seleccionados.
                    </td>
                  </tr>
                ) : (
                  filtered.map((r) => <RecetaRow key={r.id} receta={r} />)
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

export function FarmacosPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);

  // Search state — 300ms debounce (mirrors IngresosListaPage)
  const [inputQ, setInputQ] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setInputQ((v) => {
      setQ(v.trim());
      return v;
    }), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputQ]);

  const { data: pacientes = [], isFetching } = useBuscarPacientes(q);

  // Selected paciente
  const [selectedPaciente, setSelectedPaciente] = useState<PacienteRead | null>(null);

  // When query changes, clear selection
  useEffect(() => {
    setSelectedPaciente(null);
  }, [q]);

  // Resolve ingreso_id via vista360 — same pattern as PatientSheet.tsx lines ~244-248
  const { data: vista, isLoading: vistaLoading } = useVista360(
    selectedPaciente?.id ?? null
  );
  const ingresoId: number | undefined = vista?.ingresos?.[0]?.id;

  // Derive receta KPIs once we have data
  const { data: recetasForKpi = [] } = useRecetas(ingresoId ?? 0);
  const vencidas = recetasForKpi.filter(
    (r) => recetaStatusInfo(r.fecha_revision ?? null).label === "Vencida"
  ).length;
  const porVencer = recetasForKpi.filter(
    (r) => recetaStatusInfo(r.fecha_revision ?? null).label === "Por vencer"
  ).length;

  const hasSearched = q.length > 0;

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">
            Gestión de fármacos
          </h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            {ingresoId && !vistaLoading
              ? `${recetasForKpi.length} receta${recetasForKpi.length !== 1 ? "s" : ""}${porVencer > 0 ? ` · ${porVencer} por vencer` : ""}${vencidas > 0 ? ` · ${vencidas} vencida${vencidas !== 1 ? "s" : ""}` : ""}`
              : selectedPaciente
              ? "Cargando ingreso…"
              : "Busca un paciente para ver su historial de fármacos."}
          </p>
        </div>
        {/* "Nueva receta" — hidden for Auditor; no-op (dialog comes in a later task) */}
        {canWrite && (
          <Button
            size="sm"
            disabled
            aria-label="Nueva receta"
            data-testid="btn-nueva-receta"
          >
            <Plus /> Nueva receta
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

      {/* ── Patient detail: registro + recetas ── */}
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

          {/* Detail panels */}
          {ingresoId && (
            <>
              <RegistroPanel ingresoId={ingresoId} canWrite={canWrite} />
              <div className="space-y-2">
                <h2 className="text-[14px] font-semibold px-0.5">Recetas</h2>
                <RecetasPanel ingresoId={ingresoId} canWrite={canWrite} />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
