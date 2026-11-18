/**
 * Pacientes con más de un caso de reintegro activo (QA-003). Solo lectura: sirve para
 * revisar los duplicados a mano; desde cada caso se puede abrir su ficha.
 */
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fmtDate } from "@/lib/utils";
import { usePacientesConCasosRepetidos } from "./hooks";
import { ESTADO_REINTEGRO_LABELS } from "./cierreSchema";

interface Props {
  onAbrirCaso: (casoId: number) => void;
}

const th =
  "px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

export function CasosRepetidosPanel({ onAbrirCaso }: Props) {
  const { data, isLoading, isError } = usePacientesConCasosRepetidos();

  if (isLoading)
    return <p className="text-[13px] text-muted-foreground px-1">Buscando casos repetidos…</p>;
  if (isError)
    return (
      <p className="text-[13px] text-destructive px-1">
        No se pudo cargar el listado de casos repetidos.
      </p>
    );
  if (!data || data.length === 0)
    return (
      <p className="text-[13px] text-muted-foreground px-1">
        No hay pacientes con más de un caso activo.
      </p>
    );

  return (
    <div className="space-y-3" data-testid="casos-repetidos">
      <p className="text-[12.5px] text-muted-foreground px-1">
        {data.length} paciente(s) con más de un caso activo (reintegro pendiente o parcial).
      </p>
      {data.map((p) => (
        <Card key={p.paciente_id} className="overflow-hidden p-0">
          <div className="flex items-baseline gap-3 border-b bg-muted/30 px-4 py-2">
            <span className="text-[13px] font-semibold">{p.nombre}</span>
            <span className="font-mono text-[12px] text-muted-foreground">{p.rut ?? "Sin RUT"}</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className={th}>Caso</th>
                <th className={th}>Región</th>
                <th className={th}>Razón social</th>
                <th className={th}>Fecha</th>
                <th className={th}>Estado</th>
                <th className={th} />
              </tr>
            </thead>
            <tbody>
              {p.casos.map((c) => (
                <tr key={c.id} className="border-b last:border-0" data-testid={`fila-caso-${c.id}`}>
                  <td className="px-4 py-2 text-[13px] font-semibold">N° {c.id}</td>
                  <td className="px-4 py-2 text-[12.5px]">{c.region}</td>
                  <td className="px-4 py-2 text-[12.5px]">{c.razon_social ?? "—"}</td>
                  <td className="px-4 py-2 font-mono text-[12px]">{fmtDate(c.fecha_caso)}</td>
                  <td className="px-4 py-2">
                    <Badge variant={c.estado_reintegro === "parcial" ? "warning" : "info"}>
                      {ESTADO_REINTEGRO_LABELS[c.estado_reintegro]}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-[11.5px] px-2"
                      aria-label={`Abrir caso N° ${c.id}`}
                      onClick={() => onAbrirCaso(c.id)}
                    >
                      Abrir
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}
    </div>
  );
}
