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
/** Anchos de chrome fijos. Por debajo de `xl` el panel de alertas pasa a overlay
 *  y el sidebar arranca colapsado, para no aplastar el contenido. */
function isWide(): boolean {
  return typeof window !== "undefined" ? window.innerWidth >= 1280 : true;
}
function isNarrow(): boolean {
  return typeof window !== "undefined" ? window.innerWidth < 1024 : false;
}

export function AppShell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(isNarrow);
  const [alertsVisible, setAlertsVisible] = useState(isWide);

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

      {alertsVisible && (
        <>
          {/* Backdrop solo en pantallas < xl (modo overlay) */}
          <button
            type="button"
            aria-label="Cerrar panel de alertas"
            onClick={() => setAlertsVisible(false)}
            className="xl:hidden fixed inset-0 z-30 bg-black/40"
          />
          {/* Inline (xl+) / drawer flotante a la derecha (< xl) */}
          <div className="fixed inset-y-0 right-0 z-40 shrink-0 shadow-xl xl:static xl:z-auto xl:shadow-none">
            <AlertsPanel />
          </div>
        </>
      )}
    </div>
  );
}
