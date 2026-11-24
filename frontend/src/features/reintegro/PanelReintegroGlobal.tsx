/**
 * PanelReintegroGlobal — lista global de la pestaña Reintegro (QA-010, QA 23-11-2026).
 *
 * Sin buscar paciente: los casos activos de todos los pacientes (con su proyección más
 * reciente y sus pendientes) y «Pendientes por registrar»: pacientes con una alerta de
 * proyección abierta que aún no tienen caso de reintegro activo.
 */
import { AlertCircle, Plus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fmtDate } from "@/lib/utils";
import { usePanelReintegro } from "./hooks";
import { ESTADO_REINTEGRO_LABELS } from "./cierreSchema";
import type { CasoPanel, EstadoReintegro, PendienteRegistro } from "./api";

function estadoVariant(estado: EstadoReintegro): "info" | "warning" | "success" {
  if (estado === "total") return "success";
  if (estado === "parcial") return "warning";
  return "info";
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-4 py-3 font-semibold text-[11px] uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function Pendientes({ caso }: { caso: CasoPanel }) {
  if (!caso.reca_por_solicitar && !caso.pendiente_remitir_isl)
    return <span className="text-[12px] text-muted-foreground">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {caso.reca_por_solicitar && <Badge variant="warning">RECA por solicitar</Badge>}
      {caso.pendiente_remitir_isl && <Badge variant="warning">No remitido a ISL</Badge>}
    </div>
  );
}

interface Props {
  onAbrirCaso: (casoId: number) => void;
  /** Solo para quien puede escribir: abre el alta del caso del paciente pendiente. */
  onRegistrar?: (pendiente: PendienteRegistro) => void;
}

export function PanelReintegroGlobal({ onAbrirCaso, onRegistrar }: Props) {
  const { data, isLoading, isError } = usePanelReintegro();

  if (isLoading)
    return <p className="text-[13px] text-muted-foreground px-1">Cargando casos de reintegro…</p>;
  if (isError || !data)
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-start gap-2">
        <AlertCircle className="size-4 text-destructive mt-0.5 shrink-0" />
        <p className="text-[13px] text-destructive">No se pudo cargar la lista de casos de reintegro.</p>
      </div>
    );

  const { activos, pendientes_registro: pendientes } = data;

  return (
    <div className="space-y-5" data-testid="panel-reintegro-global">
      {pendientes.length > 0 && (
        <section className="space-y-2" aria-labelledby="titulo-pendientes-registro">
          <h2 id="titulo-pendientes-registro" className="text-[14px] font-semibold px-0.5">
            Pendientes por registrar ({pendientes.length})
          </h2>
          <p className="text-[12.5px] text-muted-foreground px-0.5">
            Pacientes con una proyección de reintegro registrada en un control y sin caso de reintegro activo.
          </p>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Paciente</Th>
                  <Th>Folio</Th>
                  <Th>Proyección</Th>
                  <Th>Control</Th>
                  <Th>Plazo estimado</Th>
                  {onRegistrar && <Th>{""}</Th>}
                </tr>
              </thead>
              <tbody>
                {pendientes.map((p) => (
                  <tr key={p.paciente_id} className="border-b" data-testid={`pendiente-${p.paciente_id}`}>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-[13px]">{p.paciente_nombre}</div>
                      <div className="text-[11.5px] text-muted-foreground font-mono">{p.rut ?? "Sin RUT"}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px]">{p.folio}</td>
                    <td className="px-4 py-3 text-[12.5px]">{p.proyeccion ?? "—"}</td>
                    <td className="px-4 py-3 font-mono text-[12px]">{fmtDate(p.fecha_control)}</td>
                    <td className="px-4 py-3 font-mono text-[12px]">
                      {p.plazo_estimado ? fmtDate(p.plazo_estimado) : "Seguimiento"}
                    </td>
                    {onRegistrar && (
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-[11.5px] px-2"
                          onClick={() => onRegistrar(p)}
                          data-testid={`btn-registrar-${p.paciente_id}`}
                        >
                          <Plus className="size-3 mr-1" /> Registrar caso
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </section>
      )}

      <section className="space-y-2" aria-labelledby="titulo-casos-activos">
        <h2 id="titulo-casos-activos" className="text-[14px] font-semibold px-0.5">
          Casos de reintegro activos ({activos.length})
        </h2>
        {activos.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
            <p className="text-[13.5px] text-muted-foreground">No hay casos de reintegro activos.</p>
          </div>
        ) : (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <Th>Paciente</Th>
                  <Th>Folio</Th>
                  <Th>Estado</Th>
                  <Th>Proyección</Th>
                  <Th>Fecha caso</Th>
                  <Th>Pendientes</Th>
                </tr>
              </thead>
              <tbody>
                {activos.map((c) => (
                  <tr
                    key={c.caso_id}
                    onClick={() => onAbrirCaso(c.caso_id)}
                    className="border-b cursor-pointer transition-colors hover:bg-muted/40"
                    data-testid={`activo-${c.caso_id}`}
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-[13px]">{c.paciente_nombre}</div>
                      <div className="text-[11.5px] text-muted-foreground font-mono">{c.rut ?? "Sin RUT"}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px]">{c.folio}</td>
                    <td className="px-4 py-3">
                      <Badge variant={estadoVariant(c.estado_reintegro)}>
                        {ESTADO_REINTEGRO_LABELS[c.estado_reintegro]}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[12.5px]">
                      {c.proyeccion ? (
                        <>
                          <div>{c.proyeccion}</div>
                          {c.fecha_proyeccion && (
                            <div className="text-[11.5px] text-muted-foreground">
                              Control {fmtDate(c.fecha_proyeccion)}
                            </div>
                          )}
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px]">{fmtDate(c.fecha_caso)}</td>
                    <td className="px-4 py-3">
                      <Pendientes caso={c} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </section>
    </div>
  );
}
