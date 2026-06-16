import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  Clock,
  Bell,
  CheckCircle2,
  Plus,
  FileText,
  Pill,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { useAlertas, useTareas } from "@/features/alertas/hooks";
import type { AlertaRead, TareaItemRead } from "@/features/alertas/api";

// ── visual helpers ────────────────────────────────────────────────────────────

type TabKey = "todas" | "criticas" | "proximas" | "info";
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

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-CL", {
      day: "2-digit",
      month: "short",
      year: "numeric",
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

// ── sub-components ────────────────────────────────────────────────────────────

interface AlertItemProps {
  bucket: BucketKey;
  title: string;
  subtitle: string;
  meta: string;
  onClick: () => void;
}

function AlertItem({ bucket, title, subtitle, meta, onClick }: AlertItemProps) {
  const Icon = ICON_MAP[bucket];
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-5 py-3 border-b hover:bg-muted/50 transition-colors flex gap-3 cursor-pointer"
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
        <div className="text-[12.5px] font-semibold leading-tight mb-0.5">
          {title}
        </div>
        <div className="text-[11px] text-muted-foreground truncate">
          {subtitle}
        </div>
        <div className="flex items-center gap-1.5 mt-1 text-[10.5px] text-muted-foreground">
          <span>{meta}</span>
        </div>
      </div>
    </button>
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

export function AlertsPanel() {
  const navigate = useNavigate();
  const { rol } = useAuth();
  const escritor = puedeEscribir(rol as Rol);

  const { data: alertas = [] } = useAlertas();
  const { data: tareas = [] } = useTareas();

  const [tab, setTab] = useState<TabKey>("todas");

  // Filter alertas to only pending/leidas (resolved are not shown)
  const activeAlertas = alertas.filter((a) => a.estado !== "resuelta");
  const activeTareas = tareas.filter((t) => t.estado !== "completada");

  const criticas = activeAlertas.filter((a) => a.estado === "pendiente");
  const proximas = activeAlertas.filter((a) => a.estado === "leida");
  const info = alertas.filter((a) => a.estado === "resuelta").slice(0, 5); // show recent resolved as "info"

  const totalCount = activeAlertas.length + activeTareas.length;
  const criticasCount = criticas.length;

  // Items to display per tab
  function getDisplayAlertas(): AlertaRead[] {
    if (tab === "todas") return activeAlertas;
    if (tab === "criticas") return criticas;
    if (tab === "proximas") return proximas;
    if (tab === "info") return info;
    return [];
  }

  const displayAlertas = getDisplayAlertas();
  const displayTareas = tab === "todas" || tab === "proximas" ? activeTareas : [];

  const handleAlertaClick = () => {
    // Deep-link by case ID/tipo comes in a later task — navigate to ingresos for now
    navigate("/ingresos");
  };

  const handleTareaClick = () => {
    navigate("/ingresos");
  };

  const TABS: { key: TabKey; label: string }[] = [
    { key: "todas", label: "Todas" },
    { key: "criticas", label: "Críticas" },
    { key: "proximas", label: "Próximas" },
    { key: "info", label: "Info" },
  ];

  return (
    <aside className="w-80 shrink-0 bg-card border-l flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-5 h-[3.75rem] border-b">
        <Bell className="size-4 text-primary" />
        <h3 className="text-sm font-bold">Alertas y tareas</h3>
        {criticasCount > 0 && (
          <span className="ml-auto size-5 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold grid place-items-center">
            {criticasCount}
          </span>
        )}
        {criticasCount === 0 && totalCount > 0 && (
          <span className="ml-auto size-5 rounded-full bg-muted text-muted-foreground text-[10px] font-bold grid place-items-center">
            {totalCount}
          </span>
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
            Sin alertas en esta categoría
          </div>
        )}

        {displayAlertas.map((a) => {
          const bucket = alertaTipoBucket(a);
          const title = cap(a.tipo.replace(/_/g, " "));
          const subtitle =
            a.caso_tipo && a.caso_id
              ? `${a.caso_tipo} #${a.caso_id}`
              : "—";
          const meta = a.plazo_objetivo
            ? `Plazo: ${formatDate(a.plazo_objetivo)}`
            : formatDate(a.generada_en);

          return (
            <AlertItem
              key={`alerta-${a.id}`}
              bucket={bucket}
              title={title}
              subtitle={subtitle}
              meta={meta}
              onClick={handleAlertaClick}
            />
          );
        })}

        {displayTareas.map((t) => (
          <TareaItem
            key={`tarea-${t.id}`}
            tarea={t}
            onClick={handleTareaClick}
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
              onClick={() => navigate("/ingresos/nuevo")}
            >
              <Plus className="size-3.5" /> Nuevo ingreso
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="justify-start h-8 text-[12px]"
            disabled
            title="Módulo de licencias no disponible aún"
          >
            <FileText className="size-3.5" /> Registrar licencia
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="justify-start h-8 text-[12px]"
            disabled
            title="Módulo de fármacos no disponible aún"
          >
            <Pill className="size-3.5" /> Nueva receta
          </Button>
        </div>
      </div>
    </aside>
  );
}
