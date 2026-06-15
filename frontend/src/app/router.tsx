import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { AppShell } from "./shell/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { BuscarPage } from "@/features/ingresos/BuscarPage";
import { Vista360Page } from "@/features/ingresos/Vista360Page";
import { AltaIngresoPage } from "@/features/ingresos/AltaIngresoPage";

export function ProtectedRoute({ rolesEscritura }: { rolesEscritura?: boolean }) {
  const { rol, cargando } = useAuth();
  if (cargando) return <div className="p-6 text-ink-500">Cargando…</div>;
  if (!rol) return <Navigate to="/login" replace />;
  if (rolesEscritura && !puedeEscribir(rol as Rol)) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<BuscarPage />} />
          <Route path="/pacientes/:id" element={<Vista360Page />} />
          <Route element={<ProtectedRoute rolesEscritura />}>
            <Route path="/ingresos/nuevo" element={<AltaIngresoPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
