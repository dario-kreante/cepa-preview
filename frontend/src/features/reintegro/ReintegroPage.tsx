/**
 * ReintegroPage — workspace del módulo Seguimiento de Reintegro (EPIC-04).
 *
 * A diferencia de EPT, el backend SÍ expone listado (`GET /api/v1/reintegros?
 * ingreso_id=`). La navegación es paciente-driven:
 *   1. Buscar paciente → resolver ingreso_id vía Vista360 → listar sus casos +
 *      "Nuevo caso".
 *   2. Cargar por caso_id (input numérico o `?caso=<id>` en la URL).
 *
 * RBAC: escritura = Coordinacion + Administrativo (puedeEscribir). Auditor lee.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Plus, RefreshCw, AlertCircle, Hash, Pencil } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useBuscarPacientes, useVista360 } from "@/features/ingresos/hooks";
import { useCaso, useCasosPorIngreso, useReca } from "./hooks";
import { NuevoCasoReintegroDialog } from "./NuevoCasoReintegroDialog";
import { NuevaRecaDialog } from "./NuevaRecaDialog";
import { CierreDialog } from "./CierreDialog";
import { ESTADO_REINTEGRO_LABELS } from "./cierreSchema";
import type { CasoReintegroForm } from "./casoReintegroSchema";
import type { RecaForm } from "./recaSchema";
import type { CasoReintegroRead, EstadoReintegro } from "./api";
import type { components } from "@/types/api";

type PacienteRead = components["schemas"]["PacienteRead"];

function estadoVariant(
  estado: EstadoReintegro,
): "info" | "warning" | "success" {
  if (estado === "total") return "success";
  if (estado === "parcial") return "warning";
  return "info";
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <p className="text-[13px]">{value}</p>
    </div>
  );
}

// ── RECA panel ────────────────────────────────────────────────────────────────

function RecaPanel({ casoId, canWrite }: { casoId: number; canWrite: boolean }) {
  const { data: reca, isLoading } = useReca(casoId);
  const [open, setOpen] = useState(false);

  const initialValues: RecaForm | undefined = reca
    ? {
        fecha_reca: reca.fecha_reca,
        tipo_reca: reca.tipo_reca,
        numero_reca: reca.numero_reca,
        razon_social: reca.razon_social,
        riesgos_calificados: reca.riesgos_calificados ?? "",
        solicita_medidas: reca.solicita_medidas,
        detalle_medidas: reca.detalle_medidas ?? "",
        fecha_medidas: reca.fecha_medidas ?? "",
        verifica_medidas: reca.verifica_medidas,
        detalle_verificacion: reca.detalle_verificacion ?? "",
        fecha_verificacion: reca.fecha_verificacion ?? "",
      }
    : undefined;

  return (
    <Card className="p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[14px] font-semibold">RECA y medidas correctivas</h3>
        {canWrite && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[11.5px] px-2"
            onClick={() => setOpen(true)}
            data-testid="btn-reca"
          >
            {reca ? (
              <>
                <Pencil className="size-3 mr-1" /> Editar RECA
              </>
            ) : (
              <>
                <Plus className="size-3 mr-1" /> Registrar RECA
              </>
            )}
          </Button>
        )}
      </div>

      {isLoading ? (
        <p className="text-[13px] text-muted-foreground">Cargando RECA…</p>
      ) : reca ? (
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="N° RECA" value={reca.numero_reca} />
          <Field label="Tipo" value={reca.tipo_reca} />
          <Field label="Fecha RECA" value={fmtDate(reca.fecha_reca)} />
          <Field label="Razón social" value={reca.razon_social} />
          <Field
            label="Solicita medidas"
            value={reca.solicita_medidas ? "Sí" : "No"}
          />
          <Field
            label="Verifica medidas"
            value={reca.verifica_medidas ? "Sí" : "No"}
          />
        </div>
      ) : (
        <p className="text-[13px] text-muted-foreground">
          Sin RECA registrada para este caso.
        </p>
      )}

      {canWrite && (
        <NuevaRecaDialog
          casoId={casoId}
          open={open}
          onOpenChange={setOpen}
          initialValues={initialValues}
          isEdit={!!reca}
        />
      )}
    </Card>
  );
}

// ── Caso detail + cierre ──────────────────────────────────────────────────────

function CasoPanel({
  casoId,
  canWrite,
}: {
  casoId: number;
  canWrite: boolean;
}) {
  const { data: caso, isLoading, isError, error } = useCaso(casoId);
  const [editOpen, setEditOpen] = useState(false);
  const [cierreOpen, setCierreOpen] = useState(false);

  if (isLoading)
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        Cargando caso {casoId}…
      </p>
    );

  if (isError) {
    const msg =
      error instanceof Error ? error.message : "No se pudo cargar el caso";
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-start gap-2">
        <AlertCircle className="size-4 text-destructive mt-0.5 shrink-0" />
        <p className="text-[13px] text-destructive">{msg}</p>
      </div>
    );
  }

  if (!caso) return null;

  const initialValues: CasoReintegroForm = {
    rut: caso.rut,
    nombre: caso.nombre,
    tipo_derivacion: caso.tipo_derivacion,
    fecha_caso: caso.fecha_caso,
    sexo: caso.sexo as CasoReintegroForm["sexo"],
    edad: caso.edad,
    region: caso.region,
    comuna: caso.comuna ?? "",
    rubro_empleador: caso.rubro_empleador ?? "",
  };

  return (
    <div className="space-y-4">
      <Card className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Caso N° {caso.id}
            </p>
            <h2 className="text-[16px] font-semibold">{caso.nombre}</h2>
            <p className="text-[12.5px] text-muted-foreground font-mono">
              {caso.rut}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge variant={estadoVariant(caso.estado_reintegro)}>
              {ESTADO_REINTEGRO_LABELS[caso.estado_reintegro]}
            </Badge>
            {canWrite && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-[11.5px] px-2"
                  data-testid="btn-editar-caso"
                  onClick={() => setEditOpen(true)}
                >
                  <Pencil className="size-3 mr-1" /> Editar
                </Button>
                <Button
                  size="sm"
                  className="h-7 text-[11.5px] px-2"
                  data-testid="btn-cierre"
                  onClick={() => setCierreOpen(true)}
                >
                  Reintegro / cierre
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Tipo derivación" value={caso.tipo_derivacion} />
          <Field label="Fecha caso" value={fmtDate(caso.fecha_caso)} />
          <Field label="Región" value={caso.region} />
          <Field label="Comuna" value={caso.comuna ?? "—"} />
          <Field label="Edad / Sexo" value={`${caso.edad} · ${caso.sexo}`} />
          <Field label="Rubro empleador" value={caso.rubro_empleador ?? "—"} />
          <Field
            label="Remitido ISL"
            value={caso.remitido_isl ? "Sí" : "No"}
          />
          <Field
            label="Fecha reintegro"
            value={caso.fecha_reintegro ? fmtDate(caso.fecha_reintegro) : "—"}
          />
          <Field
            label="Alta médica"
            value={
              caso.alta_medica
                ? caso.fecha_alta_medica
                  ? fmtDate(caso.fecha_alta_medica)
                  : "Sí"
                : "No"
            }
          />
          <Field
            label="Alta psicológica"
            value={
              caso.alta_psicologica
                ? caso.fecha_alta_psico
                  ? fmtDate(caso.fecha_alta_psico)
                  : "Sí"
                : "No"
            }
          />
        </div>

        {canWrite && (
          <>
            <NuevoCasoReintegroDialog
              ingresoId={caso.ingreso_id}
              open={editOpen}
              onOpenChange={setEditOpen}
              onSaved={() => setEditOpen(false)}
              initialValues={initialValues}
              casoId={caso.id}
            />
            <CierreDialog
              caso={caso}
              open={cierreOpen}
              onOpenChange={setCierreOpen}
            />
          </>
        )}
      </Card>

      <RecaPanel casoId={casoId} canWrite={canWrite} />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ReintegroPage() {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);
  const [searchParams] = useSearchParams();

  const [inputQ, setInputQ] = useState("");
  const [q, setQ] = useState("");
  const [selectedPaciente, setSelectedPaciente] = useState<PacienteRead | null>(
    null,
  );

  useEffect(() => {
    const t = setTimeout(() => {
      setQ(inputQ.trim());
      setSelectedPaciente(null);
    }, 300);
    return () => clearTimeout(t);
  }, [inputQ]);

  const { data: pacientes = [], isFetching } = useBuscarPacientes(q);
  const { data: vista, isLoading: vistaLoading } = useVista360(
    selectedPaciente?.id ?? null,
  );
  const ingresoId: number | undefined = vista?.ingresos?.[0]?.id;
  const { data: casosIngreso = [] } = useCasosPorIngreso(ingresoId ?? null);

  const [casoIdInput, setCasoIdInput] = useState("");
  const [casoId, setCasoId] = useState<number | null>(() => {
    const param = searchParams.get("caso");
    const n = param ? parseInt(param, 10) : NaN;
    return Number.isInteger(n) && n > 0 ? n : null;
  });

  const [nuevaOpen, setNuevaOpen] = useState(false);
  const hasSearched = q.length > 0;

  function handleLoadCaso() {
    const parsed = parseInt(casoIdInput, 10);
    if (!isNaN(parsed) && parsed > 0) setCasoId(parsed);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">
            Seguimiento de reintegro
          </h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Reintegro laboral · RECA, medidas correctivas y cierre del caso
          </p>
        </div>
        {canWrite && (
          <>
            <Button
              size="sm"
              aria-label="Nuevo caso de reintegro"
              data-testid="btn-nuevo-caso"
              disabled={!ingresoId}
              onClick={() => setNuevaOpen(true)}
            >
              <Plus className="size-3.5" /> Nuevo caso
            </Button>
            {ingresoId && (
              <NuevoCasoReintegroDialog
                ingresoId={ingresoId}
                open={nuevaOpen}
                onOpenChange={setNuevaOpen}
                onSaved={(caso) => {
                  setCasoId(caso.id);
                  setNuevaOpen(false);
                }}
              />
            )}
          </>
        )}
      </div>

      {/* Cargar por caso_id */}
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

      {/* Caso activo */}
      {casoId !== null && (
        <div className="space-y-2">
          <h2 className="text-[14px] font-semibold px-0.5">Caso activo</h2>
          <CasoPanel casoId={casoId} canWrite={canWrite} />
        </div>
      )}

      {/* Búsqueda paciente */}
      <div className="space-y-3">
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

        {!hasSearched && !isFetching && casoId === null && (
          <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
            <RefreshCw className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-[13.5px] text-muted-foreground">
              Busca un paciente para ver o crear sus casos de reintegro, o carga
              un caso existente por su número.
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

        {!isFetching && pacientes.length > 0 && (
          <Card className="overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
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
                        : "hover:bg-muted/40",
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
          </Card>
        )}

        {/* Paciente seleccionado → casos del ingreso */}
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
              <div className="space-y-2">
                <p className="text-[12.5px] text-muted-foreground px-1">
                  Ingreso N° {ingresoId} ·{" "}
                  {casosIngreso.length === 0
                    ? "sin casos de reintegro"
                    : `${casosIngreso.length} caso(s) de reintegro`}
                </p>
                {casosIngreso.length > 0 && (
                  <Card className="overflow-hidden p-0">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-muted/30 border-b">
                          <Th>Caso</Th>
                          <Th>Fecha</Th>
                          <Th>Estado</Th>
                        </tr>
                      </thead>
                      <tbody>
                        {casosIngreso.map((c: CasoReintegroRead) => (
                          <tr
                            key={c.id}
                            onClick={() => setCasoId(c.id)}
                            className={cn(
                              "border-b cursor-pointer transition-colors",
                              casoId === c.id
                                ? "bg-primary/5 hover:bg-primary/10"
                                : "hover:bg-muted/40",
                            )}
                            data-testid={`row-caso-${c.id}`}
                          >
                            <td className="px-4 py-3 font-semibold text-[13px]">
                              N° {c.id} · {c.nombre}
                            </td>
                            <td className="px-4 py-3 font-mono text-[12px]">
                              {fmtDate(c.fecha_caso)}
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant={estadoVariant(c.estado_reintegro)}>
                                {ESTADO_REINTEGRO_LABELS[c.estado_reintegro]}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </Card>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
