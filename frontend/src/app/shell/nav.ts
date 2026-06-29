import {
  LayoutDashboard,
  Users,
  FileText,
  Pill,
  Stethoscope,
  Briefcase,
  RefreshCw,
  ShieldCheck,
  Calendar,
  BarChart3,
  UserCog,
  type LucideIcon,
} from "lucide-react";
import type { Rol } from "@/lib/rbac";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badgeKey?: string;
  /** Si se define, el item solo se muestra a estos roles. */
  roles?: Rol[];
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export const NAV: NavSection[] = [
  {
    label: "General",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Módulos clínicos",
    items: [
      { to: "/ingresos", label: "Ingresos y pacientes", icon: Users },
      {
        to: "/licencias",
        label: "Licencias médicas",
        icon: FileText,
        badgeKey: "licencias",
      },
      { to: "/farmacos", label: "Gestión de fármacos", icon: Pill },
      { to: "/controles", label: "Controles médicos", icon: Stethoscope },
      {
        to: "/ept",
        label: "Seguimiento EPT",
        icon: Briefcase,
        badgeKey: "ept",
      },
      { to: "/reintegro", label: "Seguimiento reintegro", icon: RefreshCw },
      { to: "/auditoria", label: "Auditoría", icon: ShieldCheck },
    ],
  },
  {
    label: "Operación",
    items: [
      { to: "/agenda", label: "Agendamiento", icon: Calendar },
      { to: "/reportes", label: "Reportería", icon: BarChart3 },
    ],
  },
  {
    label: "Administración",
    items: [
      {
        to: "/usuarios",
        label: "Usuarios y roles",
        icon: UserCog,
        roles: ["Coordinacion"],
      },
    ],
  },
];

/** Pathname → title mapping for Topbar */
export const TITLE_MAP: Record<string, string> = {
  "/": "Dashboard",
  "/ingresos": "Pacientes",
  "/ingresos/nuevo": "Nuevo ingreso",
  "/licencias": "Licencias médicas",
  "/farmacos": "Gestión de fármacos",
  "/controles": "Controles médicos",
  "/ept": "Seguimiento EPT",
  "/reintegro": "Seguimiento reintegro",
  "/auditoria": "Auditoría",
  "/agenda": "Agendamiento",
  "/reportes": "Reportería",
  "/usuarios": "Usuarios y roles",
};

/** Pathname → breadcrumb string mapping */
export const CRUMBS_MAP: Record<string, string> = {
  "/": "Inicio · Dashboard",
  "/ingresos": "Inicio · Pacientes",
  "/ingresos/nuevo": "Inicio · Pacientes · Nuevo ingreso",
  "/licencias": "Inicio · Clínico · Licencias médicas",
  "/farmacos": "Inicio · Clínico · Fármacos",
  "/controles": "Inicio · Clínico · Controles médicos",
  "/ept": "Inicio · Clínico · Seguimiento EPT",
  "/reintegro": "Inicio · Clínico · Reintegro laboral",
  "/auditoria": "Inicio · Auditoría",
  "/agenda": "Inicio · Operación · Agendamiento",
  "/reportes": "Inicio · Operación · Reportería",
  "/usuarios": "Inicio · Administración · Usuarios y roles",
};
