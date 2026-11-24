import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/utils";
import type { ControlMedicoRead } from "./api";

type NotaSalutem = ControlMedicoRead["notas_salutem"][number];

/** "2026-11-23T12:07:28" (hora local de Santiago) → "23/11/2026 12:07". */
function fechaNota(fecha: string | null | undefined): string | null {
  if (!fecha) return null;
  const hora = fecha.match(/T(\d{2}:\d{2})/)?.[1];
  return hora ? `${fmtDate(fecha)} ${hora}` : fmtDate(fecha);
}

/** Etiqueta del control que tiene un addendum registrado como nota en SALUTEM (QA-008). */
export function BadgeAddendum({ control }: { control: ControlMedicoRead }) {
  if (!control.tiene_addendum) return null;
  return (
    <Badge
      variant="purple"
      title="El control tiene un addendum registrado en SALUTEM: ábrelo para leerlo"
      data-testid={`badge-addendum-${control.id}`}
    >
      Con addendum
    </Badge>
  );
}

/**
 * Las notas de la atención en SALUTEM, completas, con fecha y profesional. Las que son
 * addendum van primero, con su etiqueta; las demás quedan como «Notas de SALUTEM».
 */
export function NotasSalutemControl({ control }: { control: ControlMedicoRead }) {
  const notas = control.notas_salutem ?? [];
  if (notas.length === 0) return null;
  const addendum = notas.filter((n) => n.es_addendum);
  const otras = notas.filter((n) => !n.es_addendum);
  return (
    <div className="space-y-3" data-testid={`notas-salutem-${control.id}`}>
      {addendum.length > 0 && <ListaNotas titulo="Addendum" notas={addendum} />}
      {otras.length > 0 && <ListaNotas titulo="Notas de SALUTEM" notas={otras} />}
    </div>
  );
}

function ListaNotas({ titulo, notas }: { titulo: string; notas: NotaSalutem[] }) {
  return (
    <section>
      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {titulo}
      </h4>
      <ul className="mt-1 space-y-2">
        {notas.map((n, i) => {
          const fecha = fechaNota(n.fecha);
          return (
            <li key={i} className="rounded-md border bg-background px-3 py-2">
              {(fecha || n.profesional) && (
                <div className="text-[11px] text-muted-foreground">
                  {[fecha, n.profesional].filter(Boolean).join(" · ")}
                </div>
              )}
              <p className="mt-0.5 text-[13px] whitespace-pre-line">{n.texto}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
