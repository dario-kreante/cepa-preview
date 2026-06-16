import { useLocation } from "react-router-dom";
import { Bell, HelpCircle } from "lucide-react";
import { TITLE_MAP, CRUMBS_MAP } from "@/app/shell/nav";

interface TopbarProps {
  alertsVisible: boolean;
  onToggleAlerts: () => void;
  /** Count of pending/critical alertas to show the "críticas" pill */
  alertasCriticas: number;
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
  alertasCriticas,
}: TopbarProps) {
  const { pathname } = useLocation();

  const titleKey = resolvePathKey(TITLE_MAP, pathname);
  const title = (titleKey && TITLE_MAP[titleKey]) ?? "SIGE";

  const crumbsKey = resolvePathKey(CRUMBS_MAP, pathname);
  const crumbs = (crumbsKey && CRUMBS_MAP[crumbsKey]) ?? "Inicio";

  return (
    <header className="h-14 bg-card border-b flex items-center px-6 gap-3 sticky top-0 z-20">
      <div>
        <h1 className="text-[15px] font-semibold tracking-tight leading-none">
          {title}
        </h1>
        <p className="text-[11px] text-muted-foreground mt-1">{crumbs}</p>
      </div>

      <div className="flex-1" />

      {/* Active cases pill — placeholder count until Dashboard module provides it */}
      <div className="flex items-center gap-2 bg-[oklch(0.96_0.05_155)] text-[oklch(0.38_0.12_155)] border border-[oklch(0.88_0.05_155)] px-2.5 py-1 rounded-full text-[11px] font-semibold">
        <span className="size-1.5 rounded-full bg-[oklch(0.64_0.14_155)]" />
        — activos
      </div>

      {/* Critical alerts pill */}
      <div className="flex items-center gap-2 bg-destructive/10 text-destructive border border-destructive/20 px-2.5 py-1 rounded-full text-[11px] font-semibold">
        <span className="size-1.5 rounded-full bg-destructive animate-pulse" />
        {alertasCriticas > 0 ? `${alertasCriticas} críticas` : "sin críticas"}
      </div>

      <div className="w-px h-6 bg-border mx-1" />

      <button className="size-9 rounded-md grid place-items-center hover:bg-muted transition-colors cursor-pointer text-muted-foreground hover:text-foreground">
        <HelpCircle className="size-[18px]" />
      </button>

      <button
        onClick={onToggleAlerts}
        title={alertsVisible ? "Ocultar alertas" : "Mostrar alertas"}
        className="size-9 rounded-md grid place-items-center hover:bg-muted transition-colors relative cursor-pointer text-muted-foreground hover:text-foreground"
      >
        <Bell className="size-[18px]" />
        {alertasCriticas > 0 && (
          <span className="absolute top-2 right-2 size-1.5 bg-destructive rounded-full ring-2 ring-card" />
        )}
      </button>
    </header>
  );
}
