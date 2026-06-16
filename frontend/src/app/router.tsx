import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { AppShell } from "./shell/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { BuscarPage } from "@/features/ingresos/BuscarPage";
import { Vista360Page } from "@/features/ingresos/Vista360Page";
import { AltaIngresoPage } from "@/features/ingresos/AltaIngresoPage";
import { ProximamentePage } from "@/features/_placeholder/ProximamentePage";

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
          <Route path="/" element={<ProximamentePage titulo="Dashboard" />} />
          <Route path="/ingresos" element={<BuscarPage />} />
          <Route path="/pacientes/:id" element={<Vista360Page />} />
          <Route element={<ProtectedRoute rolesEscritura />}>
            <Route path="/ingresos/nuevo" element={<AltaIngresoPage />} />
          </Route>
          <Route path="/licencias" element={<ProximamentePage titulo="Licencias médicas" />} />
          <Route path="/farmacos" element={<ProximamentePage titulo="Gestión de fármacos" />} />
          <Route path="/controles" element={<ProximamentePage titulo="Controles médicos" />} />
          <Route path="/ept" element={<ProximamentePage titulo="Seguimiento EPT" />} />
          <Route path="/reintegro" element={<ProximamentePage titulo="Seguimiento reintegro" />} />
          <Route path="/auditoria" element={<ProximamentePage titulo="Auditoría" />} />
          <Route path="/agenda" element={<ProximamentePage titulo="Agendamiento" />} />
          <Route path="/reportes" element={<ProximamentePage titulo="Reportería" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
