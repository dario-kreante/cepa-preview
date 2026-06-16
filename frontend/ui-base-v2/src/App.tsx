import { useState } from "react"
import { Sidebar, type NavKey } from "@/components/shell/Sidebar"
import { Topbar } from "@/components/shell/Topbar"
import { AlertsPanel } from "@/components/shell/AlertsPanel"
import { Dashboard } from "@/pages/Dashboard"
import { Ingresos } from "@/pages/Ingresos"
import { PatientSheet } from "@/pages/PatientSheet"
import { Licencias, Farmacos, Controles } from "@/pages/SimplePages"
import { EPT } from "@/pages/EPT"
import { Reintegro } from "@/pages/Reintegro"
import { Auditoria } from "@/pages/Auditoria"
import { Agenda } from "@/pages/Agenda"
import { Reportes } from "@/pages/Reportes"
import { PATIENTS, type Patient } from "@/data/seed"

const TITLE_MAP: Record<NavKey, string> = {
  dashboard: "Dashboard",
  ingresos: "Pacientes",
  licencias: "Licencias médicas",
  farmacos: "Gestión de fármacos",
  controles: "Controles médicos",
  ept: "Seguimiento EPT",
  reintegro: "Seguimiento reintegro",
  auditoria: "Auditoría",
  agenda: "Agendamiento",
  reportes: "Reportería",
}

const CRUMBS_MAP: Record<NavKey, string> = {
  dashboard: "Inicio · Dashboard",
  ingresos: "Inicio · Pacientes",
  licencias: "Inicio · Clínico · Licencias médicas",
  farmacos: "Inicio · Clínico · Fármacos",
  controles: "Inicio · Clínico · Controles médicos",
  ept: "Inicio · Clínico · Seguimiento EPT",
  reintegro: "Inicio · Clínico · Reintegro laboral",
  auditoria: "Inicio · Auditoría",
  agenda: "Inicio · Operación · Agendamiento",
  reportes: "Inicio · Operación · Reportería",
}

export default function App() {
  const [current, setCurrent] = useState<NavKey>("dashboard")
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [alertsHidden, setAlertsHidden] = useState(false)
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  const openPatientByFolio = (folio: string) => {
    const p = PATIENTS.find((x) => x.folio === folio)
    if (p) {
      setSelectedPatient(p)
      setSheetOpen(true)
    }
  }
  const openPatient = (p: Patient) => {
    setSelectedPatient(p)
    setSheetOpen(true)
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background">
      <Sidebar
        current={current}
        onNav={setCurrent}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          title={TITLE_MAP[current]}
          crumbs={CRUMBS_MAP[current]}
          onToggleAlerts={() => setAlertsHidden((v) => !v)}
          alertsHidden={alertsHidden}
        />

        <main className="flex-1 overflow-y-auto bg-[oklch(0.985_0.003_195)]">
          <div className="p-6 lg:p-8 max-w-[1600px] mx-auto">
            {current === "dashboard" && <Dashboard onOpenPatient={openPatientByFolio} />}
            {current === "ingresos" && <Ingresos onOpenPatient={openPatient} />}
            {current === "licencias" && <Licencias />}
            {current === "farmacos" && <Farmacos />}
            {current === "controles" && <Controles />}
            {current === "ept" && <EPT />}
            {current === "reintegro" && <Reintegro />}
            {current === "auditoria" && <Auditoria />}
            {current === "agenda" && <Agenda />}
            {current === "reportes" && <Reportes />}
          </div>
        </main>
      </div>

      {!alertsHidden && (
        <AlertsPanel
          onItemClick={(a) => openPatientByFolio(a.folio)}
        />
      )}

      <PatientSheet patient={selectedPatient} open={sheetOpen} onOpenChange={setSheetOpen} />
    </div>
  )
}
