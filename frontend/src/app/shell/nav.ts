export interface NavItem { to: string; label: string; activo: boolean; }
export const NAV: NavItem[] = [
  { to: "/", label: "Búsqueda 360°", activo: true },
  { to: "/ingresos/nuevo", label: "Nuevo ingreso", activo: true },
  { to: "/farmacos", label: "Fármacos", activo: false },
  { to: "/licencias", label: "Licencias", activo: false },
  { to: "/controles", label: "Controles", activo: false },
  { to: "/ept", label: "EPT", activo: false },
  { to: "/reintegro", label: "Reintegro", activo: false },
  { to: "/agenda", label: "Agendamiento", activo: false },
  { to: "/reportes", label: "Reportería", activo: false },
  { to: "/alertas", label: "Alertas", activo: false },
  { to: "/auditoria", label: "Auditoría", activo: false },
];
