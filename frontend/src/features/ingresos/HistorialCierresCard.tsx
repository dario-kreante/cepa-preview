/**
 * HistorialCierresCard — cierres y reaperturas del caso en la ficha resumen (QA-007).
 *
 * Cada cierre muestra motivo, fecha y quién cerró; si se reabrió, cuándo, quién y por qué.
 * Sin registros (o mientras carga / si falla) la sección no se muestra.
 */
import { Card, CardContent } from "@/components/ui/card";
import { useHistorialCierres } from "./hooks";
import { etiquetaMotivo } from "./motivosCierre";

/** ISO date (YYYY-MM-DD) → DD/MM/YYYY. */
function fechaCorta(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

/** Instante ISO → DD/MM/YYYY en hora de Chile. */
function fechaChile(iso: string): string {
  const partes = new Intl.DateTimeFormat("es-CL", {
    timeZone: "America/Santiago",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).formatToParts(new Date(iso));
  const p = (t: string) => partes.find((x) => x.type === t)?.value ?? "";
  return `${p("day")}/${p("month")}/${p("year")}`;
}

export function HistorialCierresCard({ ingresoId }: { ingresoId: number }) {
  const { data: cierres = [] } = useHistorialCierres(ingresoId);
  if (cierres.length === 0) return null;

  return (
    <Card data-testid="historial-cierres">
      <CardContent className="p-4">
        <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
          Historial de cierres
        </div>
        <ul className="space-y-2.5">
          {cierres.map((c) => (
            <li key={c.id} className="text-[12px] border-l-2 border-muted pl-3" data-testid="cierre-item">
              <div>
                <span className="font-semibold">{etiquetaMotivo(c.motivo_cierre) ?? c.motivo_cierre}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · Cerrado el {fechaCorta(c.fecha_cierre)} por {c.cerrado_por}
                </span>
              </div>
              {c.reabierto_en && (
                <div className="text-muted-foreground mt-0.5">
                  Reabierto el {fechaChile(c.reabierto_en)}
                  {c.reabierto_por ? ` por ${c.reabierto_por}` : ""}
                  {c.motivo_reapertura ? ` — ${c.motivo_reapertura}` : ""}
                </div>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
