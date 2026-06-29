import { NavLink } from "react-router-dom";
import {
  ChevronsLeft,
  Search,
  LifeBuoy,
  Settings,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { type Rol } from "@/lib/rbac";
import { APP_INITIAL, APP_NAME, APP_SUBTITLE } from "@/lib/brand";
import { NAV } from "@/app/shell/nav";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  badges?: Record<string, number>;
}

export function Sidebar({ collapsed, onToggleCollapse, badges = {} }: SidebarProps) {
  const { username, rol, logout } = useAuth();

  // Derive initials from username for avatar
  const initials = username
    ? username
        .split(/[._\s-]/)
        .slice(0, 2)
        .map((p) => p[0]?.toUpperCase() ?? "")
        .join("")
    : "?";

  return (
    <aside
      className={cn(
        "bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col transition-all duration-300 shrink-0",
        collapsed ? "w-16" : "w-[260px]",
      )}
    >
      {/* Brand */}
      <div
        className={cn(
          "flex items-center gap-2.5 px-5 pt-5 pb-4",
          collapsed && "justify-center px-2",
        )}
      >
        <div className="relative size-8 rounded-lg bg-gradient-to-br from-primary to-[oklch(0.38_0.09_195)] grid place-items-center shadow-sm shrink-0">
          <span className="text-primary-foreground font-bold text-[13px] tracking-tight">
            {APP_INITIAL}
          </span>
        </div>
        {!collapsed && (
          <div className="flex flex-col leading-tight">
            <span className="text-foreground font-bold text-[14px] tracking-tight">
              {APP_NAME}
            </span>
            <span className="text-muted-foreground text-[10.5px]">
              {APP_SUBTITLE}
            </span>
          </div>
        )}
      </div>

      {/* Search (visual only — global search not wired yet) */}
      {!collapsed && (
        <div className="px-4 pb-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 size-3.5 text-muted-foreground pointer-events-none" />
            <input
              placeholder="Buscar…"
              readOnly
              className="w-full h-8 pl-8 pr-2 text-[12.5px] bg-background border border-border rounded-md shadow-xs placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-ring cursor-not-allowed"
            />
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3">
        {NAV.map((section) => {
          // Filtra items restringidos por rol; oculta la sección si queda vacía.
          const items = section.items.filter(
            (item) => !item.roles || (rol != null && item.roles.includes(rol as Rol)),
          );
          if (items.length === 0) return null;
          return (
          <div key={section.label} className="mb-3">
            {!collapsed && (
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70 px-2 py-1.5 font-semibold">
                {section.label}
              </div>
            )}
            <div className="space-y-0.5">
              {items.map((item) => {
                const Icon = item.icon;
                const badgeCount =
                  item.badgeKey != null ? (badges[item.badgeKey] ?? 0) : 0;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      cn(
                        "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium transition-colors",
                        collapsed && "justify-center px-0",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon
                          className={cn(
                            "size-[17px] shrink-0",
                            isActive
                              ? "text-primary"
                              : "text-muted-foreground",
                          )}
                        />
                        {!collapsed && (
                          <>
                            <span className="flex-1 text-left truncate">
                              {item.label}
                            </span>
                            {badgeCount > 0 && (
                              <span className="bg-destructive/10 text-destructive text-[10px] font-semibold px-1.5 py-0.5 rounded-full min-w-4 text-center">
                                {badgeCount}
                              </span>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
          );
        })}
      </nav>

      {/* Bottom: Support + Settings */}
      <div className="px-3 pb-2 space-y-0.5">
        <button
          className={cn(
            "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors cursor-pointer",
            collapsed && "justify-center px-0",
          )}
        >
          <LifeBuoy className="size-[17px] text-muted-foreground shrink-0" />
          {!collapsed && <span>Ayuda y soporte</span>}
        </button>
        <button
          className={cn(
            "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors cursor-pointer",
            collapsed && "justify-center px-0",
          )}
        >
          <Settings className="size-[17px] text-muted-foreground shrink-0" />
          {!collapsed && <span>Configuración</span>}
        </button>
      </div>

      {/* User profile */}
      <div
        className={cn(
          "border-t border-sidebar-border flex items-center gap-2.5 px-3 py-3",
          collapsed && "justify-center",
        )}
      >
        <div className="size-9 rounded-full bg-primary grid place-items-center text-primary-foreground text-[11px] font-bold shrink-0">
          {initials}
        </div>
        {!collapsed && (
          <>
            <div className="flex-1 min-w-0 leading-tight">
              <div className="text-[12.5px] font-semibold truncate">
                {username ?? "—"}
              </div>
              <div className="text-[11px] text-muted-foreground truncate">
                {rol ?? "—"}
              </div>
            </div>
            <button
              onClick={logout}
              title="Cerrar sesión"
              className="size-7 rounded-md hover:bg-sidebar-accent grid place-items-center text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <LogOut className="size-[15px]" />
            </button>
          </>
        )}
      </div>

      {/* Collapse toggle */}
      <div className="border-t border-sidebar-border p-2">
        <button
          onClick={onToggleCollapse}
          className={cn(
            "w-full flex items-center gap-2.5 px-2 py-1.5 text-[11.5px] text-muted-foreground hover:text-foreground hover:bg-sidebar-accent rounded-md cursor-pointer",
            collapsed && "justify-center",
          )}
        >
          <ChevronsLeft
            className={cn(
              "size-4 transition-transform",
              collapsed && "rotate-180",
            )}
          />
          {!collapsed && <span>Colapsar menú</span>}
        </button>
      </div>
    </aside>
  );
}
