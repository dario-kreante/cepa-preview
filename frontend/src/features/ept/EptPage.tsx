/**
 * EptPage — caso-céntrico workspace for Seguimiento EPT.
 *
 * ARCHITECTURAL NOTE:
 * The EPT backend exposes NO list, no search, and no por-ingreso endpoint.
 * Vista360 also does NOT include EPT casos. The ONLY way to reach a caso is:
 *   GET /api/v1/casos-ept/{caso_id}
 *
 * Navigation to a caso is therefore caso-céntrico via two paths:
 *   1. Alta paciente-driven: search paciente → resolve ingreso_id via Vista360
 *      → create caso with "Nueva EPT" → active caso detail appears.
 *   2. Cargar por caso_id: type a known caso_id in the numeric input (or pass
 *      ?caso=<id> in the URL) → GET /api/v1/casos-ept/{caso_id} → detail renders.
 *
 * RBAC: EPT write = Administrativo ONLY (puedeEscribirEpt). Coordinacion can
 * read but NOT write — this is intentionally stricter than other modules.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Search,
  Plus,
  Briefcase,
  AlertCircle,
  Hash,
  Pencil,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribirEpt, type Rol } from "@/lib/rbac";
import { useBuscarPacientes, useVista360 } from "@/features/ingresos/hooks";
import { useCaso } from "./hooks";
import { NuevoCasoEptDialog } from "./NuevoCasoEptDialog";
import { ProcesoEptPanel } from "./ProcesoEptPanel";
import { FACTOR_RIESGO_LABELS, type CasoEptForm } from "./casoEptSchema";
import type { CasoEptRead, EstadoEpt, FactorRiesgo } from "./api";
import type { components } from "@/types/api";

type PacienteRead = components["schemas"]["PacienteRead"];

// ── Badge helpers ────────────────────────────────────────────────────────────

const ESTADO_EPT_LABELS: Record<EstadoEpt, string> = {
  abierto: "Abierto",
  no_corresponde: "No corresponde",
  cerrado: "Cerrado",
};

function estadoVariant(
  estado: EstadoEpt
): "info" | "neutral" | "success" {
  if (estado === "abierto") return "info";
  if (estado === "cerrado") return "success";
  return "neutral";
}

// ── Sub-components ───────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

// ── Caso detail card ─────────────────────────────────────────────────────────

interface CasoDetailProps {
  caso: CasoEptRead;
  canWrite: boolean;
  onEdit: () => void;
}

function CasoDetail({ caso, canWrite, onEdit }: CasoDetailProps) {
  return (
    <Card className="p-5 space-y-4">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Caso N° {caso.id}
          </p>
          <h2 className="text-[16px] font-semibold">{caso.nombre_trabajador}</h2>
          <p className="text-[12.5px] text-muted-foreground font-mono">
            {caso.rut_trabajador}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge variant={estadoVariant(caso.estado)}>
            {ESTADO_EPT_LABELS[caso.estado]}
          </Badge>
          {canWrite && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-[11.5px] px-2"
              aria-label="Editar caso"
              data-testid="btn-editar-caso"
              onClick={onEdit}
            >
              <Pencil className="size-3 mr-1" />
              Editar caso
            </Button>
          )}
        </div>
      </div>

      {/* Grid of fields */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-[13px]">
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Región trabajador
          </p>
          <p>{caso.region_trabajador}</p>
        </div>
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            EISTA
          </p>
          <p>{caso.eista}</p>
        </div>
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Factor de riesgo
          </p>
          <Badge variant="neutral" className="mt-0.5">
            {FACTOR_RIESGO_LABELS[caso.factor_riesgo as FactorRiesgo] ??
              caso.factor_riesgo}
          </Badge>
        </div>
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Corresponde EPT
          </p>
          <p>{caso.corresponde_ept ? "Sí" : "No"}</p>
        </div>
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Mes
          </p>
          <p>{caso.mes}</p>
        </div>
        <div>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Fecha ingreso EPT
          </p>
          <p className="font-mono text-[12px]">
            {fmtDate(caso.fecha_ingreso_ept)}
          </p>
        </div>
        {caso.razon_social && (
          <div>
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
              Razón social
            </p>
            <p>{caso.razon_social}</p>
          </div>
        )}
        {caso.unidad_cargo_horario && (
          <div>
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
              Unidad / Cargo / Horario
            </p>
            <p>{caso.unidad_cargo_horario}</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// ── Loaded caso panel ────────────────────────────────────────────────────────

interface CasoPanelProps {
  casoId: number;
  canWrite: boolean;
  onCasoUpdated: (caso: CasoEptRead) => void;
}

function CasoPanel({ casoId, canWrite, onCasoUpdated }: CasoPanelProps) {
  const { data: caso, isLoading, isError, error } = useCaso(casoId);
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) {
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando caso EPT {casoId}…
      </p>
    );
  }

  if (isError) {
    const msg =
      error instanceof Error ? error.message : "No se pudo cargar el caso EPT";
    const isNotFound = msg.toLowerCase().includes("404") || msg.toLowerCase().includes("no se pudo obtener");
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-start gap-2">
        <AlertCircle className="size-4 text-destructive mt-0.5 shrink-0" />
        <p className="text-[13px] text-destructive">
          {isNotFound
            ? `El caso N° ${casoId} no fue encontrado.`
            : msg}
        </p>
      </div>
    );
  }

  if (!caso) return null;

  const initialValues: CasoEptForm = {
    mes: caso.mes,
    fecha_ingreso_ept: caso.fecha_ingreso_ept,
    nombre_trabajador: caso.nombre_trabajador,
    rut_trabajador: caso.rut_trabajador,
    region_trabajador: caso.region_trabajador,
    eista: caso.eista,
    factor_riesgo: caso.factor_riesgo as CasoEptForm["factor_riesgo"],
    corresponde_ept: caso.corresponde_ept,
    razon_social: caso.razon_social ?? "",
    unidad_cargo_horario: caso.unidad_cargo_horario ?? "",
  };

  return (
    <>
      <CasoDetail
        caso={caso}
        canWrite={canWrite}
        onEdit={() => setEditOpen(true)}
      />
      <ProcesoEptPanel casoId={casoId} canWrite={canWrite} />
      {canWrite && (
        <NuevoCasoEptDialog
          ingresoId={caso.ingreso_id}
          open={editOpen}
          onOpenChange={setEditOpen}
          onCreated={(updated) => {
            onCasoUpdated(updated);
            setEditOpen(false);
          }}
          initialValues={initialValues}
          casoId={caso.id}
        />
      )}
    </>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export function EptPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribirEpt(rol as Rol);

  const [searchParams] = useSearchParams();

  // ── Paciente search (alta paciente-driven) ──────────────────────────────
  const [inputQ, setInputQ] = useState("");
  const [q, setQ] = useState("");
  const [selectedPaciente, setSelectedPaciente] =
    useState<PacienteRead | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setQ(inputQ.trim());
      setSelectedPaciente(null);
    }, 300);
    return () => clearTimeout(t);
  }, [inputQ]);

  const { data: pacientes = [], isFetching } = useBuscarPacientes(q);

  // Resolve ingreso_id via vista-360
  const { data: vista, isLoading: vistaLoading } = useVista360(
    selectedPaciente?.id ?? null
  );
  const ingresoId: number | undefined = vista?.ingresos?.[0]?.id;

  // ── Cargar por caso_id ──────────────────────────────────────────────────
  const [casoIdInput, setCasoIdInput] = useState("");
  const [casoId, setCasoId] = useState<number | null>(() => {
    const param = searchParams.get("caso");
    const n = param ? parseInt(param, 10) : NaN;
    return Number.isInteger(n) && n > 0 ? n : null;
  });

  // ── Active caso (set by create OR load) ────────────────────────────────
  // casoId drives useCaso — either set from "cargar" input or from onCreated
  const hasSearched = q.length > 0;

  // Dialog for "Nueva EPT"
  const [nuevaOpen, setNuevaOpen] = useState(false);

  function handleCasoCreated(caso: CasoEptRead) {
    setCasoId(caso.id);
    setNuevaOpen(false);
  }

  function handleLoadCaso() {
    const parsed = parseInt(casoIdInput, 10);
    if (!isNaN(parsed) && parsed > 0) {
      setCasoId(parsed);
    }
  }

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">
            Seguimiento EPT
          </h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Evaluaciones de Puesto de Trabajo · Gestión con empleadores e ISL
          </p>
        </div>

        {/* "Nueva EPT" — Administrativo only; enabled when a paciente + ingreso is resolved */}
        {canWrite && (
          <>
            <Button
              size="sm"
              aria-label="Nueva EPT"
              data-testid="btn-nueva-ept"
              disabled={!ingresoId}
              onClick={() => setNuevaOpen(true)}
            >
              <Plus className="size-3.5" /> Nueva EPT
            </Button>

            {ingresoId && (
              <NuevoCasoEptDialog
                ingresoId={ingresoId}
                open={nuevaOpen}
                onOpenChange={setNuevaOpen}
                onCreated={handleCasoCreated}
              />
            )}
          </>
        )}
      </div>

      {/* ── Cargar por caso_id ── */}
      <div className="flex items-center gap-2">
        <Hash className="size-3.5 text-muted-foreground shrink-0" />
        <Input
          type="number"
          min={1}
          value={casoIdInput}
          onChange={(e) => setCasoIdInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleLoadCaso();
          }}
          placeholder="Cargar caso N°"
          className="h-9 w-[180px] text-[13px]"
          aria-label="Cargar caso por ID"
          data-testid="input-caso-id"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={handleLoadCaso}
          disabled={!casoIdInput || isNaN(parseInt(casoIdInput, 10))}
          data-testid="btn-cargar-caso"
        >
          Cargar
        </Button>
      </div>

      {/* ── Active caso (from cargar or create) ── */}
      {casoId !== null && (
        <div className="space-y-2">
          <h2 className="text-[14px] font-semibold px-0.5">
            Caso activo
          </h2>
          <CasoPanel
            casoId={casoId}
            canWrite={canWrite}
            onCasoUpdated={(updated) => setCasoId(updated.id)}
          />
        </div>
      )}

      {/* ── Paciente search (alta paciente-driven) ── */}
      <div className="space-y-3">
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

        {/* Initial empty state */}
        {!hasSearched && !isFetching && casoId === null && (
          <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
            <Briefcase className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-[13.5px] text-muted-foreground">
              Busca un paciente para crear un caso EPT, o carga un caso existente
              por su número.
            </p>
          </div>
        )}

        {isFetching && (
          <p className="text-[13px] text-muted-foreground px-1">Buscando…</p>
        )}

        {hasSearched && !isFetching && pacientes.length === 0 && (
          <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
            <p className="text-[13.5px] text-muted-foreground">
              Sin resultados.
            </p>
          </div>
        )}

        {/* Paciente list — selectable */}
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
                        <div className="font-semibold text-[13px]">
                          {p.nombre}
                        </div>
                        <div className="text-[11.5px] text-muted-foreground">
                          {p.edad} años · {p.sexo}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-[12px]">
                        {p.rut}
                      </td>
                      <td className="px-4 py-3 text-[12.5px]">{p.region}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Paciente selected — vista loading / no ingreso / ready to create */}
        {selectedPaciente && (
          <div className="space-y-3">
            {vistaLoading && (
              <p className="text-[13px] text-muted-foreground px-1">
                Cargando ingreso de {selectedPaciente.nombre}…
              </p>
            )}

            {!vistaLoading && !ingresoId && (
              <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-8 text-center">
                <p className="text-[13.5px] text-muted-foreground">
                  Este paciente no tiene ingresos registrados.
                </p>
              </div>
            )}

            {!vistaLoading && ingresoId && (
              <div className="rounded-lg border border-border bg-muted/10 px-5 py-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-[13px] font-semibold">
                    {selectedPaciente.nombre}
                  </p>
                  <p className="text-[12px] text-muted-foreground">
                    Ingreso N° {ingresoId} disponible
                    {canWrite
                      ? " — haz clic en «Nueva EPT» para registrar el caso."
                      : "."}
                  </p>
                </div>
                {canWrite && (
                  <Button
                    size="sm"
                    onClick={() => setNuevaOpen(true)}
                    data-testid="btn-nueva-ept-inline"
                  >
                    <Plus className="size-3.5" /> Nueva EPT
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
