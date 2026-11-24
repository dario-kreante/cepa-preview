/**
 * Pestaña «Ambulatorio» de Reportería (QA del 23-11-2026): atenciones realizadas en el
 * formato de la plataforma ISL, con región, código región, comuna y código comuna.
 * Filtros: período (obligatorio), programa y región. Descarga en Excel con los mismos filtros.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { REGIONES_CHILE } from "@/lib/regiones";
import { cn, fmtDate } from "@/lib/utils";
import type { FiltroAmbulatorio, ProgramaFiltro } from "./api";
import { useDescargarAmbulatorioExcel, useReporteAmbulatorio } from "./hooks";

const SELECT_CLS =
  "h-9 pl-3 pr-8 text-[12.5px] border rounded-md bg-card hover:bg-muted/30 cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring font-medium";
const SIN_DATO = "—";

const PROGRAMAS: [ProgramaFiltro | "", string][] = [
  ["", "Todos"],
  ["regular", "Regular"],
  ["ingreso_isl", "Ingreso ISL"],
  ["tratamiento_isl", "Tratamiento ISL"],
  ["ley_karin", "Ley Karin"],
  ["pipt", "PIPT"],
];

const COLUMNAS = [
  "Región",
  "Cód. región",
  "Comuna",
  "Cód. comuna",
  "N° cuenta",
  "OPA",
  "ODA",
  "RUT",
  "Nombre",
  "Cant.",
  "Cód. prestación",
  "Glosa prestación",
  "Fecha",
  "Hora",
  "Monto total",
  "Folio",
  "Programa",
];

const v = (x: string | number | null | undefined) => (x == null || x === "" ? SIN_DATO : x);

export function AmbulatorioTab() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [programa, setPrograma] = useState<ProgramaFiltro | "">("");
  const [region, setRegion] = useState("");
  const m = useReporteAmbulatorio();
  const excel = useDescargarAmbulatorioExcel();

  const filtro = (): FiltroAmbulatorio => ({
    fecha_desde: desde,
    fecha_hasta: hasta,
    programa: programa || undefined,
    region: region || undefined,
  });
  const rangoInvalido = !!desde && !!hasta && desde > hasta;

  async function consultar() {
    try {
      await m.mutateAsync(filtro());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  async function descargar() {
    try {
      await excel.mutateAsync(filtro());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    }
  }

  const listo = !!desde && !!hasta && !rangoInvalido;
  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="amb-desde">Desde *</Label>
            <Input
              id="amb-desde"
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <Label htmlFor="amb-hasta">Hasta *</Label>
            <Input
              id="amb-hasta"
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <Label htmlFor="amb-programa">Programa</Label>
            <select
              id="amb-programa"
              value={programa}
              onChange={(e) => setPrograma(e.target.value as ProgramaFiltro | "")}
              className={cn(SELECT_CLS, "block")}
            >
              {PROGRAMAS.map(([valor, texto]) => (
                <option key={valor} value={valor}>
                  {texto}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="amb-region">Región</Label>
            <select
              id="amb-region"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className={cn(SELECT_CLS, "block")}
            >
              <option value="">Todas</option>
              {REGIONES_CHILE.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <Button
            size="sm"
            onClick={consultar}
            disabled={m.isPending || !listo}
            data-testid="btn-generar-reporte"
          >
            <FileText className="size-3.5" />
            {m.isPending ? "Generando…" : "Generar"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={descargar}
            disabled={excel.isPending || !listo}
            data-testid="btn-excel-ambulatorio"
          >
            <Download className="size-3.5" />
            {excel.isPending ? "Descargando…" : "Descargar Excel"}
          </Button>
        </div>
        {rangoInvalido && (
          <p className="mt-2 text-[12px] text-destructive">
            La fecha desde no puede ser posterior a la fecha hasta.
          </p>
        )}
        <p className="mt-2 max-w-3xl text-[12px] text-muted-foreground">
          Una fila por atención realizada, con las columnas de la plataforma ISL. La ODA/OPA es la
          orden registrada en SIGE que cubre la fecha; el código y la glosa son las prestaciones de
          la cita en SALUTEM (o la especialidad si no las trae). SIGE no guarda el N° de cuenta ni
          los montos: esas columnas quedan vacías.
        </p>
      </Card>

      {m.data &&
        (m.data.items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
            <p className="text-[13.5px] text-muted-foreground">
              Sin atenciones realizadas en el período.
            </p>
          </div>
        ) : (
          <Card className="overflow-hidden p-0">
            <p className="px-4 pt-3 text-[12px] text-muted-foreground" data-testid="total-ambulatorio">
              {m.data.total} {m.data.total === 1 ? "atención" : "atenciones"}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/30 border-b">
                    {COLUMNAS.map((h) => (
                      <th
                        key={h}
                        className="text-left px-3 py-2.5 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {m.data.items.map((it) => (
                    <tr key={it.cita_id} className="border-b text-[12.5px]">
                      <td className="px-3 py-2">{v(it.region)}</td>
                      <td className="px-3 py-2 font-mono">{v(it.codigo_region)}</td>
                      <td className="px-3 py-2">{v(it.comuna)}</td>
                      <td className="px-3 py-2 font-mono">{v(it.codigo_comuna)}</td>
                      <td className="px-3 py-2">{v(it.numero_cuenta)}</td>
                      <td className="px-3 py-2 font-mono">{v(it.opa)}</td>
                      <td className="px-3 py-2 font-mono">{v(it.oda)}</td>
                      <td className="px-3 py-2 font-mono whitespace-nowrap">{v(it.rut)}</td>
                      <td className="px-3 py-2">{it.nombre}</td>
                      <td className="px-3 py-2">{it.cantidad}</td>
                      <td className="px-3 py-2 font-mono">{v(it.codigo_prestacion)}</td>
                      <td className="px-3 py-2">{v(it.glosa_prestacion)}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{fmtDate(it.fecha)}</td>
                      <td className="px-3 py-2">{v(it.hora)}</td>
                      <td className="px-3 py-2">{v(it.monto_total)}</td>
                      <td className="px-3 py-2 font-mono">{it.folio}</td>
                      <td className="px-3 py-2">{v(it.programa)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
    </div>
  );
}
