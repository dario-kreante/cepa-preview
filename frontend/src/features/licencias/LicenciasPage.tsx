import { useEffect, useState } from "react";
import { Search, Plus, ChevronRight, Ban, Send, Bell } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import {
  useLicenciasPorFolio,
  useLicenciasDetalle,
  useActualizarISL,
  useGenerarAlertas,
} from "./hooks";
import type { LicenciaReadSlim, LicenciaRead } from "./api";
import { AltaLicenciaDialog } from "./AltaLicenciaDialog";
import { AnularLicenciaDialog } from "./AnularLicenciaDialog";
import { IslLicenciaDialog } from "./IslLicenciaDialog";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Computes a "Vence en" label given fecha_termino and whether the row is anulada.
 * Uses calendar days (simple, no business-day calendar).
 */
function venceEnInfo(
  fechaTermino: string,
  anulada: boolean,
): { label: string; variant: "destructive" | "warning" | "success" | "neutral" } {
  if (anulada) return { label: "Anulada", variant: "neutral" };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const fin = new Date(fechaTermino);
  fin.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((fin.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return { label: "Vencida", variant: "neutral" };
  if (diffDays < 3) return { label: `Vence en ${diffDays}d`, variant: "destructive" };
  if (diffDays < 7) return { label: `Vence en ${diffDays}d`, variant: "warning" };
  return { label: `Vigente (${diffDays}d)`, variant: "success" };
}

/**
 * Estado badge: driven from anulada + fecha_termino vs today.
 */
function estadoInfo(
  fechaTermino: string,
  anulada: boolean,
): { label: string; variant: "destructive" | "success" | "neutral" } {
  if (anulada) return { label: "Anulada", variant: "destructive" };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const fin = new Date(fechaTermino);
  fin.setHours(0, 0, 0, 0);
  if (fin < today) return { label: "Finalizada", variant: "neutral" };
  return { label: "Vigente", variant: "success" };
}

// Label map for tipo_lm enum values
const TIPO_LM_LABELS: Record<string, string> = {
  "1": "Tipo 1",
  "5": "Tipo 5",
  "6": "Tipo 6",
};

// Label map for tipo_reposo
const TIPO_REPOSO_LABELS: Record<string, string> = {
  total: "Total",
  parcial: "Parcial",
};

// Label map for EstadoEnvioISL
const ISL_LABELS: Record<string, string> = {
  pendiente: "Pendiente",
  enviado: "Enviado",
  rechazado: "Rechazado",
};

// ─── Sub-components ─────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

// ─── Row component ───────────────────────────────────────────────────────────

interface RowProps {
  slim: LicenciaReadSlim;
  full: LicenciaRead | undefined;
  canWrite: boolean;
  selected: boolean;
  onToggleSelect: (id: number) => void;
  onAnular: (row: LicenciaReadSlim) => void;
  onISL: (row: LicenciaReadSlim) => void;
}

function LicenciaRow({
  slim,
  full,
  canWrite,
  selected,
  onToggleSelect,
  onAnular,
  onISL,
}: RowProps) {
  const vence = venceEnInfo(slim.fecha_termino, slim.anulada);
  const estado = estadoInfo(slim.fecha_termino, slim.anulada);

  // Full fields — "—" when not yet loaded (backend contract gap: slim has no tipo_reposo/eeag_gaf/envio_isl)
  const folioLm = full?.folio_lm ?? "—";
  const tipoReposo = full ? (TIPO_REPOSO_LABELS[full.tipo_reposo] ?? full.tipo_reposo) : "—";
  const eeagGaf = full ? (full.eeag_gaf != null ? String(full.eeag_gaf) : "—") : "—";
  const envioIsl = full ? (ISL_LABELS[full.envio_isl] ?? full.envio_isl) : "—";

  return (
    <tr className="border-b hover:bg-muted/40 transition-colors">
      {/* Checkbox — writers only; anulled rows are not selectable */}
      {canWrite && (
        <td className="px-4 py-3">
          <Checkbox
            checked={selected}
            onCheckedChange={() => onToggleSelect(slim.id)}
            disabled={slim.anulada}
            aria-label={`Seleccionar licencia ${slim.id}`}
          />
        </td>
      )}
      {/* Folio LM */}
      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">{folioLm}</td>
      {/* Tipo */}
      <td className="px-4 py-3">
        <Badge variant="info">{TIPO_LM_LABELS[slim.tipo_lm] ?? slim.tipo_lm}</Badge>
      </td>
      {/* Reposo */}
      <td className="px-4 py-3 text-[12.5px]">{tipoReposo}</td>
      {/* Inicio */}
      <td className="px-4 py-3 font-mono text-[12px] text-muted-foreground">{fmtDate(slim.fecha_inicio)}</td>
      {/* Fin + Vence en badge */}
      <td className="px-4 py-3">
        <div className="font-mono text-[12px] text-muted-foreground">{fmtDate(slim.fecha_termino)}</div>
        <Badge variant={vence.variant} className="mt-1">{vence.label}</Badge>
      </td>
      {/* Días */}
      <td className="px-4 py-3 font-mono text-[12px] font-semibold">{slim.cantidad_dias}</td>
      {/* GAF/EEAG */}
      <td className="px-4 py-3 text-[12.5px]">{eeagGaf}</td>
      {/* ISL */}
      <td className="px-4 py-3">
        {envioIsl === "—" ? (
          <span className="text-[12px] text-muted-foreground">—</span>
        ) : (
          <Badge
            variant={
              envioIsl === "Enviado"
                ? "success"
                : envioIsl === "Rechazado"
                ? "destructive"
                : "warning"
            }
          >
            {envioIsl}
          </Badge>
        )}
      </td>
      {/* Estado */}
      <td className="px-4 py-3">
        <Badge variant={estado.variant}>{estado.label}</Badge>
      </td>
      {/* Acciones — writers only; anulled rows can't be re-anulled */}
      <td className="px-4 py-3">
        {canWrite && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => onAnular(slim)}
              disabled={slim.anulada}
              className="h-7 w-7 flex items-center justify-center rounded border border-transparent hover:border-border hover:bg-destructive/10 hover:text-destructive disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-muted-foreground"
              title={slim.anulada ? "Licencia ya anulada" : "Anular licencia"}
              aria-label="Anular licencia"
            >
              <Ban className="size-3.5" />
            </button>
            <button
              onClick={() => onISL(slim)}
              className="h-7 w-7 flex items-center justify-center rounded border border-transparent hover:border-border hover:bg-muted/40 transition-colors text-muted-foreground"
              title="Actualizar envío ISL"
              aria-label="Actualizar ISL"
            >
              <Send className="size-3.5" />
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export function LicenciasPage() {
  const { rol } = useAuth();
  const puedeCrear = puedeEscribir(rol as Rol);

  const [inputFolio, setInputFolio] = useState("");
  const [folio, setFolio] = useState("");

  // Dialog state
  const [altaOpen, setAltaOpen] = useState(false);
  const [anularTarget, setAnularTarget] = useState<LicenciaReadSlim | null>(null);
  const [islTarget, setIslTarget] = useState<LicenciaReadSlim | null>(null);

  // Filters (client-side over fetched rows)
  const [tipoFilter, setTipoFilter] = useState("Todos");
  const [reposoFilter, setReposoFilter] = useState("Todos");
  const [islFilter, setIslFilter] = useState("Todos");

  // Row selection — only used by writers; Set of licencia ids
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 400ms debounce on folio input
  useEffect(() => {
    const t = setTimeout(() => setFolio(inputFolio.trim()), 400);
    return () => clearTimeout(t);
  }, [inputFolio]);

  const { data: licenciasResp, isFetching } = useLicenciasPorFolio(folio);

  const historial: LicenciaReadSlim[] = licenciasResp?.historial ?? [];
  const diasAcumulados = licenciasResp?.dias_acumulados ?? 0;

  // Fetch full details per row (para tipo_reposo, eeag_gaf, envio_isl, folio_lm)
  const fullDetails = useLicenciasDetalle(historial.map((h) => h.id));

  // Derive ingreso_id from the first resolved full detail row.
  // LicenciaRead contains ingreso_id; LicenciasResponse does not expose it.
  const ingresoId: number | undefined = fullDetails.find((d) => d?.ingreso_id != null)?.ingreso_id;

  // Build merged rows for filtering
  const mergedRows = historial.map((slim, i) => ({
    slim,
    full: fullDetails[i],
  }));

  // Client-side filters
  const filtered = mergedRows.filter(({ slim, full }) => {
    if (tipoFilter !== "Todos" && slim.tipo_lm !== tipoFilter) return false;
    if (reposoFilter !== "Todos") {
      if (full && full.tipo_reposo !== reposoFilter) return false;
    }
    if (islFilter !== "Todos") {
      if (full && full.envio_isl !== islFilter) return false;
    }
    return true;
  });

  // Non-anulled filtered rows eligible for selection
  const selectableRows = filtered.filter(({ slim }) => !slim.anulada);

  // Select-all state: checked if all selectable visible rows are in selectedIds
  const allSelected =
    selectableRows.length > 0 &&
    selectableRows.every(({ slim }) => selectedIds.has(slim.id));
  const someSelected = selectableRows.some(({ slim }) => selectedIds.has(slim.id));

  function handleToggleSelectAll() {
    if (allSelected) {
      // Deselect all currently visible selectable rows
      setSelectedIds((prev) => {
        const next = new Set(prev);
        selectableRows.forEach(({ slim }) => next.delete(slim.id));
        return next;
      });
    } else {
      // Select all currently visible selectable rows
      setSelectedIds((prev) => {
        const next = new Set(prev);
        selectableRows.forEach(({ slim }) => next.add(slim.id));
        return next;
      });
    }
  }

  function handleToggleRow(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // Hooks for bulk operations
  // NOTE: Cross-region bulk ISL is NOT supported — there is no backend global/region
  // list endpoint to enumerate licencias across patients. Bulk send only applies to
  // the currently selected rows of the active folio search (per-patient scope).
  const actualizarISL = useActualizarISL(folio);
  const generarAlertas = useGenerarAlertas();

  const [isBulkSending, setIsBulkSending] = useState(false);
  const [isGeneratingAlertas, setIsGeneratingAlertas] = useState(false);

  async function handleBulkISL() {
    if (selectedIds.size === 0) return;
    setIsBulkSending(true);
    const today = new Date().toISOString().split("T")[0];
    const ids = Array.from(selectedIds);

    const results = await Promise.allSettled(
      ids.map((id) =>
        actualizarISL.mutateAsync({
          id,
          body: { envio_isl: "enviado", fecha_envio_isl: today },
        })
      )
    );

    const succeeded = results.filter((r) => r.status === "fulfilled").length;
    const failed = results.filter((r) => r.status === "rejected").length;

    if (succeeded > 0) {
      toast.success(`${succeeded} licencia${succeeded !== 1 ? "s" : ""} enviada${succeeded !== 1 ? "s" : ""} a ISL`);
    }
    if (failed > 0) {
      toast.error(`${failed} licencia${failed !== 1 ? "s" : ""} fallaron al enviar a ISL`);
    }

    setSelectedIds(new Set());
    setIsBulkSending(false);
  }

  async function handleGenerarAlertas() {
    setIsGeneratingAlertas(true);
    try {
      const alertas = await generarAlertas.mutateAsync();
      toast.success(`${alertas.length} alerta${alertas.length !== 1 ? "s" : ""} generada${alertas.length !== 1 ? "s" : ""}`);
    } catch {
      toast.error("No se pudieron generar las alertas");
    } finally {
      setIsGeneratingAlertas(false);
    }
  }

  function handleAnular(row: LicenciaReadSlim) {
    setAnularTarget(row);
  }
  function handleISL(row: LicenciaReadSlim) {
    setIslTarget(row);
  }

  const hasSearched = folio.length > 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Licencias médicas</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            {hasSearched && !isFetching && licenciasResp
              ? `${historial.length} licencia${historial.length !== 1 ? "s" : ""} · ${diasAcumulados} días acumulados`
              : "Busca por folio para ver el historial de licencias."}
          </p>
        </div>
        {puedeCrear && (
          <div className="flex items-center gap-2">
            {/* Generar alertas de vencimiento — writers only */}
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerarAlertas}
              disabled={isGeneratingAlertas}
              aria-label="Generar alertas de vencimiento"
            >
              <Bell />
              Generar alertas
            </Button>

            {/* Envío masivo ISL — writers only, enabled when ≥1 row selected */}
            {/* NOTE: cross-region "envío por región" is not implemented — requires a
                backend global list endpoint that does not exist. Bulk send operates
                only over selected rows of the current folio (per-patient scope). */}
            <Button
              size="sm"
              variant="outline"
              onClick={handleBulkISL}
              disabled={selectedIds.size === 0 || isBulkSending}
              aria-label="Envío masivo ISL"
            >
              <Send />
              Envío masivo ISL
            </Button>

            <Button size="sm" onClick={() => setAltaOpen(true)}>
              <Plus /> Nueva licencia
            </Button>
          </div>
        )}
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Folio search */}
        <div className="relative w-[240px]">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input
            value={inputFolio}
            onChange={(e) => setInputFolio(e.target.value)}
            placeholder="Buscar por folio"
            className="h-9 pl-8 text-[13px]"
            aria-label="Buscar por folio"
          />
        </div>

        {/* Tipo LM filter */}
        <div className="relative">
          <select
            value={tipoFilter}
            onChange={(e) => setTipoFilter(e.target.value)}
            className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
          >
            <option value="Todos">Tipo LM: Todos</option>
            <option value="1">Tipo 1</option>
            <option value="5">Tipo 5</option>
            <option value="6">Tipo 6</option>
          </select>
          <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
        </div>

        {/* Reposo filter */}
        <div className="relative">
          <select
            value={reposoFilter}
            onChange={(e) => setReposoFilter(e.target.value)}
            className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
          >
            <option value="Todos">Reposo: Todos</option>
            <option value="total">Total</option>
            <option value="parcial">Parcial</option>
          </select>
          <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
        </div>

        {/* ISL Estado filter */}
        <div className="relative">
          <select
            value={islFilter}
            onChange={(e) => setIslFilter(e.target.value)}
            className="h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring appearance-none font-medium"
          >
            <option value="Todos">ISL: Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="enviado">Enviado</option>
            <option value="rechazado">Rechazado</option>
          </select>
          <ChevronRight className="absolute right-2 top-2.5 size-3.5 text-muted-foreground pointer-events-none rotate-90" />
        </div>

        {/* Selection count chip — writers only */}
        {puedeCrear && selectedIds.size > 0 && (
          <Badge variant="info" className="ml-1">
            {selectedIds.size} seleccionada{selectedIds.size !== 1 ? "s" : ""}
          </Badge>
        )}

        {hasSearched && !isFetching && (
          <Badge variant="neutral" className="ml-auto">
            {filtered.length} registros
          </Badge>
        )}
      </div>

      {/* States */}
      {!hasSearched && !isFetching && (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <Search className="mx-auto mb-3 size-8 text-muted-foreground/50" />
          <p className="text-[13.5px] text-muted-foreground">
            Ingresa un folio para ver sus licencias.
          </p>
        </div>
      )}

      {isFetching && (
        <p className="text-[13px] text-muted-foreground px-1">Buscando…</p>
      )}

      {hasSearched && !isFetching && historial.length === 0 && (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <p className="text-[13.5px] text-muted-foreground">
            Sin licencias para este folio.
          </p>
        </div>
      )}

      {/* Alta de licencia dialog — writers only */}
      {puedeCrear && (
        <AltaLicenciaDialog
          folio={folio || inputFolio.trim()}
          ingresoId={ingresoId}
          open={altaOpen}
          onOpenChange={setAltaOpen}
        />
      )}

      {/* Anular dialog — writers only; mounted when a row is targeted */}
      {puedeCrear && anularTarget && (
        <AnularLicenciaDialog
          licenciaId={anularTarget.id}
          folio={folio}
          open={anularTarget != null}
          onOpenChange={(open) => { if (!open) setAnularTarget(null); }}
        />
      )}

      {/* ISL dialog — writers only; mounted when a row is targeted */}
      {puedeCrear && islTarget && (
        <IslLicenciaDialog
          licenciaId={islTarget.id}
          folio={folio}
          open={islTarget != null}
          onOpenChange={(open) => { if (!open) setIslTarget(null); }}
        />
      )}

      {/* Table */}
      {!isFetching && filtered.length > 0 && (
        <>
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/30 border-b">
                    {/* Select-all header checkbox — writers only */}
                    {puedeCrear && (
                      <th className="px-4 py-3 w-10">
                        <Checkbox
                          checked={allSelected}
                          // indeterminate when some (not all) are selected
                          data-state={someSelected && !allSelected ? "indeterminate" : undefined}
                          onCheckedChange={handleToggleSelectAll}
                          aria-label="Seleccionar todas las licencias"
                        />
                      </th>
                    )}
                    <Th>Folio LM</Th>
                    <Th>Tipo</Th>
                    <Th>Reposo</Th>
                    <Th>Inicio</Th>
                    <Th>Fin / Vence</Th>
                    <Th>Días</Th>
                    <Th>GAF/EEAG</Th>
                    <Th>ISL</Th>
                    <Th>Estado</Th>
                    <Th>Acciones</Th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(({ slim, full }) => (
                    <LicenciaRow
                      key={slim.id}
                      slim={slim}
                      full={full}
                      canWrite={puedeCrear}
                      selected={selectedIds.has(slim.id)}
                      onToggleSelect={handleToggleRow}
                      onAnular={handleAnular}
                      onISL={handleISL}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Días acumulados strip */}
          <div
            className={cn(
              "flex items-center gap-3 rounded-lg border px-5 py-3",
              "bg-[oklch(0.96_0.08_85)] border-[oklch(0.88_0.10_85)] text-[oklch(0.42_0.14_75)]",
            )}
          >
            <span className="text-[13px] font-semibold">Días acumulados</span>
            <span className="text-[22px] font-bold tabular-nums leading-none">{diasAcumulados}</span>
            <span className="text-[12px] opacity-70">días totales para folio {licenciasResp?.folio}</span>
          </div>
        </>
      )}
    </div>
  );
}
