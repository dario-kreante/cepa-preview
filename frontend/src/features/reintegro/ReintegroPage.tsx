/**
 * ReintegroPage — workspace del módulo Seguimiento de Reintegro (EPIC-04).
 *
 * A diferencia de EPT, el backend SÍ expone listado (`GET /api/v1/reintegros?
 * ingreso_id=`). La navegación es paciente-driven:
 *   0. Sin buscar (QA-010): lista global de casos activos y «Pendientes por registrar».
 *   1. Buscar paciente → resolver ingreso_id vía Vista360 → listar sus casos +
 *      "Nuevo caso".
 *   2. Cargar por caso_id (input numérico o `?caso=<id>` en la URL).
 *   3. `?paciente=<id>&nuevo=1` (alerta de proyección, QA-010): carga el paciente; con un caso
 *      activo lo muestra y, sin él, abre «Nuevo caso de reintegro» precargado.
 *
 * RBAC: escritura = Coordinacion + Administrativo (puedeEscribir). Auditor lee.
 */
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Plus, AlertCircle, Hash, Pencil } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn, fmtDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useBuscarPacientes, useVista360 } from "@/features/ingresos/hooks";
import {
  useCaso,
  useCasosActivosDePaciente,
  useCasosPorIngreso,
  usePrecargaCaso,
  useReca,
} from "./hooks";
import { CasoRepetidoAviso } from "./CasoRepetidoAviso";
import { CasosRepetidosPanel } from "./CasosRepetidosPanel";
import { NuevoCasoReintegroDialog } from "./NuevoCasoReintegroDialog";
import { NuevaRecaDialog } from "./NuevaRecaDialog";
import { CierreDialog } from "./CierreDialog";
import { SolicitudRecaDialog } from "./SolicitudRecaDialog";
import { RemisionIslDialog } from "./RemisionIslDialog";
import { PanelReintegroGlobal } from "./PanelReintegroGlobal";
import {
  ESTADO_SOLICITUD_RECA_LABELS,
  ESTADO_SOLICITUD_RECA_VARIANT,
} from "./solicitudRecaSchema";
import { ESTADO_REINTEGRO_LABELS } from "./cierreSchema";
import {
  TIPO_TRABAJADOR_LABELS,
  TIPO_DERIVACION_VALUES,
  type CasoReintegroForm,
} from "./casoReintegroSchema";
import type { RecaForm } from "./recaSchema";
import type { CasoReintegroRead, EstadoReintegro, PendienteRegistro } from "./api";

function idDeParam(valor: string | null): number | null {
  const n = valor ? parseInt(valor, 10) : NaN;
  return Number.isInteger(n) && n > 0 ? n : null;
}

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

function RecaPanel({ caso, canWrite }: { caso: CasoReintegroRead; canWrite: boolean }) {
  const casoId = caso.id;
  const { data: reca, isLoading } = useReca(casoId);
  const [open, setOpen] = useState(false);
  const [solicitudOpen, setSolicitudOpen] = useState(false);
  const estadoSolicitud = caso.estado_solicitud_reca ?? "pendiente";

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

      {/* Solicitud de RECA (QA-003): estado derivado y fecha en que se pidió */}
      <div
        className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border border-border px-3 py-2"
        data-testid="solicitud-reca"
      >
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Solicitud de RECA
          </span>
          <Badge variant={ESTADO_SOLICITUD_RECA_VARIANT[estadoSolicitud]} data-testid="estado-solicitud-reca">
            {ESTADO_SOLICITUD_RECA_LABELS[estadoSolicitud]}
          </Badge>
        </div>
        <p className="text-[13px]" data-testid="fecha-solicitud-reca">
          {caso.fecha_solicitud_reca ? fmtDate(caso.fecha_solicitud_reca) : "Sin fecha de solicitud"}
        </p>
        {canWrite && (
          <Button
            size="sm"
            variant="outline"
            className="ml-auto h-7 text-[11.5px] px-2"
            onClick={() => setSolicitudOpen(true)}
            data-testid="btn-solicitud-reca"
          >
            {caso.fecha_solicitud_reca ? (
              <>
                <Pencil className="size-3 mr-1" /> Corregir fecha
              </>
            ) : (
              <>
                <Plus className="size-3 mr-1" /> Registrar solicitud
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

      {canWrite && <SolicitudRecaDialog caso={caso} open={solicitudOpen} onOpenChange={setSolicitudOpen} />}

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
  const [remisionOpen, setRemisionOpen] = useState(false);

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
    rut: caso.rut ?? "",
    nombre: caso.nombre,
    tipo_derivacion: caso.tipo_derivacion,
    fecha_caso: caso.fecha_caso,
    region: caso.region,
    comuna: caso.comuna ?? "",
    rubro_empleador: caso.rubro_empleador ?? "",
    razon_social: caso.razon_social ?? "",
    tipo_trabajador: caso.tipo_trabajador ?? "",
    ocupacion: caso.ocupacion ?? "",
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
          <Field label="Razón social empresa" value={caso.razon_social ?? "—"} />
          <Field
            label="Tipo de trabajador"
            value={
              caso.tipo_trabajador
                ? TIPO_TRABAJADOR_LABELS[caso.tipo_trabajador]
                : "—"
            }
          />
          <Field label="Ocupación" value={caso.ocupacion ?? "—"} />
          <Field label="Rubro empleador" value={caso.rubro_empleador ?? "—"} />
          <div>
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
              Remitido ISL
            </p>
            <div className="flex items-center gap-2">
              <p className="text-[13px]" data-testid="remitido-isl">
                {caso.remitido_isl
                  ? caso.fecha_remitido_isl
                    ? `Sí · ${fmtDate(caso.fecha_remitido_isl)}`
                    : "Sí"
                  : "No"}
              </p>
              {canWrite && caso.estado_reintegro !== "total" && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 text-[11px] px-2"
                  onClick={() => setRemisionOpen(true)}
                  data-testid="btn-remitido-isl"
                >
                  {caso.remitido_isl ? "Corregir fecha" : "Marcar remitido"}
                </Button>
              )}
            </div>
          </div>
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
            <RemisionIslDialog caso={caso} open={remisionOpen} onOpenChange={setRemisionOpen} />
          </>
        )}
      </Card>

      <RecaPanel caso={caso} canWrite={canWrite} />
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
  // Paciente seleccionado: desde la búsqueda, la lista global o `?paciente=` (alerta de proyección).
  const [selectedPacienteId, setSelectedPacienteId] = useState<number | null>(() =>
    idDeParam(searchParams.get("paciente")),
  );
  // Ingreso preferido (el del control de la proyección); si no, el principal del paciente.
  const [ingresoPreferido, setIngresoPreferido] = useState<number | null>(() =>
    idDeParam(searchParams.get("ingreso")),
  );
  // Pedido de alta pendiente (`?nuevo=1` o «Registrar caso»): se abre cuando el paciente cargó
  // y se confirmó que no tiene caso activo; con uno activo se muestra ese caso.
  const [quiereNuevo, setQuiereNuevo] = useState(() => searchParams.get("nuevo") === "1");

  useEffect(() => {
    const t = setTimeout(() => setQ(inputQ.trim()), 300);
    return () => clearTimeout(t);
  }, [inputQ]);

  function cambiarBusqueda(valor: string) {
    setInputQ(valor);
    setSelectedPacienteId(null);
    setIngresoPreferido(null);
    setQuiereNuevo(false);
  }

  const { data: pacientes = [], isFetching } = useBuscarPacientes(q);
  const { data: vista, isLoading: vistaLoading } = useVista360(selectedPacienteId);
  const ingresoElegido =
    vista?.ingresos?.find((i) => i.id === ingresoPreferido) ?? vista?.ingresos?.[0];
  const ingresoId: number | undefined = ingresoElegido?.id;
  const { data: casosIngreso = [] } = useCasosPorIngreso(ingresoId ?? null);
  // Casos activos del paciente en todos sus ingresos: base del aviso de caso repetido.
  const { data: casosActivos = [], isSuccess: activosCargados } =
    useCasosActivosDePaciente(selectedPacienteId);
  // Ocupación y tipo de trabajador de un caso anterior o de SALUTEM (QA-010).
  const { data: precarga } = usePrecargaCaso(canWrite ? (ingresoId ?? null) : null);

  // Precarga del alta con los datos del paciente y de su ingreso.
  const prefillCaso = useMemo<Partial<CasoReintegroForm> | undefined>(() => {
    if (!vista) return undefined;
    const p = vista.paciente;
    const ing = ingresoElegido;
    const prefill: Partial<CasoReintegroForm> = { rut: p.rut ?? "", nombre: p.nombre };
    if (p.region) prefill.region = p.region;
    if (ing?.razon_social) prefill.razon_social = ing.razon_social;
    if (ing && (TIPO_DERIVACION_VALUES as readonly string[]).includes(ing.tipo_derivacion)) {
      prefill.tipo_derivacion = ing.tipo_derivacion as CasoReintegroForm["tipo_derivacion"];
    }
    if (precarga?.ocupacion) prefill.ocupacion = precarga.ocupacion;
    if (precarga?.tipo_trabajador) prefill.tipo_trabajador = precarga.tipo_trabajador;
    return prefill;
  }, [vista, ingresoElegido, precarga]);

  const [casoIdInput, setCasoIdInput] = useState("");
  const [casoId, setCasoId] = useState<number | null>(() => idDeParam(searchParams.get("caso")));

  const [nuevaOpen, setNuevaOpen] = useState(false);
  const [avisoOpen, setAvisoOpen] = useState(false);
  const [repetidosOpen, setRepetidosOpen] = useState(false);

  // Derivados del pedido de alta: sin efectos (la regla de lint no permite setState en efectos).
  const pedidoListo = quiereNuevo && !!ingresoId && activosCargados;
  const abrirAltaPedida = pedidoListo && canWrite && casosActivos.length === 0;
  const casoActivoPedido = pedidoListo && casosActivos.length > 0 ? casosActivos[0].id : null;
  const casoMostrado = casoId ?? casoActivoPedido;
  const altaAbierta = nuevaOpen || abrirAltaPedida;

  function cambiarAlta(open: boolean) {
    setNuevaOpen(open);
    if (!open) setQuiereNuevo(false);
  }

  function registrarPendiente(p: PendienteRegistro) {
    setInputQ("");
    setQ("");
    setCasoId(null);
    setSelectedPacienteId(p.paciente_id);
    setIngresoPreferido(p.ingreso_id);
    setQuiereNuevo(true);
    window.scrollTo?.({ top: 0 });
  }

  function handleNuevoCaso() {
    // No bloquea: con casos activos se avisa primero; sin ellos se abre el formulario.
    if (casosActivos.length > 0) setAvisoOpen(true);
    else setNuevaOpen(true);
  }

  function abrirCaso(id: number) {
    setCasoId(id);
    setAvisoOpen(false);
    setQuiereNuevo(false);
    window.scrollTo?.({ top: 0 });
  }
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
            {/* BUG-2608-04/05: el botón depende de haber seleccionado un paciente. Antes quedaba
                deshabilitado sin decir por qué —y `disabled:pointer-events-none` impedía incluso
                el hover—, así que se leía como "el sistema no deja crear casos". El motivo ahora
                se explica en texto visible, no solo en un tooltip. */}
            <div className="flex flex-col items-end gap-1">
              <Button
                size="sm"
                aria-label="Nuevo caso de reintegro"
                data-testid="btn-nuevo-caso"
                aria-describedby={!ingresoId ? "nuevo-caso-requisito" : undefined}
                disabled={!ingresoId}
                onClick={handleNuevoCaso}
              >
                <Plus className="size-3.5" /> Nuevo caso
              </Button>
              {!ingresoId && (
                <p
                  id="nuevo-caso-requisito"
                  data-testid="nuevo-caso-requisito"
                  className="text-[11.5px] text-muted-foreground"
                >
                  Busca y selecciona un paciente para crear su caso
                </p>
              )}
            </div>
            {ingresoId && (
              <CasoRepetidoAviso
                casos={casosActivos}
                open={avisoOpen}
                onOpenChange={setAvisoOpen}
                onAbrir={abrirCaso}
                onContinuar={() => {
                  setAvisoOpen(false);
                  setNuevaOpen(true);
                }}
              />
            )}
            {ingresoId && (
              <NuevoCasoReintegroDialog
                ingresoId={ingresoId}
                prefill={prefillCaso}
                open={altaAbierta}
                onOpenChange={cambiarAlta}
                onSaved={(caso) => {
                  setCasoId(caso.id);
                  cambiarAlta(false);
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

      {/* Revisión de duplicados (solo lectura) */}
      <div className="space-y-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setRepetidosOpen((v) => !v)}
          aria-expanded={repetidosOpen}
          data-testid="btn-casos-repetidos"
        >
          {repetidosOpen ? "Ocultar casos repetidos" : "Revisar pacientes con casos repetidos"}
        </Button>
        {repetidosOpen && <CasosRepetidosPanel onAbrirCaso={abrirCaso} />}
      </div>

      {/* Caso activo */}
      {casoMostrado !== null && (
        <div className="space-y-2">
          <h2 className="text-[14px] font-semibold px-0.5">Caso activo</h2>
          <CasoPanel casoId={casoMostrado} canWrite={canWrite} />
        </div>
      )}

      {/* Búsqueda paciente */}
      <div className="space-y-3">
        <div className="relative w-[300px]">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input
            value={inputQ}
            onChange={(e) => cambiarBusqueda(e.target.value)}
            placeholder="Buscar por RUT, folio, nombre o ID SALUTEM"
            className="h-9 pl-8 text-[13px]"
            aria-label="Buscar pacientes"
          />
        </div>

        {/* QA-010: sin buscar, la lista global de casos activos y pendientes por registrar. */}
        {!hasSearched && selectedPacienteId === null && (
          <PanelReintegroGlobal
            onAbrirCaso={abrirCaso}
            onRegistrar={canWrite ? registrarPendiente : undefined}
          />
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
                    onClick={() => {
                      setSelectedPacienteId(p.id);
                      setIngresoPreferido(null);
                    }}
                    className={cn(
                      "border-b cursor-pointer transition-colors",
                      selectedPacienteId === p.id
                        ? "bg-primary/5 hover:bg-primary/10"
                        : "hover:bg-muted/40",
                    )}
                    aria-selected={selectedPacienteId === p.id}
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
        {selectedPacienteId !== null && (
          <div className="space-y-3">
            {vistaLoading && (
              <p className="text-[13px] text-muted-foreground px-1">
                Cargando ingreso del paciente…
              </p>
            )}

            {vista && (
              <p className="text-[13px] font-semibold px-1" data-testid="paciente-seleccionado">
                {vista.paciente.nombre}
                {vista.paciente.rut && (
                  <span className="ml-2 font-mono text-[12px] font-normal text-muted-foreground">
                    {vista.paciente.rut}
                  </span>
                )}
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
                              casoMostrado === c.id
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
