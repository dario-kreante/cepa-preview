import { Link, useLocation } from "react-router-dom";
import { Bell, HelpCircle } from "lucide-react";
import { TITLE_MAP, CRUMBS_MAP } from "@/app/shell/nav";
import { cn } from "@/lib/utils";
import { guiaDeRuta } from "@/features/ayuda/contenido";

interface TopbarProps {
  alertsVisible: boolean;
  onToggleAlerts: () => void;
  /** Alertas sin leer de quien mira (asignadas a ella o sin dueño): el número de la campana. */
  alertasSinLeer: number;
}

/**
 * Resolves the closest matching path key in a map.
 * Tries exact match first, then the first prefix that starts the pathname.
 */
function resolvePathKey(
  map: Record<string, string>,
  pathname: string,
): string | undefined {
  if (map[pathname] !== undefined) return pathname;
  // Try longest prefix match (e.g. /pacientes/123 → /)
  const sorted = Object.keys(map).sort((a, b) => b.length - a.length);
  return sorted.find((k) => k !== "/" && pathname.startsWith(k));
}

export function Topbar({
  alertsVisible,
  onToggleAlerts,
  alertasSinLeer,
}: TopbarProps) {
  const { pathname } = useLocation();

  const titleKey = resolvePathKey(TITLE_MAP, pathname);
  const title = (titleKey && TITLE_MAP[titleKey]) ?? "SIGE";

  const crumbsKey = resolvePathKey(CRUMBS_MAP, pathname);
  const crumbs = (crumbsKey && CRUMBS_MAP[crumbsKey]) ?? "Inicio";

  // El (?) abre la guía de la pantalla actual; fuera de una pantalla con guía, la portada.
  const guia = pathname === "/ayuda" ? undefined : guiaDeRuta(pathname);
  const ayudaHref = guia ? `/ayuda?guia=${encodeURIComponent(guia)}` : "/ayuda";

  return (
    <header className="h-14 bg-card border-b flex items-center px-6 gap-3 sticky top-0 z-20">
      <div>
        <h1 className="text-[15px] font-semibold tracking-tight leading-none">
          {title}
        </h1>
        <p className="text-[11px] text-muted-foreground mt-1">{crumbs}</p>
      </div>

      <div className="flex-1" />

      <Link
        to={ayudaHref}
        title={guia ? "Ayuda sobre esta pantalla" : "Ayuda"}
        aria-label={guia ? "Ayuda sobre esta pantalla" : "Ayuda"}
        className="size-9 rounded-md grid place-items-center hover:bg-muted transition-colors cursor-pointer text-muted-foreground hover:text-foreground"
      >
        <HelpCircle className="size-[18px]" />
      </Link>

      <button
        onClick={onToggleAlerts}
        title={alertsVisible ? "Ocultar alertas" : "Mostrar alertas"}
        aria-label={
          alertasSinLeer > 0 ? `Alertas: ${alertasSinLeer} sin leer` : "Alertas"
        }
        aria-expanded={alertsVisible}
        className={cn(
          "size-9 rounded-md grid place-items-center hover:bg-muted transition-colors relative cursor-pointer text-muted-foreground hover:text-foreground",
          alertsVisible && "bg-muted text-foreground",
        )}
      >
        <Bell className="size-[18px]" />
        {alertasSinLeer > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold leading-[18px] text-center ring-2 ring-card">
            {alertasSinLeer > 99 ? "99+" : alertasSinLeer}
          </span>
        )}
      </button>
    </header>
  );
}
