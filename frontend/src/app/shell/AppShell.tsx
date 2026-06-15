import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { NAV } from "./nav";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AppShell() {
  const { rol, username, logout } = useAuth();
  const escritor = puedeEscribir(rol as Rol);
  return (
    <div className="min-h-screen grid grid-cols-[240px_1fr] bg-ink-50">
      <aside className="border-r border-ink-200 bg-white p-4 space-y-1">
        <div className="px-2 py-3 text-brand-700 font-semibold">Sistema CEPA</div>
        {NAV.filter((n) => n.activo && (n.to !== "/ingresos/nuevo" || escritor)).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"}
            className={({ isActive }) => cn(
              "block rounded-md px-3 py-2 text-sm",
              isActive ? "bg-brand-50 text-brand-700 font-medium" : "text-ink-700 hover:bg-ink-100",
            )}>
            {n.label}
          </NavLink>
        ))}
        <div className="pt-2 mt-2 border-t border-ink-200 text-xs text-ink-400">Próximamente</div>
        {NAV.filter((n) => !n.activo).map((n) => (
          <span key={n.to} className="block rounded-md px-3 py-2 text-sm text-ink-300 cursor-not-allowed">{n.label}</span>
        ))}
      </aside>
      <div className="flex flex-col">
        <header className="flex items-center justify-between border-b border-ink-200 bg-white px-6 py-3">
          <Link to="/" className="text-sm text-ink-500">CEPA · UTalca</Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-ink-500">{username} · {rol}</span>
            <Button variant="outline" size="sm" onClick={logout}>Salir</Button>
          </div>
        </header>
        <main className="p-6"><Outlet /></main>
      </div>
    </div>
  );
}
