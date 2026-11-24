/**
 * Reporte «Externalizado» (QA-010 / QA-013): cada fármaco recetado en el período, con el
 * paciente y su clasificación frente a la canasta del Convenio 002 y la lista Externalizado.
 * Vive en Gestión de fármacos (decidido el 18-11-2026), no en Auditoría.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Download, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtDate } from "@/lib/utils";
import {
  useDescargarExternalizadoExcel,
  useReporteExternalizado,
  type ClasificacionFarmaco,
  type FiltroExternalizado,
} from "./externalizadoApi";

const SIN_DATO = "—";

const VARIANTE: Record<ClasificacionFarmaco, "success" | "info" | "warning" | "neutral"> = {
  "Convenio 002": "success",
  "Convenio 001": "info",
  REVISAR: "warning",
  "Fuera de convenio": "neutral",
};

export function ExternalizadoReporte({
  paciente,
}: {
  /** Paciente elegido en la vista por paciente: permite acotar el reporte a él. */
  paciente?: { id: number; nombre: string } | null;
}) {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [soloPaciente, setSoloPaciente] = useState(false);
  const m = useReporteExternalizado();
  const excel = useDescargarExternalizadoExcel();

  const rangoInvalido = !!desde && !!hasta && desde > hasta;
  const listo = !!desde && !!hasta && !rangoInvalido;
  const filtro = (): FiltroExternalizado => ({
    fecha_desde: desde,
    fecha_hasta: hasta,
    paciente_id: soloPaciente && paciente ? paciente.id : undefined,
  });

  async function generar() {
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

  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="ext-desde">Desde *</Label>
            <Input
              id="ext-desde"
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <Label htmlFor="ext-hasta">Hasta *</Label>
            <Input
              id="ext-hasta"
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              className="h-9"
            />
          </div>
          {paciente && (
            <label className="flex h-9 items-center gap-2 text-[12.5px]">
              <input
                type="checkbox"
                checked={soloPaciente}
                onChange={(e) => setSoloPaciente(e.target.checked)}
                data-testid="ext-solo-paciente"
              />
              Solo {paciente.nombre}
            </label>
          )}
          <Button
            size="sm"
            onClick={generar}
            disabled={m.isPending || !listo}
            data-testid="btn-generar-externalizado"
          >
            <FileText className="size-3.5" />
            {m.isPending ? "Generando…" : "Generar"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={descargar}
            disabled={excel.isPending || !listo}
            data-testid="btn-excel-externalizado"
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
          Recetas (por fecha de emisión) y medicamentos del esquema (por fecha de registro),
          comparados por código SAP y por marca y presentación con la canasta del Convenio 002 y la
          lista Externalizado. «REVISAR» = coincidencia dudosa (solo la marca o el principio activo,
          o varias opciones de distinto convenio).
        </p>
      </Card>

      {m.data && (
        <div className="flex flex-wrap gap-2" data-testid="ext-resumen">
          {m.data.resumen.map((r) => (
            <Badge key={r.clasificacion} variant={VARIANTE[r.clasificacion]}>
              {r.clasificacion}: {r.total}
            </Badge>
          ))}
        </div>
      )}

      {m.data &&
        (m.data.items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
            <p className="text-[13.5px] text-muted-foreground">
              Sin fármacos recetados en el período.
            </p>
          </div>
        ) : (
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/30 border-b">
                    {["Fecha", "Paciente", "RUT", "Folio", "Origen", "Fármaco", "Código SAP", "Clasificación", "Detalle"].map(
                      (h) => (
                        <th
                          key={h}
                          className="text-left px-3 py-2.5 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {m.data.items.map((it) => (
                    <tr key={`${it.origen}-${it.registro_id}`} className="border-b text-[12.5px] align-top">
                      <td className="px-3 py-2 whitespace-nowrap">{fmtDate(it.fecha)}</td>
                      <td className="px-3 py-2">{it.paciente_nombre}</td>
                      <td className="px-3 py-2 font-mono whitespace-nowrap">{it.paciente_rut ?? SIN_DATO}</td>
                      <td className="px-3 py-2 font-mono">{it.folio}</td>
                      <td className="px-3 py-2">{it.origen}</td>
                      <td className="px-3 py-2">
                        <div className="font-medium">{it.farmaco}</div>
                        {it.dosis && <div className="text-[11.5px] text-muted-foreground">{it.dosis}</div>}
                      </td>
                      <td className="px-3 py-2 font-mono">{it.codigo_sap ?? SIN_DATO}</td>
                      <td className="px-3 py-2">
                        <Badge variant={VARIANTE[it.clasificacion]}>{it.clasificacion}</Badge>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">
                        <div>{it.detalle}</div>
                        {it.coincidencias.length > 0 && (
                          <div className="text-[11.5px]">{it.coincidencias.join(" / ")}</div>
                        )}
                      </td>
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
