import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import { AppShell } from "./shell/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { IngresosListaPage } from "@/features/ingresos/IngresosListaPage";
import { AltaIngresoPage } from "@/features/ingresos/AltaIngresoPage";
import { LicenciasPage } from "@/features/licencias/LicenciasPage";
import { FarmacosPage } from "@/features/farmacos/FarmacosPage";
import { ControlesPage } from "@/features/controles/ControlesPage";
import { EptPage } from "@/features/ept/EptPage";
import { ReintegroPage } from "@/features/reintegro/ReintegroPage";
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
          <Route path="/ingresos" element={<IngresosListaPage />} />
          <Route element={<ProtectedRoute rolesEscritura />}>
            <Route path="/ingresos/nuevo" element={<AltaIngresoPage />} />
          </Route>
          <Route path="/licencias" element={<LicenciasPage />} />
          <Route path="/farmacos" element={<FarmacosPage />} />
          <Route path="/controles" element={<ControlesPage />} />
          <Route path="/ept" element={<EptPage />} />
          <Route path="/reintegro" element={<ReintegroPage />} />
          <Route path="/auditoria" element={<ProximamentePage titulo="Auditoría" />} />
          <Route path="/agenda" element={<ProximamentePage titulo="Agendamiento" />} />
          <Route path="/reportes" element={<ProximamentePage titulo="Reportería" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
