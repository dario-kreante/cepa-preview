import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { AlertsPanel } from "@/components/shell/AlertsPanel";
import { useAlertas } from "@/features/alertas/hooks";

/**
 * AppShell — authenticated layout.
 *
 * Rendered inside ProtectedRoute, so we can safely use useAuth() in child
 * components. Manages sidebar collapse + alerts panel visibility.
 *
 * Badge computation:
 *   - "licencias" badge = alertas pendientes cuyo tipo contiene "licencia"
 *   - "ept"       badge = alertas pendientes cuyo caso_tipo == "ept"
 *   - críticas count    = alertas with estado == "pendiente"
 */
export function AppShell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [alertsVisible, setAlertsVisible] = useState(true);

  const { data: alertas = [] } = useAlertas();

  // Compute sidebar badges from real alert data
  const pendientes = alertas.filter((a) => a.estado === "pendiente");

  const badges: Record<string, number> = {
    licencias: pendientes.filter((a) =>
      a.tipo.toLowerCase().includes("licencia"),
    ).length,
    ept: pendientes.filter(
      (a) => a.caso_tipo?.toLowerCase() === "ept",
    ).length,
  };

  // Critical count for Topbar pill
  const alertasCriticas = pendientes.length;

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
          alertasCriticas={alertasCriticas}
        />

        <main className="flex-1 overflow-y-auto bg-[oklch(0.985_0.003_195)]">
          <div className="p-6 lg:p-8 max-w-[1600px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>

      {alertsVisible && <AlertsPanel />}
    </div>
  );
}
