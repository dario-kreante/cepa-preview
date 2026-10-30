import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertCircle,
  Clock,
  Bell,
  CheckCircle2,
  Plus,
  FileText,
  Pill,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useActualizarAlerta, useAlertas, useTareas } from "@/features/alertas/hooks";
import type { AlertaRead, TareaItemRead } from "@/features/alertas/api";
import { DocumentosAlertaDialog, type CasoAlerta } from "./DocumentosAlertaDialog";

// ── visual helpers ────────────────────────────────────────────────────────────

type TabKey = "todas" | "sin_leer" | "resueltas";
type BucketKey = "criticas" | "proximas" | "info";

/**
 * Classify AlertaRead into a visual "tipo" bucket:
 *  - "criticas" : estado == "pendiente" (urgent, action needed)
 *  - "proximas" : estado == "leida"     (acknowledged but unresolved)
 *  - "info"     : anything else / resuelta
 */
function alertaTipoBucket(a: AlertaRead): BucketKey {
  if (a.estado === "pendiente") return "criticas";
  if (a.estado === "leida") return "proximas";
  return "info";
}

const ICON_MAP = {
  criticas: AlertCircle,
  proximas: Clock,
  info: Bell,
  tarea: CheckCircle2,
} as const;

const STYLE_MAP: Record<string, string> = {
  criticas: "bg-destructive/10 text-destructive",
  proximas:
    "bg-[oklch(0.96_0.08_85)] text-[oklch(0.52_0.16_75)]",
  info: "bg-[oklch(0.94_0.04_230)] text-[oklch(0.42_0.14_230)]",
  tarea: "bg-[oklch(0.94_0.05_155)] text-[oklch(0.40_0.12_155)]",
};

// ── date formatting ───────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-CL", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone,
    });
  } catch {
    return "—";
  }
}

function todayLabel(): string {
  return new Date().toLocaleDateString("es-CL", {
    weekday: "long",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// Capitalize first letter
function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const TITULOS_ALERTA: Record<string, string> = {
  licencia_en_control: "Licencia emitida en control",
  receta_en_control: "Receta emitida en control",
  paciente_pendiente_folio: "Paciente nuevo pendiente de folio",
  inasistencia: "Inasistencia a cita",
  posible_encuadre: "Posible encuadre: 2 o más inasistencias",
  cita_fuera_de_oda: "Cita fuera de la vigencia de la ODA",
};

/** Alertas de un control médico: al hacer clic abren sus documentos en un diálogo. */
const TIPOS_DE_CONTROL = ["licencia_en_control", "receta_en_control"];

/** Alertas de una atención médica que no es control (Evaluación médica, psiquiátrica…). */
const CASO_ATENCION = "salutem_atencion";

const TITULOS_ATENCION: Record<string, string> = {
  licencia_en_control: "Licencia emitida en atención médica",
  receta_en_control: "Receta emitida en atención médica",
};

export function tituloAlerta(tipo: string, casoTipo?: string | null): string {
  if (casoTipo === CASO_ATENCION && TITULOS_ATENCION[tipo]) return TITULOS_ATENCION[tipo];
  return TITULOS_ALERTA[tipo] ?? cap(tipo.replace(/_/g, " "));
}

const ETIQUETAS_CASO: Record<string, string> = {
  control_medico: "Control",
  [CASO_ATENCION]: "Atención SALUTEM",
  salutem_cita: "Cita SALUTEM",
  paciente: "Paciente",
};

function subtituloCaso(casoTipo: string | null | undefined, casoId: number | null | undefined): string {
  if (!casoTipo || !casoId) return "—";
  return `${ETIQUETAS_CASO[casoTipo] ?? casoTipo} #${casoId}`;
}

/**
 * Una alerta es "para mí" si me la asignaron o no tiene dueño. Coordinación ve también las
 * de otros profesionales, pero esas no las lee ella: la leída es de quien la tiene asignada.
 */
export function esParaMi(a: AlertaRead, usuarioId: number | null | undefined): boolean {
  return a.usuario_id === null || a.usuario_id === usuarioId;
}

/** Alertas que la persona todavía no ha visto: el número de la campana. */
export function alertasSinLeer(alertas: AlertaRead[], usuarioId: number | null | undefined) {
  return alertas.filter((a) => a.estado === "pendiente" && esParaMi(a, usuarioId));
}

/**
 * Mapea un caso (caso_tipo + caso_id) a la ruta de su módulo. Los valores de
 * caso_tipo provienen del generador de alertas: oda, licencia, ept, ingreso,
 * control_medico, receta, paciente. EPT acepta deep-link por ?caso=; ODA e ingreso abren
 * la ficha del paciente (?paciente=, y la pestaña ODA) cuando la alerta trae paciente_id;
 * el resto navega a su página (paciente-driven, sin parámetro de caso).
 */
export function routeForCaso(
  casoTipo: string | null | undefined,
  casoId: number | null | undefined,
  pacienteId?: number | null,
): string {
  if (pacienteId && casoTipo === "oda") return `/ingresos?paciente=${pacienteId}&tab=odas`;
  if (pacienteId && (casoTipo === "ingreso" || casoTipo === "salutem_cita"))
    return `/ingresos?paciente=${pacienteId}`;
  switch (casoTipo) {
    case "ept":
      return casoId ? `/ept?caso=${casoId}` : "/ept";
    case "control_medico":
      return "/controles";
    case "salutem_cita":
      return "/ingresos";
    case "receta":
      return "/farmacos";
    case "licencia":
      return "/licencias";
    case "paciente":
      return "/pendientes-folio";
    case "oda":
    case "ingreso":
    default:
      return "/ingresos";
  }
}

// ── sub-components ────────────────────────────────────────────────────────────

interface AlertItemProps {
  bucket: BucketKey;
  title: string;
  subtitle: string;
  meta: string;
  onClick: () => void;
  /** Pendiente y para quien mira: se destaca hasta que la vea. */
  sinLeer?: boolean;
  /** Asignada a otro profesional (solo la ve Coordinación). */
  ajena?: boolean;
  /** Se llama una vez cuando la alerta estuvo a la vista VISTA_MS seguidos (para marcarla leída). */
  onVista?: () => void;
  /** Solo para quien puede gestionar alertas; sin él la alerta es de solo lectura. */
  onResolver?: () => void;
  ocupado?: boolean;
}

/** Texto de fecha de una alerta según su tipo; sin plazo, cuándo se generó. */
function metaAlerta(
  a: {
    tipo: string;
    caso_tipo?: string | null;
    plazo_objetivo?: string | null;
    generada_en: string;
  },
  esDeControl: boolean,
): string {
  if (!a.plazo_objetivo) return formatDate(a.generada_en);
  if (a.tipo === "inasistencia" || a.tipo === "posible_encuadre" || a.tipo === "cita_fuera_de_oda")
    return `Cita: ${formatDate(a.plazo_objetivo, "UTC")}`;
  if (esDeControl) {
    const etiqueta = a.caso_tipo === CASO_ATENCION ? "Atención" : "Control";
    return `${etiqueta}: ${formatDate(a.plazo_objetivo, "UTC")}`;
  }
  return `Plazo: ${formatDate(a.plazo_objetivo)}`;
}

/** Tiempo que una alerta tiene que estar en pantalla para darla por leída. */
const VISTA_MS = 1500;

/**
 * Llama a `onVista` una sola vez cuando el elemento estuvo al menos 60% visible durante
 * VISTA_MS seguidos: pasar de largo al hacer scroll no cuenta como haberla leído.
 */
function useVistaDurante(onVista: (() => void) | undefined) {
  const ref = useRef<HTMLDivElement>(null);
  const llamar = useRef(onVista);
  useEffect(() => {
    llamar.current = onVista;
  });
  const activo = onVista !== undefined;

  useEffect(() => {
    const el = ref.current;
    if (!activo || !el || typeof IntersectionObserver === "undefined") return;
    let temporizador: ReturnType<typeof setTimeout> | undefined;
    let hecho = false;
    const observador = new IntersectionObserver(
      (entradas) => {
        const visible = entradas.some((e) => e.isIntersecting);
        if (visible && !temporizador && !hecho) {
          temporizador = setTimeout(() => {
            hecho = true;
            observador.disconnect();
            llamar.current?.();
          }, VISTA_MS);
        } else if (!visible && temporizador) {
          clearTimeout(temporizador);
          temporizador = undefined;
        }
      },
      { threshold: 0.6 },
    );
    observador.observe(el);
    return () => {
      clearTimeout(temporizador);
      observador.disconnect();
    };
  }, [activo]);

  return ref;
}

function AlertItem({
  bucket,
  title,
  subtitle,
  meta,
  onClick,
  sinLeer = false,
  ajena = false,
  onVista,
  onResolver,
  ocupado = false,
}: AlertItemProps) {
  const Icon = ICON_MAP[bucket];
  const ref = useVistaDurante(onVista);
  return (
    <div
      ref={ref}
      data-sin-leer={sinLeer || undefined}
      className={cn(
        "relative border-b transition-colors",
        sinLeer ? "bg-primary/[0.06] hover:bg-primary/10" : "hover:bg-muted/50",
      )}
    >
      {sinLeer && (
        <span
          aria-label="Sin leer"
          className="absolute left-2 top-[1.35rem] size-1.5 rounded-full bg-primary"
        />
      )}
      <button
        onClick={onClick}
        className="w-full text-left px-5 pt-3 pb-2 flex gap-3 cursor-pointer"
      >
        <div
          className={cn(
            "size-8 rounded-lg grid place-items-center shrink-0",
            STYLE_MAP[bucket],
          )}
        >
          <Icon className="size-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div
            className={cn(
              "text-[12.5px] leading-tight mb-0.5",
              sinLeer ? "font-bold" : "font-medium",
            )}
          >
            {title}
          </div>
          <div className="text-[11px] text-muted-foreground truncate">
            {subtitle}
          </div>
          <div className="flex items-center gap-1.5 mt-1 text-[10.5px] text-muted-foreground">
            <span>{meta}</span>
            {ajena && (
              <>
                <span>•</span>
                <span>Asignada a otro profesional</span>
              </>
            )}
          </div>
        </div>
      </button>
      {onResolver && (
        <div className="flex gap-3 pl-16 pr-5 pb-2.5 text-[11px]">
          <button
            type="button"
            disabled={ocupado}
            onClick={onResolver}
            aria-label={`Resolver: ${title}`}
            className="text-muted-foreground hover:text-foreground underline-offset-2 hover:underline disabled:opacity-50"
          >
            Resolver
          </button>
        </div>
      )}
    </div>
  );
}

interface TareaItemProps {
  tarea: TareaItemRead;
  onClick: () => void;
}

function TareaItem({ tarea, onClick }: TareaItemProps) {
  const Icon = ICON_MAP["tarea"];
  const subtitle =
    tarea.caso_tipo && tarea.caso_id
      ? `${tarea.caso_tipo} #${tarea.caso_id}`
      : "—";
  const meta = formatDate(tarea.creada_en);

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-5 py-3 border-b hover:bg-muted/50 transition-colors flex gap-3 cursor-pointer"
    >
      <div
        className={cn(
          "size-8 rounded-lg grid place-items-center shrink-0",
          STYLE_MAP["tarea"],
        )}
      >
        <Icon className="size-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] font-semibold leading-tight mb-0.5">
          {tarea.titulo}
        </div>
        <div className="text-[11px] text-muted-foreground truncate">
          {subtitle}
        </div>
        <div className="flex items-center gap-1.5 mt-1 text-[10.5px] text-muted-foreground">
          <span className="capitalize">{tarea.tipo_tarea}</span>
          <span>•</span>
          <span>{meta}</span>
        </div>
      </div>
    </button>
  );
}

// ── main panel ────────────────────────────────────────────────────────────────

interface AlertsPanelProps {
  /** Cierra la ventana flotante (también al navegar desde una alerta o tarea). */
  onClose?: () => void;
}

export function AlertsPanel({ onClose }: AlertsPanelProps = {}) {
  const navigate = useNavigate();
  const { rol, usuarioId } = useAuth();
  const escritor = puedeEscribir(rol as Rol);

  const { data: alertas = [] } = useAlertas();
  const { data: tareas = [] } = useTareas();
  const actualizar = useActualizarAlerta();

  const cambiarEstado = (a: AlertaRead, estado: "leida" | "resuelta") =>
    actualizar.mutate(
      { id: a.id, estado },
      { onError: () => toast.error("No se pudo actualizar la alerta. Intenta de nuevo.") },
    );

  const [tab, setTab] = useState<TabKey>("todas");
  const [alertaControl, setAlertaControl] = useState<AlertaRead | null>(null);
  const casoAbierto: CasoAlerta | null =
    alertaControl?.caso_id != null
      ? { tipo: alertaControl.caso_tipo === CASO_ATENCION ? "atencion" : "control", id: alertaControl.caso_id }
      : null;

  // "Todas" son las abiertas (pendientes y leídas); las resueltas tienen su pestaña.
  const activeAlertas = alertas.filter((a) => a.estado !== "resuelta");
  const activeTareas = tareas.filter((t) => t.estado !== "completada");
  const sinLeer = alertasSinLeer(alertas, usuarioId);
  const resueltas = alertas.filter((a) => a.estado === "resuelta").slice(0, 20);

  const displayAlertas =
    tab === "todas" ? activeAlertas : tab === "sin_leer" ? sinLeer : resueltas;
  const displayTareas = tab === "todas" ? activeTareas : [];

  const ir = (ruta: string) => {
    navigate(ruta);
    onClose?.();
  };

  const handleAlertaClick = (a: AlertaRead) => {
    if (TIPOS_DE_CONTROL.includes(a.tipo)) {
      setAlertaControl(a);
      return;
    }
    ir(routeForCaso(a.caso_tipo, a.caso_id, a.paciente_id));
  };

  const handleTareaClick = (t: TareaItemRead) => {
    ir(routeForCaso(t.caso_tipo, t.caso_id));
  };

  const TABS: { key: TabKey; label: string }[] = [
    { key: "todas", label: "Todas" },
    { key: "sin_leer", label: sinLeer.length ? `Sin leer (${sinLeer.length})` : "Sin leer" },
    { key: "resueltas", label: "Resueltas" },
  ];

  return (
    <aside
      aria-label="Alertas y tareas"
      className="w-[380px] max-w-[calc(100vw-1.5rem)] max-h-[min(640px,calc(100vh-5rem))] bg-card border rounded-xl shadow-2xl flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2 pl-5 pr-2 h-12 border-b">
        <Bell className="size-4 text-primary" />
        <h3 className="text-sm font-bold">Alertas y tareas</h3>
        {sinLeer.length > 0 && (
          <span className="text-[11px] text-muted-foreground">· {sinLeer.length} sin leer</span>
        )}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar alertas"
            className="ml-auto size-8 rounded-md grid place-items-center text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-2 border-b bg-muted/30">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "flex-1 text-[11px] font-semibold py-1.5 rounded-md transition-colors cursor-pointer",
              tab === t.key
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Date header */}
      <div className="px-5 py-2 bg-muted/40 border-b">
        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
          Hoy · {cap(todayLabel())}
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto">
        {displayAlertas.length === 0 && displayTareas.length === 0 && (
          <div className="px-5 py-8 text-center text-[12px] text-muted-foreground">
            {tab === "sin_leer" ? "No tienes alertas sin leer" : "Sin alertas en esta categoría"}
          </div>
        )}

        {displayAlertas.map((a) => {
          const bucket = alertaTipoBucket(a);
          const title = tituloAlerta(a.tipo, a.caso_tipo);
          const subtitle = subtituloCaso(a.caso_tipo, a.caso_id);
          // En licencia/receta de un control, plazo_objetivo es la fecha del control a medianoche
          // UTC: en hora local de Chile caería el día anterior.
          const esDeControl = a.tipo === "licencia_en_control" || a.tipo === "receta_en_control";
          const meta = metaAlerta(a, esDeControl);

          return (
            <AlertItem
              key={`alerta-${a.id}`}
              bucket={bucket}
              title={title}
              subtitle={subtitle}
              meta={meta}
              onClick={() => handleAlertaClick(a)}
              sinLeer={a.estado === "pendiente" && esParaMi(a, usuarioId)}
              ajena={!esParaMi(a, usuarioId)}
              onVista={
                // Se marca leída al verla, solo si es de quien la mira o no tiene dueño:
                // Coordinación ve todas y no debe "leer" las de otra persona.
                escritor &&
                a.estado === "pendiente" &&
                esParaMi(a, usuarioId)
                  ? () => actualizar.mutate({ id: a.id, estado: "leida" })
                  : undefined
              }
              onResolver={
                escritor && a.estado !== "resuelta" ? () => cambiarEstado(a, "resuelta") : undefined
              }
              ocupado={actualizar.isPending}
            />
          );
        })}

        {displayTareas.map((t) => (
          <TareaItem
            key={`tarea-${t.id}`}
            tarea={t}
            onClick={() => handleTareaClick(t)}
          />
        ))}
      </div>

      {/* Quick actions */}
      <div className="p-4 border-t bg-muted/30">
        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
          Accesos rápidos
        </div>
        <div className="flex flex-col gap-1">
          {escritor && (
            <Button
              variant="ghost"
              size="sm"
              className="justify-start h-8 text-[12px]"
              onClick={() => ir("/ingresos/nuevo")}
            >
              <Plus className="size-3.5" /> Nuevo ingreso
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="justify-start h-8 text-[12px]"
            onClick={() => ir("/licencias")}
          >
            <FileText className="size-3.5" /> Registrar licencia
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="justify-start h-8 text-[12px]"
            onClick={() => ir("/farmacos")}
          >
            <Pill className="size-3.5" /> Nueva receta
          </Button>
        </div>
      </div>

      <DocumentosAlertaDialog
        titulo={alertaControl ? tituloAlerta(alertaControl.tipo, alertaControl.caso_tipo) : ""}
        caso={casoAbierto}
        onOpenChange={(open) => !open && setAlertaControl(null)}
        alertaId={alertaControl?.id ?? null}
        tipoAlerta={alertaControl?.tipo}
        pendiente={alertaControl ? alertaControl.estado !== "resuelta" : false}
        puedeGestionar={escritor}
        onResolver={alertaControl ? () => cambiarEstado(alertaControl, "resuelta") : undefined}
        onIr={ir}
      />
    </aside>
  );
}
