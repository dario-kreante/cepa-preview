/**
 * DashboardPage — CEPA-090: dashboard multiprograma con filtros (EPIC-09).
 *
 * Indicadores en tiempo real (ingresos, atenciones, inasistencias, anulaciones,
 * agendadas) + carga por profesional y cumplimiento por convenio. Solo lectura,
 * accesible a todos los roles.
 */
import { useState } from "react";
import {
  Users,
  CheckCircle2,
  UserX,
  Ban,
  CalendarClock,
  Filter,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDashboard } from "./hooks";
import type { DashboardFiltros } from "./api";

interface CargaRow {
  profesional_id: number | null;
  total_ingresos: number;
}
interface ConvenioRow {
  tipo_convenio: string | null;
  total_realizadas: number;
}

interface KpiDef {
  key: keyof KpiValues;
  label: string;
  icon: typeof Users;
  tone: string;
}
interface KpiValues {
  total_ingresos: number;
  total_atenciones: number;
  total_inasistencias: number;
  total_anulaciones: number;
  total_citas_agendadas: number;
}

const KPIS: KpiDef[] = [
  { key: "total_ingresos", label: "Ingresos", icon: Users, tone: "text-[oklch(0.45_0.13_250)]" },
  { key: "total_atenciones", label: "Atenciones", icon: CheckCircle2, tone: "text-[oklch(0.5_0.13_150)]" },
  { key: "total_inasistencias", label: "Inasistencias", icon: UserX, tone: "text-[oklch(0.55_0.15_60)]" },
  { key: "total_anulaciones", label: "Anulaciones", icon: Ban, tone: "text-destructive" },
  { key: "total_citas_agendadas", label: "Agendadas", icon: CalendarClock, tone: "text-[oklch(0.45_0.13_250)]" },
];

function KpiCard({ label, value, icon: Icon, tone }: { label: string; value: number; icon: typeof Users; tone: string }) {
  return (
    <Card className="p-4 flex items-center gap-3">
      <div className={`shrink-0 ${tone}`}>
        <Icon className="size-6" />
      </div>
      <div>
        <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
          {label}
        </p>
        <p className="text-[22px] font-semibold leading-tight" data-testid={`kpi-${label}`}>
          {value}
        </p>
      </div>
    </Card>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-2.5 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

export function DashboardPage() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [filtros, setFiltros] = useState<DashboardFiltros>({});

  const { data, isLoading, isError, error } = useDashboard(filtros);

  function aplicar() {
    setFiltros({
      fecha_desde: desde || undefined,
      fecha_hasta: hasta || undefined,
    });
  }

  const kpis: KpiValues = {
    total_ingresos: data?.total_ingresos ?? 0,
    total_atenciones: data?.total_atenciones ?? 0,
    total_inasistencias: data?.total_inasistencias ?? 0,
    total_anulaciones: data?.total_anulaciones ?? 0,
    total_citas_agendadas: data?.total_citas_agendadas ?? 0,
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Dashboard</h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Indicadores multiprograma en tiempo real
        </p>
      </div>

      {/* Filtros de período */}
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <Filter className="size-4 text-muted-foreground mb-2" />
          <div>
            <Label htmlFor="desde">Desde</Label>
            <Input
              id="desde"
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <Label htmlFor="hasta">Hasta</Label>
            <Input
              id="hasta"
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              className="h-9"
            />
          </div>
          <Button size="sm" onClick={aplicar} data-testid="btn-aplicar">
            Aplicar
          </Button>
        </div>
      </Card>

      {isError && (
        <p className="text-[13px] text-destructive px-1">
          {error instanceof Error ? error.message : "Error al cargar"}
        </p>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {KPIS.map((k) => (
          <KpiCard
            key={k.key}
            label={k.label}
            value={kpis[k.key]}
            icon={k.icon}
            tone={k.tone}
          />
        ))}
      </div>

      {isLoading && (
        <p className="text-[13px] text-muted-foreground px-1">Cargando…</p>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {/* Carga por profesional */}
        <Card className="p-0 overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h3 className="text-[14px] font-semibold">Carga por profesional</h3>
          </div>
          {data && data.carga_por_profesional.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Profesional</Th>
                  <Th>Ingresos</Th>
                </tr>
              </thead>
              <tbody>
                {(data.carga_por_profesional as unknown as CargaRow[]).map((row, i) => (
                  <tr key={i} className="border-b">
                    <td className="px-4 py-2.5 text-[13px]">
                      {row.profesional_id != null
                        ? `N° ${row.profesional_id}`
                        : "Sin asignar"}
                    </td>
                    <td className="px-4 py-2.5 text-[13px] font-semibold">
                      {row.total_ingresos}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-[13px] text-muted-foreground px-4 py-6">
              Sin datos de carga para el período.
            </p>
          )}
        </Card>

        {/* Cumplimiento convenios */}
        <Card className="p-0 overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h3 className="text-[14px] font-semibold">
              Cumplimiento por convenio
            </h3>
          </div>
          {data && data.cumplimiento_convenios.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Convenio</Th>
                  <Th>Atenciones</Th>
                </tr>
              </thead>
              <tbody>
                {(data.cumplimiento_convenios as unknown as ConvenioRow[]).map((row, i) => (
                  <tr key={i} className="border-b">
                    <td className="px-4 py-2.5 text-[13px]">
                      {row.tipo_convenio ?? "Sin convenio"}
                    </td>
                    <td className="px-4 py-2.5 text-[13px] font-semibold">
                      {row.total_realizadas}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-[13px] text-muted-foreground px-4 py-6">
              Sin atenciones por convenio para el período.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
