import { Sheet, SheetContent, SheetTitle } from "@/components/ui/dialog"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { LICENCIAS, RECETAS, CONTROLES, type Patient } from "@/data/seed"
import { X, Phone, Mail, Building2, FileText, Pill, Stethoscope, Edit3, MoreHorizontal } from "lucide-react"
import { cn } from "@/lib/utils"

export function PatientSheet({
  patient, open, onOpenChange,
}: {
  patient: Patient | null
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  if (!patient) return null
  const lic = LICENCIAS.filter((l) => l.folio === patient.folio)
  const rec = RECETAS.filter((r) => r.folio === patient.folio)
  const ctrl = CONTROLES.filter((c) => c.folio === patient.folio)
  const totalDiasLic = lic.reduce((s, l) => s + l.dias, 0)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="p-0 !w-[720px] !max-w-[95vw]">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-br from-brand-900 to-primary/90 text-white relative shrink-0">
          <button
            onClick={() => onOpenChange(false)}
            className="absolute right-4 top-4 size-8 rounded-md hover:bg-white/20 grid place-items-center transition-colors cursor-pointer"
          >
            <X className="size-4" />
          </button>
          <SheetTitle asChild>
            <div>
              <div className="flex items-start gap-4">
                <div className="size-14 rounded-full bg-white/15 backdrop-blur grid place-items-center text-lg font-bold border border-white/20">
                  {patient.inicial}
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-xl font-bold leading-tight">{patient.nombre}</h2>
                  <div className="text-sm text-white/80 mt-0.5">
                    Folio {patient.folio} · {patient.rut} · {patient.region}
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <Badge variant="outline" className="bg-white/15 text-white border-white/20">
                      {patient.estado}
                    </Badge>
                    <Badge variant="outline" className="bg-white/15 text-white border-white/20">
                      {patient.tipoDerivacion}
                    </Badge>
                    <Badge variant="outline" className="bg-white/15 text-white border-white/20">
                      {patient.edad} años · {patient.genero}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </SheetTitle>

          <div className="flex items-center gap-2 mt-5">
            <Button variant="secondary" size="sm" className="bg-white text-primary hover:bg-white/90">
              <Edit3 /> Editar ficha
            </Button>
            <Button variant="outline" size="sm" className="bg-transparent border-white/30 text-white hover:bg-white/10">
              <FileText /> Nueva licencia
            </Button>
            <Button variant="outline" size="sm" className="bg-transparent border-white/30 text-white hover:bg-white/10">
              <Stethoscope /> Agendar control
            </Button>
            <Button variant="outline" size="icon-sm" className="bg-transparent border-white/30 text-white hover:bg-white/10 ml-auto">
              <MoreHorizontal />
            </Button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          <Tabs defaultValue="resumen">
            <div className="border-b sticky top-0 bg-card z-10 px-6">
              <TabsList className="bg-transparent p-0 h-auto rounded-none gap-1">
                {[
                  { v: "resumen", l: "Resumen" },
                  { v: "licencias", l: `Licencias (${lic.length})` },
                  { v: "farmacos", l: `Fármacos (${rec.length})` },
                  { v: "controles", l: `Controles (${ctrl.length})` },
                  { v: "obs", l: "Observaciones" },
                ].map((t) => (
                  <TabsTrigger
                    key={t.v}
                    value={t.v}
                    className="text-[13px] rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent px-3 py-3 data-[state=active]:text-primary"
                  >
                    {t.l}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>

            <div className="p-6">
              <TabsContent value="resumen" className="mt-0 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <InfoCard icon={<Phone className="size-4" />} label="Teléfono" value={patient.telefono} />
                  <InfoCard icon={<Mail className="size-4" />} label="Email" value={patient.email} />
                  <InfoCard icon={<Building2 className="size-4" />} label="Empresa" value={patient.empresa} />
                  <InfoCard icon={<Stethoscope className="size-4" />} label="Profesional a cargo" value={patient.profesionalRef} />
                </div>

                <Card>
                  <CardContent className="p-4">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
                      Diagnóstico principal
                    </div>
                    <div className="text-[14px] font-semibold">{patient.diagnostico}</div>
                    <div className="text-[12px] text-muted-foreground mt-1">
                      Confirmado · Ingreso {patient.fechaIngreso}
                    </div>
                  </CardContent>
                </Card>

                <div className="grid grid-cols-3 gap-3">
                  <StatCard label="Licencias emitidas" value={lic.length} sub={`${totalDiasLic} días total`} />
                  <StatCard label="Recetas activas" value={rec.filter(r => r.estado === "Vigente").length} sub={`${rec.length} totales`} />
                  <StatCard label="Controles" value={ctrl.length} sub={`${ctrl.filter(c => c.estado === "Realizado").length} realizados`} />
                </div>
              </TabsContent>

              <TabsContent value="licencias" className="mt-0 space-y-2">
                {lic.length === 0 ? (
                  <EmptyState icon={<FileText />} msg="Sin licencias registradas" />
                ) : (
                  lic.map((l) => (
                    <Card key={l.numero}>
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className="size-10 rounded-md bg-[oklch(0.96_0.08_85)] text-[oklch(0.52_0.16_75)] grid place-items-center">
                          <FileText className="size-5" />
                        </div>
                        <div className="flex-1">
                          <div className="font-semibold text-[13px]">{l.numero} · {l.tipoLicencia}</div>
                          <div className="text-[11px] text-muted-foreground">
                            {l.inicio} → {l.fin} · {l.dias} días · {l.medico}
                          </div>
                        </div>
                        <Badge variant={l.estado === "Vigente" ? "success" : l.estado === "Rechazada" ? "destructive" : "neutral"}>
                          {l.estado}
                        </Badge>
                      </CardContent>
                    </Card>
                  ))
                )}
              </TabsContent>

              <TabsContent value="farmacos" className="mt-0 space-y-2">
                {rec.length === 0 ? (
                  <EmptyState icon={<Pill />} msg="Sin recetas registradas" />
                ) : (
                  rec.map((r, i) => (
                    <Card key={i}>
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className="size-10 rounded-md bg-[oklch(0.95_0.05_290)] text-[oklch(0.42_0.16_290)] grid place-items-center">
                          <Pill className="size-5" />
                        </div>
                        <div className="flex-1">
                          <div className="font-semibold text-[13px]">{r.farmaco}</div>
                          <div className="text-[11px] text-muted-foreground">
                            {r.dosis} · desde {r.inicio} · vence {r.vigenciaHasta}
                          </div>
                        </div>
                        <Badge variant={r.estado === "Vigente" ? "success" : r.estado === "Por vencer" ? "warning" : "destructive"}>
                          {r.estado}
                        </Badge>
                      </CardContent>
                    </Card>
                  ))
                )}
              </TabsContent>

              <TabsContent value="controles" className="mt-0 space-y-2">
                {ctrl.length === 0 ? (
                  <EmptyState icon={<Stethoscope />} msg="Sin controles registrados" />
                ) : (
                  ctrl.map((c, i) => (
                    <Card key={i}>
                      <CardContent className="p-4 flex items-center gap-4">
                        <div className="size-10 rounded-md bg-[oklch(0.94_0.05_155)] text-[oklch(0.40_0.12_155)] grid place-items-center">
                          <Stethoscope className="size-5" />
                        </div>
                        <div className="flex-1">
                          <div className="font-semibold text-[13px]">{c.tipo}</div>
                          <div className="text-[11px] text-muted-foreground">
                            {c.fecha} {c.hora} · {c.profesional}
                          </div>
                        </div>
                        <Badge variant={c.estado === "Realizado" ? "success" : c.estado === "No asistió" ? "destructive" : c.estado === "Reagendado" ? "warning" : "info"}>
                          {c.estado}
                        </Badge>
                      </CardContent>
                    </Card>
                  ))
                )}
              </TabsContent>

              <TabsContent value="obs" className="mt-0">
                <Card>
                  <CardContent className="p-6 text-[13px] text-muted-foreground leading-relaxed">
                    <p className="mb-3">
                      <span className="font-semibold text-foreground">Última observación clínica — {patient.profesionalRef}</span>
                    </p>
                    <p className="mb-3">
                      Paciente presenta evolución favorable tras 6 sesiones psicoterapéuticas. Refiere disminución
                      significativa de síntomas ansiosos y mejoría en patrón de sueño. Se mantiene esquema farmacológico
                      y se reagenda control en 3 semanas.
                    </p>
                    <p className="text-[11px] text-muted-foreground pt-3 border-t">
                      Registrado hace 2 días · Confidencial
                    </p>
                  </CardContent>
                </Card>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-3.5 flex items-center gap-3">
        <div className="size-9 rounded-md bg-muted grid place-items-center text-muted-foreground shrink-0">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground">{label}</div>
          <div className="text-[12.5px] font-semibold truncate">{value}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function StatCard({ label, value, sub }: { label: string; value: number; sub: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">{label}</div>
        <div className="text-2xl font-bold mt-1 tracking-tight">{value}</div>
        <div className="text-[11px] text-muted-foreground">{sub}</div>
      </CardContent>
    </Card>
  )
}

function EmptyState({ icon, msg }: { icon: React.ReactNode; msg: string }) {
  return (
    <div className={cn("text-center py-12 text-muted-foreground")}>
      <div className="size-12 rounded-full bg-muted grid place-items-center mx-auto mb-3 [&_svg]:size-5">
        {icon}
      </div>
      <div className="text-[13px]">{msg}</div>
    </div>
  )
}
