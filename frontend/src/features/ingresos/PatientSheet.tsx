import { Sheet, SheetContent, SheetTitle, SheetDescription } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  X,
  Phone,
  Mail,
  MapPin,
  FileText,
  Pill,
  Stethoscope,
  Edit3,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/AuthContext";
import { puedeEscribir, type Rol } from "@/lib/rbac";
import {
  useVista360,
  useLicenciasPorIngreso,
  useControlesPorIngreso,
  useRecetasPorIngreso,
} from "./hooks";
import type { LicenciaRead, ControlMedicoRead, RecetaRead } from "./api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getInitials(nombre: string): string {
  const parts = nombre.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return nombre.trim().charAt(0).toUpperCase();
}

function formatDate(d: string | null | undefined): string {
  if (!d) return "—";
  // ISO date (YYYY-MM-DD) → DD/MM/YYYY
  const [y, m, day] = d.split("-");
  if (!y || !m || !day) return d;
  return `${day}/${m}/${y}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function InfoCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | null | undefined;
}) {
  return (
    <Card>
      <CardContent className="p-3.5 flex items-center gap-3">
        <div className="size-9 rounded-md bg-muted grid place-items-center text-muted-foreground shrink-0">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
          <div className="text-[12.5px] font-semibold truncate">{value ?? "—"}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: number;
  sub: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          {label}
        </div>
        <div className="text-2xl font-bold mt-1 tracking-tight">{value}</div>
        <div className="text-[11px] text-muted-foreground">{sub}</div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ icon, msg }: { icon: React.ReactNode; msg: string }) {
  return (
    <div className={cn("text-center py-12 text-muted-foreground")}>
      <div className="size-12 rounded-full bg-muted grid place-items-center mx-auto mb-3 [&_svg]:size-5">
        {icon}
      </div>
      <div className="text-[13px]">{msg}</div>
    </div>
  );
}

function TabLoading() {
  return (
    <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
      <Loader2 className="size-4 animate-spin" />
      <span className="text-[13px]">Cargando…</span>
    </div>
  );
}

function TabError({ msg }: { msg: string }) {
  return (
    <div className="text-center py-8 text-[13px] text-destructive">{msg}</div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Licencias
// ---------------------------------------------------------------------------

function LicenciasTab({ licencias }: { licencias: LicenciaRead[] }) {
  if (licencias.length === 0) {
    return <EmptyState icon={<FileText />} msg="Sin licencias registradas" />;
  }
  return (
    <div className="space-y-2">
      {licencias.map((l) => (
        <Card key={l.id}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="size-10 rounded-md bg-[oklch(0.96_0.08_85)] text-[oklch(0.52_0.16_75)] grid place-items-center shrink-0">
              <FileText className="size-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[13px]">
                {l.folio_lm ? `Folio ${l.folio_lm}` : "Sin folio"} · Tipo {l.tipo_lm}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {formatDate(l.fecha_inicio)} → {formatDate(l.fecha_termino)} · {l.cantidad_dias} días
                {l.diagnostico ? ` · ${l.diagnostico}` : ""}
              </div>
            </div>
            <Badge variant={l.anulada ? "destructive" : "success"}>
              {l.anulada ? "Anulada" : "Vigente"}
            </Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Fármacos (recetas)
// ---------------------------------------------------------------------------

function FarmacosTab({ recetas }: { recetas: RecetaRead[] }) {
  if (recetas.length === 0) {
    return <EmptyState icon={<Pill />} msg="Sin recetas registradas" />;
  }
  return (
    <div className="space-y-2">
      {recetas.map((r) => (
        <Card key={r.id}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="size-10 rounded-md bg-[oklch(0.95_0.05_290)] text-[oklch(0.42_0.16_290)] grid place-items-center shrink-0">
              <Pill className="size-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[13px]">{r.marca_medicamento}</div>
              <div className="text-[11px] text-muted-foreground">
                Emisión: {formatDate(r.fecha_emision)} · Revisión: {formatDate(r.fecha_revision)}
                {r.fecha_envio ? ` · Envío: ${formatDate(r.fecha_envio)}` : ""}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Controles médicos
// ---------------------------------------------------------------------------

function ControlesTab({ controles }: { controles: ControlMedicoRead[] }) {
  if (controles.length === 0) {
    return <EmptyState icon={<Stethoscope />} msg="Sin controles registrados" />;
  }
  return (
    <div className="space-y-2">
      {controles.map((c) => (
        <Card key={c.id}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="size-10 rounded-md bg-[oklch(0.94_0.05_155)] text-[oklch(0.40_0.12_155)] grid place-items-center shrink-0">
              <Stethoscope className="size-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[13px]">
                Semana {c.semana_control} · {c.medico_tratante}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {formatDate(c.fecha_control)} · {c.region_derivacion}
                {c.proximo_control ? ` · Próximo: ${formatDate(c.proximo_control)}` : ""}
              </div>
            </div>
            {c.observaciones && (
              <span className="text-[11px] text-muted-foreground truncate max-w-[120px]">
                {c.observaciones}
              </span>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export interface PatientSheetProps {
  pacienteId: number | null;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}

export function PatientSheet({ pacienteId, open, onOpenChange }: PatientSheetProps) {
  const { rol } = useAuth();
  const canWrite = puedeEscribir(rol as Rol);

  const {
    data: vista,
    isLoading: vistaLoading,
    isError: vistaError,
  } = useVista360(pacienteId);

  // Primary ingreso = first in list (most recently created / most relevant)
  const primaryIngreso = vista?.ingresos?.[0];
  const primaryIngresoId = primaryIngreso?.id;

  const { data: licencias = [], isLoading: licLoading, isError: licError } =
    useLicenciasPorIngreso(primaryIngresoId);
  const { data: controles = [], isLoading: ctrlLoading, isError: ctrlError } =
    useControlesPorIngreso(primaryIngresoId);
  const { data: recetas = [], isLoading: recLoading, isError: recError } =
    useRecetasPorIngreso(primaryIngresoId);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="p-0 flex flex-col">
        {/* ---------------------------------------------------------------- */}
        {/* Header                                                           */}
        {/* ---------------------------------------------------------------- */}
        <div className="px-6 py-5 bg-gradient-to-br from-brand-900 to-primary/90 text-white relative shrink-0">
          <button
            onClick={() => onOpenChange(false)}
            aria-label="Cerrar"
            className="absolute right-4 top-4 size-8 rounded-md hover:bg-white/20 grid place-items-center transition-colors cursor-pointer"
          >
            <X className="size-4" />
          </button>

          <SheetTitle asChild>
            <div>
              {vistaLoading && (
                <div className="flex items-center gap-3 text-white/70">
                  <Loader2 className="size-5 animate-spin" />
                  <span className="text-sm">Cargando ficha…</span>
                </div>
              )}
              {vistaError && (
                <p className="text-sm text-red-200">No se pudo cargar el paciente.</p>
              )}
              {vista && (
                <div className="flex items-start gap-4">
                  <div className="size-14 rounded-full bg-white/15 backdrop-blur grid place-items-center text-lg font-bold border border-white/20 shrink-0">
                    {getInitials(vista.paciente.nombre)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-xl font-bold leading-tight">{vista.paciente.nombre}</h2>
                    <div className="text-sm text-white/80 mt-0.5 font-mono">
                      {vista.paciente.rut}
                      {vista.paciente.region ? ` · ${vista.paciente.region}` : ""}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mt-3">
                      {primaryIngreso && (
                        <Badge
                          variant="outline"
                          className="bg-white/15 text-white border-white/20"
                        >
                          {primaryIngreso.estado}
                        </Badge>
                      )}
                      {primaryIngreso && (
                        <Badge
                          variant="outline"
                          className="bg-white/15 text-white border-white/20"
                        >
                          {primaryIngreso.tipo_derivacion}
                        </Badge>
                      )}
                      <Badge
                        variant="outline"
                        className="bg-white/15 text-white border-white/20"
                      >
                        {vista.paciente.edad} años · {vista.paciente.sexo}
                      </Badge>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </SheetTitle>
          <SheetDescription className="sr-only">
            Ficha del paciente: datos, ingresos, licencias y seguimiento.
          </SheetDescription>

          {/* Action buttons — only for writers */}
          {canWrite && vista && (
            <div className="flex items-center gap-2 mt-5">
              <Button
                variant="secondary"
                size="sm"
                className="bg-white text-primary hover:bg-white/90"
                disabled
              >
                <Edit3 className="size-3.5" /> Editar ficha
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="bg-transparent border-white/30 text-white hover:bg-white/10"
                disabled
              >
                <FileText className="size-3.5" /> Nueva licencia
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="bg-transparent border-white/30 text-white hover:bg-white/10"
                disabled
              >
                <Stethoscope className="size-3.5" /> Agendar control
              </Button>
            </div>
          )}
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Body                                                             */}
        {/* ---------------------------------------------------------------- */}
        <div className="flex-1 overflow-y-auto">
          {vista && (
            <Tabs defaultValue="resumen">
              <div className="border-b sticky top-0 bg-card z-10 px-6">
                <TabsList className="bg-transparent p-0 h-auto rounded-none gap-1">
                  {[
                    { v: "resumen", l: "Resumen" },
                    { v: "licencias", l: `Licencias (${licencias.length})` },
                    { v: "farmacos", l: `Fármacos (${recetas.length})` },
                    { v: "controles", l: `Controles (${controles.length})` },
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
                {/* -------- Resumen -------- */}
                <TabsContent value="resumen" className="mt-0 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <InfoCard
                      icon={<Phone className="size-4" />}
                      label="Teléfono"
                      value={vista.paciente.telefono}
                    />
                    <InfoCard
                      icon={<Mail className="size-4" />}
                      label="Correo"
                      value={vista.paciente.correo}
                    />
                    <InfoCard
                      icon={<MapPin className="size-4" />}
                      label="Región"
                      value={vista.paciente.region}
                    />
                    <InfoCard
                      icon={<MapPin className="size-4" />}
                      label="Comuna"
                      value={vista.paciente.comuna}
                    />
                  </div>

                  {primaryIngreso && (
                    <Card>
                      <CardContent className="p-4">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
                          Diagnóstico principal
                        </div>
                        <div className="text-[14px] font-semibold">
                          {primaryIngreso.diagnostico}
                        </div>
                        <div className="text-[12px] text-muted-foreground mt-1">
                          {primaryIngreso.estado} · Ingreso {formatDate(primaryIngreso.fecha_ingreso)}
                          {primaryIngreso.folio ? ` · Folio ${primaryIngreso.folio}` : ""}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {vista.ingresos.length > 1 && (
                    <Card>
                      <CardContent className="p-4">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
                          Ingresos ({vista.ingresos.length})
                        </div>
                        <ul className="space-y-1">
                          {vista.ingresos.map((ing) => (
                            <li
                              key={ing.id}
                              className="text-[12px] flex justify-between"
                            >
                              <span>Folio {ing.folio}</span>
                              <span className="text-muted-foreground">
                                {ing.estado} · {formatDate(ing.fecha_ingreso)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  <div className="grid grid-cols-3 gap-3">
                    <StatCard
                      label="Licencias"
                      value={licencias.length}
                      sub={`${licencias.filter((l) => !l.anulada).length} vigentes`}
                    />
                    <StatCard
                      label="Recetas"
                      value={recetas.length}
                      sub="totales"
                    />
                    <StatCard
                      label="Controles"
                      value={controles.length}
                      sub="registrados"
                    />
                  </div>
                </TabsContent>

                {/* -------- Licencias -------- */}
                <TabsContent value="licencias" className="mt-0">
                  {licLoading ? (
                    <TabLoading />
                  ) : licError ? (
                    <TabError msg="No se pudieron cargar las licencias." />
                  ) : (
                    <LicenciasTab licencias={licencias} />
                  )}
                </TabsContent>

                {/* -------- Fármacos -------- */}
                <TabsContent value="farmacos" className="mt-0">
                  {recLoading ? (
                    <TabLoading />
                  ) : recError ? (
                    <TabError msg="No se pudieron cargar las recetas." />
                  ) : (
                    <FarmacosTab recetas={recetas} />
                  )}
                </TabsContent>

                {/* -------- Controles -------- */}
                <TabsContent value="controles" className="mt-0">
                  {ctrlLoading ? (
                    <TabLoading />
                  ) : ctrlError ? (
                    <TabError msg="No se pudieron cargar los controles." />
                  ) : (
                    <ControlesTab controles={controles} />
                  )}
                </TabsContent>

                {/* -------- Observaciones -------- */}
                <TabsContent value="obs" className="mt-0">
                  <Card>
                    <CardContent className="p-6 text-[13px] text-muted-foreground leading-relaxed">
                      <p className="text-center py-4">Sin observaciones registradas.</p>
                      <p className="text-[11px] text-muted-foreground pt-3 border-t text-center">
                        Módulo de observaciones clínicas — pendiente (ciclo futuro)
                      </p>
                    </CardContent>
                  </Card>
                </TabsContent>
              </div>
            </Tabs>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
