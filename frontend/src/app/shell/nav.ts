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
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badgeKey?: string;
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
};
