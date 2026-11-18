/**
 * ReporteIngresosPage — QA-004. Ingresos del período, una fila por ingreso, más los
 * pacientes de SALUTEM que siguen pendientes de folio. Totales por tipo de ingreso,
 * región, programa y convenio. El período vive en la URL (?desde=…&hasta=…) para que
 * la tarjeta «Ingresos» del dashboard abra el mismo período.
 */
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useReporteIngresos } from "./hooks";

const ISO = /^\d{4}-\d{2}-\d{2}$/;

const TIPOS_INGRESO: Record<string, string> = {
  consulta_espontanea: "Consulta espontánea",
  convenio: "Convenio",
  proyecto: "Proyecto",
  particular: "Particular",
};

const etiquetaTipo = (t: string | null | undefined) =>
  t ? (TIPOS_INGRESO[t] ?? t) : "—";

function isoLocal(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function fechaCl(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}-${m}-${a}`;
}

/** Lunes de la semana actual hasta hoy. */
function estaSemana(): { fecha_desde: string; fecha_hasta: string } {
  const hoy = new Date();
  const lunes = new Date(hoy);
  lunes.setDate(hoy.getDate() - ((hoy.getDay() + 6) % 7));
  return { fecha_desde: isoLocal(lunes), fecha_hasta: isoLocal(hoy) };
}

/** Día 1 del mes actual hasta hoy. */
function esteMes(): { fecha_desde: string; fecha_hasta: string } {
  const hoy = new Date();
  return {
    fecha_desde: isoLocal(new Date(hoy.getFullYear(), hoy.getMonth(), 1)),
    fecha_hasta: isoLocal(hoy),
  };
}

function periodoDeUrl(params: URLSearchParams) {
  const desde = params.get("desde") ?? "";
  const hasta = params.get("hasta") ?? "";
  if (ISO.test(desde) && ISO.test(hasta) && desde <= hasta) {
    return { fecha_desde: desde, fecha_hasta: hasta };
  }
  return esteMes();
}

function Totales({
  titulo,
  testId,
  filas,
  formato = (e: string) => e,
}: {
  titulo: string;
  testId: string;
  filas: { etiqueta: string; total: number }[];
  formato?: (etiqueta: string) => string;
}) {
  return (
    <Card className="p-0 overflow-hidden" data-testid={testId}>
      <div className="px-4 py-3 border-b">
        <h3 className="text-[14px] font-semibold">{titulo}</h3>
      </div>
      {filas.length === 0 ? (
        <p className="text-[13px] text-muted-foreground p-4">Sin datos en el período.</p>
      ) : (
        <ul className="divide-y">
          {filas.map((f) => (
            <li key={f.etiqueta} className="flex justify-between px-4 py-2 text-[13px]">
              <span>{formato(f.etiqueta)}</span>
              <span className="font-semibold tabular-nums">{f.total}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ReporteIngresosPage() {
  const [params, setParams] = useSearchParams();
  const periodo = periodoDeUrl(params);
  const [desde, setDesde] = useState(periodo.fecha_desde);
  const [hasta, setHasta] = useState(periodo.fecha_hasta);
  const claveUrl = `${periodo.fecha_desde}..${periodo.fecha_hasta}`;
  const [claveVista, setClaveVista] = useState(claveUrl);
  if (claveVista !== claveUrl) {
    // El período cambió por la URL (atajo, atrás/adelante): sincroniza los campos.
    setClaveVista(claveUrl);
    setDesde(periodo.fecha_desde);
    setHasta(periodo.fecha_hasta);
  }
  const rangoInvalido = Boolean(desde && hasta && desde > hasta);

  const { data, isLoading, isError } = useReporteIngresos(periodo);

  const fijar = (p: { fecha_desde: string; fecha_hasta: string }) =>
    setParams({ desde: p.fecha_desde, hasta: p.fecha_hasta });
  const aplicar = () => {
    if (!desde || !hasta || rangoInvalido) return;
    setParams({ desde, hasta });
  };

  const n = (v: number | undefined) => (v == null ? "—" : v.toLocaleString("es-CL"));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Reporte de ingresos</h1>
          <p className="text-[13px] text-muted-foreground mt-1">
            Período {fechaCl(periodo.fecha_desde)} al {fechaCl(periodo.fecha_hasta)} · una fila por
            ingreso, más los pacientes de SALUTEM aún pendientes de folio
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex gap-1" role="group" aria-label="Período rápido">
            <Button size="sm" variant="outline" onClick={() => fijar(estaSemana())}>
              Esta semana
            </Button>
            <Button size="sm" variant="outline" onClick={() => fijar(esteMes())}>
              Este mes
            </Button>
          </div>
          <div className="space-y-1">
            <Label htmlFor="desde" className="text-[11px]">Desde</Label>
            <Input id="desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="h-8" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="hasta" className="text-[11px]">Hasta</Label>
            <Input id="hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="h-8" />
          </div>
          <Button size="sm" variant="outline" onClick={aplicar} disabled={!desde || !hasta || rangoInvalido} data-testid="btn-aplicar">
            Aplicar
          </Button>
        </div>
      </div>
      {rangoInvalido && (
        <p className="text-[12px] text-destructive" role="alert">
          La fecha «Desde» es posterior a «Hasta».
        </p>
      )}

      {isError && (
        <p className="text-[13px] text-destructive" role="alert">
          No se pudo cargar el reporte. Intenta nuevamente.
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="p-4">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Total del período</p>
          <p className="text-[22px] font-semibold" data-testid="total-ingresos">{n(data?.total)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Con folio</p>
          <p className="text-[22px] font-semibold" data-testid="total-con-folio">{n(data?.total_con_folio)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Pendientes de folio</p>
          <p className="text-[22px] font-semibold" data-testid="total-pendientes">{n(data?.total_pendientes)}</p>
          <Link to="/pendientes-folio" className="text-[11px] text-primary hover:underline">
            Ver pendientes de folio
          </Link>
        </Card>
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          <Totales titulo="Por tipo de ingreso" testId="totales-tipo" filas={data.por_tipo_ingreso} formato={(e) => TIPOS_INGRESO[e] ?? e} />
          <Totales titulo="Por región" testId="totales-region" filas={data.por_region} />
          <Totales titulo="Por programa" testId="totales-programa" filas={data.por_programa} />
          <Totales titulo="Por convenio" testId="totales-convenio" filas={data.por_convenio} />
        </div>
      )}

      <Card className="p-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Paciente</TableHead>
              <TableHead>RUT</TableHead>
              <TableHead>Folio</TableHead>
              <TableHead>Tipo de ingreso</TableHead>
              <TableHead>Programa</TableHead>
              <TableHead>Región</TableHead>
              <TableHead>Fecha</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">Cargando…</TableCell>
              </TableRow>
            )}
            {data && data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-6">
                  No hay ingresos en este período.
                </TableCell>
              </TableRow>
            )}
            {data?.items.map((i) => (
              <TableRow key={`${i.paciente_id}-${i.ingreso_id ?? "p"}`}>
                <TableCell className="font-medium">{i.paciente_nombre}</TableCell>
                <TableCell>{i.paciente_rut ?? "—"}</TableCell>
                <TableCell>
                  {i.pendiente ? <Badge variant="warning">Pendiente</Badge> : i.folio}
                </TableCell>
                <TableCell>{etiquetaTipo(i.tipo_ingreso)}</TableCell>
                <TableCell>{i.programa ?? "—"}</TableCell>
                <TableCell>{i.region ?? "—"}</TableCell>
                <TableCell>{fechaCl(i.fecha)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
