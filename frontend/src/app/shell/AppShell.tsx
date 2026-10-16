import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { AlertsPanel, alertasSinLeer } from "@/components/shell/AlertsPanel";
import { useAlertas } from "@/features/alertas/hooks";
import { usePendientesFolio } from "@/features/pacientes-borrador/hooks";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";

/**
 * AppShell — authenticated layout.
 *
 * Rendered inside ProtectedRoute, so we can safely use useAuth() in child
 * components. Manages sidebar collapse + alerts panel visibility.
 *
 * Badge computation:
 *   - "licencias" badge = alertas pendientes cuyo tipo contiene "licencia"
 *   - "ept"       badge = alertas pendientes cuyo caso_tipo == "ept"
 *   - campana (Topbar) = alertas sin leer de quien mira (asignadas a ella o sin dueño).
 */
/** Por debajo de `lg` el sidebar arranca colapsado, para no aplastar el contenido. */
function isNarrow(): boolean {
  return typeof window !== "undefined" ? window.innerWidth < 1024 : false;
}

export function AppShell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(isNarrow);
  const [alertsVisible, setAlertsVisible] = useState(false);

  const { data: alertas = [] } = useAlertas();
  const { rol, usuarioId } = useAuth();
  // La lista de pendientes de folio es solo para quienes escriben (Auditor recibiría 403).
  const { data: pendientesFolio = [] } = usePendientesFolio(puedeEscribir(rol as Rol));

  // Compute sidebar badges from real alert data
  const pendientes = alertas.filter((a) => a.estado === "pendiente");

  const badges: Record<string, number> = {
    licencias: pendientes.filter((a) =>
      a.tipo.toLowerCase().includes("licencia"),
    ).length,
    ept: pendientes.filter(
      (a) => a.caso_tipo?.toLowerCase() === "ept",
    ).length,
    pendientes_folio: pendientesFolio.length,
  };

  // La ventana de alertas flota sobre el contenido: se cierra con Escape o al hacer clic fuera.
  useEffect(() => {
    if (!alertsVisible) return;
    const alPresionar = (e: KeyboardEvent) => e.key === "Escape" && setAlertsVisible(false);
    window.addEventListener("keydown", alPresionar);
    return () => window.removeEventListener("keydown", alPresionar);
  }, [alertsVisible]);



  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
        badges={badges}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          alertsVisible={alertsVisible}
          onToggleAlerts={() => setAlertsVisible((v) => !v)}
          alertasSinLeer={alertasSinLeer(alertas, usuarioId).length}
        />

        <main className="flex-1 overflow-y-auto bg-[oklch(0.985_0.003_195)]">
          <div className="p-6 lg:p-8 max-w-[1600px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>

      {alertsVisible && (
        <>
          {/* Capa invisible: un clic fuera de la ventana la cierra. */}
          <button
            type="button"
            aria-label="Cerrar panel de alertas"
            tabIndex={-1}
            onClick={() => setAlertsVisible(false)}
            className="fixed inset-0 z-30 cursor-default bg-transparent"
          />
          <div className="fixed top-[3.75rem] right-3 sm:right-4 z-40">
            <AlertsPanel onClose={() => setAlertsVisible(false)} />
          </div>
        </>
      )}
    </div>
  );
}
